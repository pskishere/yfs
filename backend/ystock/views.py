"""
视图模块 - 处理 HTTP 请求和响应
"""
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .models import StockAnalysis, StockInfo
from .services import (
    perform_analysis,
    perform_ai,
    fetch_fundamental,
    fetch_options,
    fetch_news,
)
from .utils import clean_nan_values

logger = logging.getLogger(__name__)


def _load_indicator_info() -> Dict[str, Any]:
    """
    读取本地指标说明文件，失败时返回空字典
    
    Returns:
        指标信息字典
    """
    info_path = Path(__file__).resolve().parent / "indicator_info.json"
    if not info_path.exists():
        return {}
    try:
        return json.loads(info_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _analysis_record(symbol: str, duration: str, bar_size: str) -> StockAnalysis:
    """
    获取或创建分析记录，确保唯一
    """
    record, _ = StockAnalysis.objects.get_or_create(
        symbol=symbol, duration=duration, bar_size=bar_size
    )
    return record


def _serialize_record(record: StockAnalysis) -> Dict[str, Any]:
    """
    将分析记录转换为响应体
    
    Args:
        record: 股票分析记录对象
        
    Returns:
        序列化后的响应字典
    """
    currency_code = None
    currency_symbol = None
    stock_name = None
    if isinstance(record.extra_data, dict):
        currency_code = record.extra_data.get("currency")
        currency_symbol = record.extra_data.get("currency_symbol") or record.extra_data.get("currencySymbol")
        stock_name = record.extra_data.get("stock_name")

    return {
        "success": record.status == StockAnalysis.Status.SUCCESS,
        "symbol": record.symbol,
        "stock_name": stock_name,
        "status": record.status,
        "indicators": record.indicators,
        "candles": record.candles,
        "ai_analysis": record.ai_analysis,
        "ai_available": bool(record.ai_analysis),
        "model": record.model,
        "currency": currency_code,
        "currency_symbol": currency_symbol,
        "task_result_id": record.task_result_id,
        "cached_at": record.cached_at.isoformat() if record.cached_at else None,
        "message": record.error_message,
    }


@require_GET
def health(_: object) -> JsonResponse:
    """
    健康检查接口
    
    Returns:
        JSON 响应，包含服务状态和时间戳
    """
    return JsonResponse(
        {
            "status": "ok",
            "service": "django-ystock",
            "timestamp": timezone.now().isoformat(),
        }
    )


@require_GET
def analyze(request, symbol: str) -> JsonResponse:
    """
    技术分析入口：优先使用当天缓存，避免重复分析前一天的美股数据
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含分析结果
    """
    duration = request.GET.get("duration", "5y")
    bar_size = request.GET.get("bar_size", "1 day")
    symbol = symbol.upper()

    record = _analysis_record(symbol, duration, bar_size)

    # perform_analysis 内部会检查当天缓存，如果有缓存直接返回
    result, error = perform_analysis(symbol, duration, bar_size, use_cache=True)
    if error:
        record.mark_failed(error[0].get("message", "分析失败"))
        return JsonResponse(clean_nan_values(error[0]), status=error[1])
    
    # 如果使用了缓存，直接返回
    if result.get("cached"):
        return JsonResponse(clean_nan_values(_serialize_record(record)))
    
    # 如果没有缓存但分析成功，更新状态（perform_analysis 内部已保存）
    record.refresh_from_db()
    return JsonResponse(clean_nan_values(_serialize_record(record)))


@csrf_exempt
@require_http_methods(["POST"])
def refresh_analyze(request, symbol: str) -> JsonResponse:
    """
    强制刷新分析：无视缓存直接重新排队
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含分析结果
    """
    duration = request.GET.get("duration", "5y")
    bar_size = request.GET.get("bar_size", "1 day")
    symbol = symbol.upper()

    record = _analysis_record(symbol, duration, bar_size)
    record.mark_running(None)
    result, error = perform_analysis(symbol, duration, bar_size, use_cache=False)
    if error:
        record.mark_failed(error[0].get("message", "分析失败"))
        return JsonResponse(clean_nan_values(error[0]), status=error[1])
    record.mark_success(result | {"cached_at": timezone.now()})
    return JsonResponse(clean_nan_values(_serialize_record(record)))


@csrf_exempt
@require_http_methods(["POST"])
def ai_analyze(request, symbol: str) -> JsonResponse:
    """
    AI分析：异步执行，立即返回状态，前端通过轮询获取结果
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含分析状态或结果
    """
    try:
        duration = request.GET.get("duration", "5y")
        bar_size = request.GET.get("bar_size", "1 day")
        symbol = symbol.upper()
        model = request.GET.get("model", "deepseek-v3.2:cloud")
        
        logger.info(f"收到 AI 分析请求: symbol={symbol}, duration={duration}, bar_size={bar_size}, model={model}")

        record = _analysis_record(symbol, duration, bar_size)
        if record.status != StockAnalysis.Status.SUCCESS:
            logger.warning(f"基础分析未完成，无法进行 AI 分析: {symbol}")
            return JsonResponse(
                {"success": False, "message": "请先完成基础分析再请求AI分析"}, status=400
            )

        # 检查是否已有当天的 AI 分析结果（包括前一日美股数据，在亚洲时区可能还是当天）
        # 只有当模型匹配时才使用缓存
        if (
            record.ai_analysis
            and record.cached_at
            and record.cached_at.date() == timezone.now().date()
            and record.model == model
        ):
            logger.info(f"使用当天缓存的 AI 分析结果: {symbol}, 模型: {record.model}")
            payload = _serialize_record(record)
            payload["success"] = True
            payload["cached"] = True
            return JsonResponse(clean_nan_values(payload))

        # 如果正在分析中，返回进行中状态
        if record.status == StockAnalysis.Status.RUNNING and not record.ai_analysis:
            logger.info(f"AI 分析正在进行中: {symbol}")
            return JsonResponse(
                {
                    "success": False,
                    "message": "AI分析正在进行中，请稍后查询",
                    "status": "running",
                },
                status=202,
            )

        # 标记为运行中，异步执行 AI 分析
        record.mark_running()
        logger.info(f"开始异步执行 AI 分析: {symbol}")

        def run_ai_analysis():
            """在后台线程中执行 AI 分析"""
            try:
                from django.db import connection
                # 在新线程中需要关闭旧的数据库连接
                connection.close()
                
                payload, error = perform_ai(symbol, duration, bar_size, model)
                if error:
                    logger.error(f"AI 分析执行失败: {error}")
                    record.mark_failed(error[0].get("message", "AI分析失败"))
                else:
                    logger.info(f"AI 分析执行成功: {symbol}")
                    record.ai_analysis = payload.get("ai_analysis")
                    record.ai_prompt = payload.get("ai_prompt")
                    record.model = payload.get("model")
                    record.status = StockAnalysis.Status.SUCCESS
                    record.cached_at = timezone.now()
                    record.save(update_fields=["ai_analysis", "ai_prompt", "model", "status", "cached_at", "updated_at"])
            except Exception as e:  # noqa: BLE001
                logger.error(f"AI 分析后台执行异常: {e}", exc_info=True)
                record.mark_failed(f"AI分析异常: {str(e)}")

        # 启动后台线程执行 AI 分析
        thread = threading.Thread(target=run_ai_analysis, daemon=True)
        thread.start()

        # 立即返回，让前端轮询获取结果
        return JsonResponse(
            {
                "success": False,
                "message": "AI分析已开始，请稍后查询结果",
                "status": "running",
            },
            status=202,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"AI 分析视图处理异常: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": f"服务器内部错误: {str(e)}"},
            status=500
        )


@require_GET
def hot_stocks(request) -> JsonResponse:
    """
    返回近期分析过的热门股票
    
    Args:
        request: HTTP 请求对象
        
    Returns:
        JSON 响应，包含热门股票列表
    """
    limit = int(request.GET.get("limit", 20))
    rows = (
        StockAnalysis.objects.filter(status=StockAnalysis.Status.SUCCESS)
        .order_by("-updated_at")[:limit]
    )
    stocks = []
    for r in rows:
        info = StockInfo.objects.filter(symbol=r.symbol).first()
        stocks.append(
            {
                "symbol": r.symbol,
                "name": info.name if info else r.symbol,
                "category": "已查询",
            }
        )
    return JsonResponse({"success": True, "count": len(stocks), "stocks": stocks})


@require_GET
def fundamental(request, symbol: str) -> JsonResponse:
    """
    获取基本面数据
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含基本面数据
    """
    symbol = symbol.upper()
    try:
        data = fetch_fundamental(symbol)
        if not data:
            return JsonResponse({"success": False, "message": f"无法获取 {symbol} 的基本面数据"}, status=404)
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def analysis_status(request, symbol: str) -> JsonResponse:
    """
    查询分析任务状态
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含分析状态或结果
    """
    duration = request.GET.get("duration", "5y")
    bar_size = request.GET.get("bar_size", "1 day")
    record, _ = StockAnalysis.objects.get_or_create(
        symbol=symbol.upper(), duration=duration, bar_size=bar_size
    )
    if record.status in (StockAnalysis.Status.PENDING, StockAnalysis.Status.RUNNING):
        return JsonResponse(
            {
                "success": False,
                "message": "分析任务正在进行，请稍后查询",
                "status": record.status,
                "task_result_id": record.task_result_id,
            },
            status=202,
        )
    if record.status == StockAnalysis.Status.FAILED:
        return JsonResponse(
            {
                "success": False,
                "message": record.error_message or "分析失败",
                "status": record.status,
                "task_result_id": record.task_result_id,
            },
            status=500,
        )

    if record.status == StockAnalysis.Status.SUCCESS and record.cached_at:
        payload = _serialize_record(record)
        payload["success"] = True
        return JsonResponse(clean_nan_values(payload))

    # 没有结果则尝试触发一次分析
    payload, error = perform_analysis(record.symbol, duration, bar_size, use_cache=True)
    if error:
        return JsonResponse(clean_nan_values(error[0]), status=error[1])
    record.mark_success(payload | {"cached_at": timezone.now()})
    return JsonResponse(clean_nan_values(_serialize_record(record)))


@require_GET
def options(request, symbol: str) -> JsonResponse:
    """
    获取期权数据
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含期权数据
    """
    symbol = symbol.upper()
    try:
        data = fetch_options(symbol)
        if not data:
            return JsonResponse({"success": False, "message": f"{symbol} 没有期权数据"}, status=404)
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def news(request, symbol: str) -> JsonResponse:
    """
    获取新闻数据
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含新闻数据
    """
    symbol = symbol.upper()
    try:
        data = fetch_news(symbol)
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def indicator_info(request) -> JsonResponse:
    """
    返回指标说明，可按名称过滤
    
    Args:
        request: HTTP 请求对象
        
    Returns:
        JSON 响应，包含指标说明信息
    """
    indicator_name = request.GET.get("indicator", "").lower()
    indicator_info_map = _load_indicator_info()
    if not indicator_info_map:
        return JsonResponse({"success": False, "message": "指标说明缺失"}, status=500)

    if indicator_name:
        info = indicator_info_map.get(indicator_name)
        if not info:
            return JsonResponse(
                {"success": False, "message": f"未找到指标 {indicator_name}"},
                status=404,
            )
        return JsonResponse(
            {"success": True, "indicator": indicator_name, "info": info}
        )

    return JsonResponse({"success": True, "indicators": indicator_info_map})


@require_GET
def index(_: object) -> JsonResponse:
    """
    首页列出可用接口
    
    Args:
        _: HTTP 请求对象（未使用）
        
    Returns:
        JSON 响应，包含服务信息和可用接口列表
    """
    return JsonResponse(
        {
            "service": "yfinance-django",
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/health",
                "analyze": "/api/analyze/<symbol>",
                "refresh": "/api/refresh-analyze/<symbol>",
                "ai": "/api/ai-analyze/<symbol>",
                "hot": "/api/hot-stocks",
                "indicator_info": "/api/indicator-info",
                "fundamental": "/api/fundamental/<symbol>",
                "options": "/api/options/<symbol>",
                "news": "/api/news/<symbol>",
                "delete_stock": "/api/stocks/<symbol>",
                "chat_sessions": "/api/chat/sessions",
                "chat_detail": "/api/chat/sessions/<session_id>",
            },
        }
    )


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def delete_stock(request, symbol: str) -> JsonResponse:
    """
    删除指定股票的缓存分析数据和基本信息
    
    Args:
        request: HTTP 请求对象
        symbol: 股票代码
        
    Returns:
        JSON 响应，包含删除结果
    """
    symbol = symbol.upper()
    deleted_analysis, _ = StockAnalysis.objects.filter(symbol=symbol).delete()
    deleted_info, _ = StockInfo.objects.filter(symbol=symbol).delete()
    return JsonResponse(
        {
            "success": True,
            "symbol": symbol,
            "deleted_analysis": deleted_analysis,
            "deleted_info": deleted_info,
        }
    )


# ============= AI 聊天会话管理 API =============

@csrf_exempt
@require_http_methods(["GET", "POST"])
def chat_sessions(request) -> JsonResponse:
    """
    获取聊天会话列表或创建新会话
    
    GET: 返回所有会话列表
    POST: 创建新会话
    
    Args:
        request: HTTP 请求对象
        
    Returns:
        JSON 响应，包含会话信息
    """
    from .models import ChatSession
    from .serializers import ChatSessionSerializer
    from .agent import StockAIAgent
    
    if request.method == 'GET':
        sessions = ChatSession.objects.all().order_by('-updated_at')[:20]
        serializer = ChatSessionSerializer(sessions, many=True)
        return JsonResponse({'sessions': serializer.data})
    
    elif request.method == 'POST':
        import json
        symbol = None
        model = None
        try:
            data = json.loads(request.body)
            symbol = data.get('symbol')
            model = data.get('model')
        except (json.JSONDecodeError, AttributeError):
            pass
            
        agent = StockAIAgent()
        session_id = agent.create_new_session(symbol=symbol, model=model)
        session = ChatSession.objects.get(session_id=session_id)
        serializer = ChatSessionSerializer(session)
        return JsonResponse({'session': serializer.data})


@csrf_exempt
@require_GET
def chat_session_detail(request, session_id: str) -> JsonResponse:
    """
    获取聊天会话详情（包含消息列表）
    
    Args:
        request: HTTP 请求对象
        session_id: 会话ID
        
    Returns:
        JSON 响应，包含会话详情和消息列表
    """
    from .models import ChatSession
    from .serializers import ChatSessionDetailSerializer
    
    try:
        session = ChatSession.objects.get(session_id=session_id)
        serializer = ChatSessionDetailSerializer(session)
        return JsonResponse({'session': serializer.data})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_chat_session(request, session_id: str) -> JsonResponse:
    """
    删除聊天会话及其所有消息
    
    Args:
        request: HTTP 请求对象
        session_id: 会话ID
        
    Returns:
        JSON 响应，包含删除结果
    """
    from .models import ChatSession
    
    try:
        session = ChatSession.objects.get(session_id=session_id)
        session.delete()
        return JsonResponse({'success': True, 'session_id': session_id})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)
