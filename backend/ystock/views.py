import json
from datetime import timedelta
from pathlib import Path

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .models import StockAnalysis
from .tasks import run_analysis
from .services import (
    clean_nan_values,
    perform_ai,
    perform_analysis,
    fetch_fundamental,
    fetch_institutional,
    fetch_insider,
    fetch_recommendations,
    fetch_earnings,
    fetch_news,
    fetch_options,
    fetch_all_data,
    fetch_comprehensive,
)


def _load_indicator_info() -> dict:
    """
    读取本地指标说明文件，失败时返回空字典
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


def _serialize_record(record: StockAnalysis) -> dict:
    """
    将分析记录转换为响应体
    """
    currency_code = None
    currency_symbol = None
    if isinstance(record.extra_data, dict):
        currency_code = record.extra_data.get("currency")
        currency_symbol = record.extra_data.get("currency_symbol") or record.extra_data.get("currencySymbol")

    return {
        "success": record.status == StockAnalysis.Status.SUCCESS,
        "symbol": record.symbol,
        "status": record.status,
        "indicators": record.indicators,
        "signals": record.signals,
        "candles": record.candles,
        "extra_data": record.extra_data,
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
def health(_: object):
    """
    健康检查
    """
    return JsonResponse(
        {
            "status": "ok",
            "service": "django-ystock",
            "timestamp": timezone.now().isoformat(),
        }
    )


@require_GET
def analyze(request, symbol: str):
    """
    技术分析入口：优先使用当天缓存，避免重复分析前一天的美股数据
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
def refresh_analyze(request, symbol: str):
    """
    强制刷新分析：无视缓存直接重新排队
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
def ai_analyze(request, symbol: str):
    """
    AI分析：异步执行，立即返回状态，前端通过轮询获取结果
    """
    import logging
    import threading
    logger = logging.getLogger(__name__)
    
    try:
        duration = request.GET.get("duration", "5y")
        bar_size = request.GET.get("bar_size", "1 day")
        symbol = symbol.upper()
        model = request.GET.get("model", "deepseek-v3.1:671b-cloud")
        
        logger.info(f"收到 AI 分析请求: symbol={symbol}, duration={duration}, bar_size={bar_size}, model={model}")

        record = _analysis_record(symbol, duration, bar_size)
        if record.status != StockAnalysis.Status.SUCCESS:
            logger.warning(f"基础分析未完成，无法进行 AI 分析: {symbol}")
            return JsonResponse(
                {"success": False, "message": "请先完成基础分析再请求AI分析"}, status=400
            )

        # 检查是否已有当天的 AI 分析结果（包括前一日美股数据，在亚洲时区可能还是当天）
        if (
            record.ai_analysis
            and record.cached_at
            and record.cached_at.date() == timezone.now().date()
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
            except Exception as e:
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
    except Exception as e:
        logger.error(f"AI 分析视图处理异常: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": f"服务器内部错误: {str(e)}"},
            status=500
        )


@require_GET
def hot_stocks(request):
    """
    返回近期分析过的热门股票
    """
    limit = int(request.GET.get("limit", 20))
    rows = (
        StockAnalysis.objects.filter(status=StockAnalysis.Status.SUCCESS)
        .order_by("-updated_at")[:limit]
    )
    stocks = []
    from .models import StockInfo  # 局部导入避免循环

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
def fundamental(request, symbol: str):
    """
    获取基本面数据
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
def analysis_status(request, symbol: str):
    """
    查询分析任务状态
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
def institutional(request, symbol: str):
    """
    获取机构持仓
    """
    symbol = symbol.upper()
    try:
        holders = fetch_institutional(symbol) or []
        return JsonResponse({"success": True, "symbol": symbol, "data": holders})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def insider(request, symbol: str):
    """
    获取内部交易
    """
    symbol = symbol.upper()
    try:
        data = fetch_insider(symbol) or []
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def recommendations(request, symbol: str):
    """
    获取分析师推荐
    """
    symbol = symbol.upper()
    try:
        data = fetch_recommendations(symbol) or []
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def earnings(request, symbol: str):
    """
    获取收益数据
    """
    symbol = symbol.upper()
    try:
        data = fetch_earnings(symbol) or {}
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def news(request, symbol: str):
    """
    获取股票新闻
    """
    symbol = symbol.upper()
    limit = int(request.GET.get("limit", 50))
    try:
        data = fetch_news(symbol, limit=limit) or []
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def options(request, symbol: str):
    """
    获取期权数据
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
def comprehensive(request, symbol: str):
    """
    全面股票分析
    """
    symbol = symbol.upper()
    include_options = request.GET.get("include_options", "false").lower() == "true"
    include_news = request.GET.get("include_news", "true").lower() == "true"
    news_limit = int(request.GET.get("news_limit", 50))
    try:
        analysis = fetch_comprehensive(symbol, include_options, include_news, news_limit)
        if not analysis:
            return JsonResponse({"success": False, "message": f"无法获取 {symbol} 的数据"}, status=404)
        return JsonResponse({"success": True, "symbol": symbol, "analysis": analysis})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def all_data(request, symbol: str):
    """
    获取股票所有原始数据
    """
    symbol = symbol.upper()
    include_options = request.GET.get("include_options", "false").lower() == "true"
    include_news = request.GET.get("include_news", "true").lower() == "true"
    news_limit = int(request.GET.get("news_limit", 50))
    try:
        data = fetch_all_data(symbol, include_options, include_news, news_limit)
        if not data:
            return JsonResponse({"success": False, "message": f"无法获取 {symbol} 的数据"}, status=404)
        return JsonResponse({"success": True, "symbol": symbol, "data": data})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@require_GET
def indicator_info(request):
    """
    返回指标说明，可按名称过滤
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
def index(_: object):
    """
    首页列出可用接口
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
                "institutional": "/api/institutional/<symbol>",
                "insider": "/api/insider/<symbol>",
                "recommendations": "/api/recommendations/<symbol>",
                "earnings": "/api/earnings/<symbol>",
                "news": "/api/news/<symbol>",
                "options": "/api/options/<symbol>",
                "comprehensive": "/api/comprehensive/<symbol>",
                "all_data": "/api/all-data/<symbol>",
            },
        }
    )
