"""
服务层模块 - 处理股票分析业务逻辑
"""
import logging
from typing import Any, Dict, Tuple

from django.db import transaction
from django.utils import timezone

from .analysis import (
    calculate_technical_indicators,
    check_ollama_available,
    perform_ai_analysis,
)
from .models import StockAnalysis, StockInfo
from .utils import (
    format_candle_data,
    extract_stock_name,
    create_error_response,
    create_success_response,
    clean_nan_values,
)
from .yfinance import (
    get_stock_info,
    get_historical_data,
    get_fundamental_data,
    get_options,
    get_news,
    search_symbols,
)

logger = logging.getLogger(__name__)


def save_stock_info_if_available(symbol: str) -> Dict[str, Any] | None:
    """
    获取并缓存股票名称（使用 ORM），并返回获取到的股票信息
    
    Args:
        symbol: 股票代码
        
    Returns:
        股票信息字典，如果获取失败则返回 None
    """
    try:
        stock_info = get_stock_info(symbol)
        if not stock_info:
            return None
        stock_name = extract_stock_name(stock_info)
        if stock_name and stock_name != symbol:
            StockInfo.objects.update_or_create(
                symbol=symbol, defaults={"name": stock_name}
            )
        return stock_info
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"获取股票信息失败: {exc}")
        return None


def get_extra_analysis_data(symbol: str) -> Dict[str, Any]:
    """
    获取额外分析数据
    
    Args:
        symbol: 股票代码
        
    Returns:
        包含额外分析数据的字典
    """
    return {}


def perform_analysis(symbol: str, duration: str, bar_size: str, use_cache: bool = True) -> Tuple[Dict[str, Any] | None, Tuple[Dict[str, Any], int] | None]:
    """
    执行技术分析：优先读取 ORM 缓存，未命中则重算并保存
    
    Args:
        symbol: 股票代码
        duration: 数据周期
        bar_size: K线周期
        use_cache: 是否使用缓存
        
    Returns:
        (分析结果字典, 错误响应元组) 或 (None, 错误响应元组)
    """
    record, _ = StockAnalysis.objects.get_or_create(
        symbol=symbol, duration=duration, bar_size=bar_size
    )

    # 检查是否有当天的缓存（包括前一日美股数据，在亚洲时区可能还是当天）
    if (
        use_cache
        and record.status == StockAnalysis.Status.SUCCESS
        and record.cached_at
        and record.cached_at.date() == timezone.now().date()
    ):
        logger.info(f"使用当天缓存的分析结果: {symbol}, 缓存时间: {record.cached_at}")
        
        indicators = record.indicators or {}
        # 如果缓存中没有新闻数据，尝试补充
        if 'news_data' not in indicators or not indicators.get('news_data'):
            try:
                from .yfinance import get_news
                news_data = get_news(symbol)
                if news_data:
                    indicators['news_data'] = news_data
                    record.indicators = indicators
                    record.save(update_fields=['indicators'])
                    logger.info(f"为缓存结果补充了新闻数据: {symbol}")
            except Exception as e:
                logger.warning(f"补充新闻数据失败: {symbol}, 错误: {e}")

        return {
            "success": True,
            "indicators": record.indicators,
            "candles": record.candles,
            "extra_data": record.extra_data,
            "ai_analysis": record.ai_analysis,
            "model": record.model,
            "ai_available": bool(record.ai_analysis),
            "cached": True,
        }, None

    stock_info = save_stock_info_if_available(symbol)
    stock_name = extract_stock_name(stock_info) if stock_info else None

    hist_data, hist_error = get_historical_data(symbol, duration, bar_size)
    indicators, ind_error = calculate_technical_indicators(symbol, duration, bar_size)

    if hist_error:
        return None, create_error_response(hist_error)

    if ind_error:
        return None, create_error_response(ind_error)

    # 即使数据不足，也允许返回部分指标
    if not indicators:
        # 如果完全没有数据，返回错误；否则返回空指标但允许继续
        if not hist_data or len(hist_data) == 0:
            return None, ({"success": False, "message": "无法获取历史数据"}, 404)
        # 有数据但指标计算失败，返回空指标结构
        indicators = {"symbol": symbol, "current_price": 0, "data_points": len(hist_data) if hist_data else 0}

    formatted_candles = format_candle_data(hist_data)
    extra_data = get_extra_analysis_data(symbol)
    currency_code = stock_info.get("currency") if stock_info else None
    currency_symbol = stock_info.get("currencySymbol") if stock_info else None

    # 构建额外数据
    payload_extra = extra_data or {}
    if currency_code:
        payload_extra["currency"] = currency_code
    if currency_symbol:
        payload_extra["currency_symbol"] = currency_symbol
    if stock_name:
        payload_extra["stock_name"] = stock_name

    # 构建响应结果
    result = create_success_response(indicators, None, formatted_candles, None, None)
    if currency_code:
        result["currency"] = currency_code
    if currency_symbol:
        result["currency_symbol"] = currency_symbol
    if stock_name:
        result["stock_name"] = stock_name
    if payload_extra:
        result["extra_data"] = payload_extra

    with transaction.atomic():
        # 清洗数据中的 NaN/inf 值，确保 JSON 字段有效
        record.indicators = clean_nan_values(result.get("indicators"))
        record.candles = clean_nan_values(result.get("candles"))
        record.extra_data = clean_nan_values(result.get("extra_data"))
        record.status = StockAnalysis.Status.SUCCESS
        record.cached_at = timezone.now()
        record.error_message = None
        record.save()

    result["data_saved"] = True
    return result, None


def perform_ai(symbol: str, duration: str, bar_size: str, model: str) -> Tuple[Dict[str, Any] | None, Tuple[Dict[str, Any], int] | None]:
    """
    基于已缓存结果执行 AI 分析（ORM 存储）
    
    Args:
        symbol: 股票代码
        duration: 数据周期
        bar_size: K线周期
        model: AI 模型名称
        
    Returns:
        (AI分析结果字典, 错误响应元组) 或 (None, 错误响应元组)
    """
    try:
        record = StockAnalysis.objects.get(
            symbol=symbol, duration=duration, bar_size=bar_size
        )
    except StockAnalysis.DoesNotExist:
        return None, (
            {"success": False, "message": "数据不存在，请先执行基础分析"},
            404,
        )

    extra_data = record.extra_data or {}
    currency_code = extra_data.get("currency")
    currency_symbol = extra_data.get("currency_symbol") or extra_data.get("currencySymbol")

    # 如果当天已有 AI 分析结果，直接返回
    if record.ai_analysis and record.cached_at and record.cached_at.date() == timezone.now().date():
        # 如果模型相同，直接返回
        if record.model == model:
            logger.info(f"使用当天缓存的 AI 分析结果: {symbol}, 模型: {model}")
            return {
                "success": True,
                "ai_analysis": record.ai_analysis,
                "model": record.model,
                "ai_available": True,
                "cached": True,
                "currency": currency_code,
                "currency_symbol": currency_symbol,
                "extra_data": record.extra_data,
            }, None
        # 如果模型不同，且之前的分析不是错误消息，则重新分析（或者根据需求决定是否允许切换模型重新分析）
        # 这里改为：如果模型不同，强制重新分析，以支持模型切换
        logger.info(f"请求模型 ({model}) 与缓存模型 ({record.model}) 不同，将重新执行 AI 分析")

    if not check_ollama_available():
        return None, (
            {"success": False, "message": "Ollama服务不可用，无法执行AI分析"},
            503,
        )

    try:
        logger.info(f"开始获取额外数据: {symbol}")
        extra_data = record.extra_data or get_extra_analysis_data(symbol)
        logger.info(f"开始执行 AI 分析: {symbol}, 模型: {model}")
        ai_analysis, ai_prompt = perform_ai_analysis(
            symbol,
            record.indicators,
            duration,
            model,
            extra_data,
        )
        logger.info(f"AI 分析完成，开始保存结果: {symbol}")
        with transaction.atomic():
            record.ai_analysis = ai_analysis
            record.ai_prompt = ai_prompt
            record.model = model
            record.status = StockAnalysis.Status.SUCCESS
            record.cached_at = timezone.now()
            record.save()

        logger.info(f"AI 分析结果已保存: {symbol}")
        return {
            "success": True,
            "ai_analysis": ai_analysis,
            "model": model,
            "ai_available": True,
            "cached": False,
            "currency": currency_code,
            "currency_symbol": currency_symbol,
            "extra_data": extra_data,
        }, None
    except Exception as exc:  # noqa: BLE001
        logger.error(f"AI分析执行失败: {exc}", exc_info=True)
        return None, (
            {"success": False, "message": f"AI分析执行失败: {str(exc)}"},
            500,
        )


def fetch_fundamental(symbol: str) -> Dict[str, Any] | None:
    """
    获取基本面数据
    """
    return get_fundamental_data(symbol)


def fetch_options(symbol: str) -> Dict[str, Any] | None:
    """
    获取期权数据
    """
    return get_options(symbol)


def fetch_news(symbol: str) -> list[Dict[str, Any]]:
    """
    获取新闻数据
    """
    return get_news(symbol)


def search_stocks(query: str) -> list[Dict[str, Any]]:
    """
    搜索股票代码
    """
    return search_symbols(query)
