import logging
import math
from typing import Any, Dict, Tuple

from django.db import transaction
from django.utils import timezone

from .analysis import calculate_technical_indicators, generate_signals
from .utils import (
    format_candle_data,
    extract_stock_name,
    create_error_response,
    create_success_response,
)
from .yfinance import (
    get_stock_info,
    get_historical_data,
    get_fundamental_data,
    get_all_data,
    get_options,
    get_news,
    get_institutional_holders,
    get_insider_transactions,
    get_recommendations,
    get_earnings,
)
from .analysis import check_ollama_available, perform_ai_analysis, create_comprehensive_analysis
from .models import StockAnalysis, StockInfo

logger = logging.getLogger(__name__)


def clean_nan_values(obj: Any):
    """
    清洗 NaN/inf，保证 JSON 可序列化
    """
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan_values(i) for i in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


def save_stock_info_if_available(symbol: str):
    """
    获取并缓存股票名称（使用 ORM）
    """
    try:
        stock_info = get_stock_info(symbol)
        if not stock_info:
            return
        stock_name = extract_stock_name(stock_info)
        if stock_name and stock_name != symbol:
            StockInfo.objects.update_or_create(
                symbol=symbol, defaults={"name": stock_name}
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"获取股票信息失败: {exc}")


def get_extra_analysis_data(symbol: str) -> dict:
    """
    获取额外分析数据（机构、内部、推荐、收益、新闻）
    """
    extra_data: Dict[str, Any] = {}
    try:
        institutional = get_institutional_holders(symbol)
        if institutional:
            extra_data["institutional_holders"] = institutional[:20]

        insider = get_insider_transactions(symbol)
        if insider:
            extra_data["insider_transactions"] = insider[:15]

        recommendations = get_recommendations(symbol)
        if recommendations:
            extra_data["analyst_recommendations"] = recommendations[:10]

        earnings = get_earnings(symbol)
        if earnings:
            extra_data["earnings"] = earnings

        news = get_news(symbol, limit=30)
        if news and len(news) > 0:
            extra_data["news"] = news
            logger.info(f"已添加新闻数据到extra_data: {symbol}, {len(news)}条")
        else:
            logger.debug(f"未获取到新闻数据: {symbol}, news={news}")

        logger.info(
            f"已获取额外分析数据: {symbol}, 模块: {list(extra_data.keys())}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"获取额外数据失败: {symbol}, 错误: {exc}")
    return extra_data


def perform_analysis(symbol: str, duration: str, bar_size: str, use_cache: bool = True):
    """
    执行技术分析：优先读取 ORM 缓存，未命中则重算并保存
    """
    record, _ = StockAnalysis.objects.get_or_create(
        symbol=symbol, duration=duration, bar_size=bar_size
    )

    if (
        use_cache
        and record.status == StockAnalysis.Status.SUCCESS
        and record.cached_at
        and record.cached_at.date() == timezone.now().date()
    ):
        return {
            "success": True,
            "indicators": record.indicators,
            "signals": record.signals,
            "candles": record.candles,
            "extra_data": record.extra_data,
            "ai_analysis": record.ai_analysis,
            "model": record.model,
            "ai_available": bool(record.ai_analysis),
            "cached": True,
        }, None

    save_stock_info_if_available(symbol)

    hist_data, hist_error = get_historical_data(symbol, duration, bar_size)
    indicators, ind_error = calculate_technical_indicators(symbol, duration, bar_size)

    if hist_error:
        return None, create_error_response(hist_error)

    if ind_error:
        return None, create_error_response(ind_error)

    if not indicators:
        return None, ({"success": False, "message": "数据不足，无法计算技术指标"}, 404)

    signals = generate_signals(indicators)
    formatted_candles = format_candle_data(hist_data)
    extra_data = get_extra_analysis_data(symbol)

    result = create_success_response(indicators, signals, formatted_candles, None, None)
    if extra_data:
        result["extra_data"] = extra_data

    with transaction.atomic():
        record.indicators = result.get("indicators")
        record.signals = result.get("signals")
        record.candles = result.get("candles")
        record.extra_data = result.get("extra_data")
        record.status = StockAnalysis.Status.SUCCESS
        record.cached_at = timezone.now()
        record.error_message = None
        record.save()

    result["data_saved"] = True
    return result, None


def perform_ai(symbol: str, duration: str, bar_size: str, model: str):
    """
    基于已缓存结果执行 AI 分析（ORM 存储）
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

    if record.ai_analysis:
        return {
            "success": True,
            "ai_analysis": record.ai_analysis,
            "model": record.model,
            "ai_available": True,
            "cached": True,
        }, None

    if not check_ollama_available():
        return None, (
            {"success": False, "message": "Ollama服务不可用，无法执行AI分析"},
            503,
        )

    try:
        extra_data = record.extra_data or get_extra_analysis_data(symbol)
        ai_analysis, ai_prompt = perform_ai_analysis(
            symbol,
            record.indicators,
            record.signals,
            duration,
            model,
            extra_data,
        )
        with transaction.atomic():
            record.ai_analysis = ai_analysis
            record.ai_prompt = ai_prompt
            record.model = model
            record.status = StockAnalysis.Status.SUCCESS
            record.cached_at = timezone.now()
            record.save()

        return {
            "success": True,
            "ai_analysis": ai_analysis,
            "model": model,
            "ai_available": True,
            "cached": False,
        }, None
    except Exception as exc:  # noqa: BLE001
        logger.error(f"AI分析执行失败: {exc}")
        return None, (
            {"success": False, "message": f"AI分析执行失败: {str(exc)}"},
            500,
        )


def fetch_fundamental(symbol: str):
    """
    获取基本面数据
    """
    return get_fundamental_data(symbol)


def fetch_institutional(symbol: str):
    """
    获取机构持仓
    """
    return get_institutional_holders(symbol)


def fetch_insider(symbol: str):
    """
    获取内部交易
    """
    return get_insider_transactions(symbol)


def fetch_recommendations(symbol: str):
    """
    获取分析师推荐
    """
    return get_recommendations(symbol)


def fetch_earnings(symbol: str):
    """
    获取收益数据
    """
    return get_earnings(symbol)


def fetch_news(symbol: str, limit: int = 50):
    """
    获取新闻
    """
    return get_news(symbol, limit=limit)


def fetch_options(symbol: str):
    """
    获取期权数据
    """
    return get_options(symbol)


def fetch_all_data(symbol: str, include_options: bool, include_news: bool, news_limit: int):
    """
    获取股票所有数据
    """
    return get_all_data(
        symbol,
        include_options=include_options,
        include_news=include_news,
        news_limit=news_limit,
    )


def fetch_comprehensive(symbol: str, include_options: bool, include_news: bool, news_limit: int):
    """
    获取综合分析
    """
    all_data = fetch_all_data(symbol, include_options, include_news, news_limit)
    if not all_data:
        return None
    return create_comprehensive_analysis(symbol, all_data)
