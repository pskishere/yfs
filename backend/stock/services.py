"""
服务层模块 - 处理股票分析业务逻辑
"""
import logging
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple, List

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from .analysis import calculate_technical_indicators
from .models import Stock, StockProfile, StockQuote, StockKLine
from .utils import (
    format_candle_data,
    create_error_response,
    create_success_response,
)
from .yfinance import (
    get_stock_info,
    get_historical_data,
    get_options_chain,
    get_news,
    get_holders,
    get_financials,
    search_symbols as yf_search_symbols,
)
from .news_api import fetch_news_api

logger = logging.getLogger(__name__)


def _refresh_stock_data(symbol: str) -> Tuple[Stock | None, StockProfile | None, StockQuote | None]:
    """
    [内部函数] 从 yfinance 获取最新数据，并同时更新 Stock, Profile, Quote
    """
    try:
        info = get_stock_info(symbol)
        if not info:
            return None, None, None
            
        with transaction.atomic():
            stock, _ = Stock.objects.get_or_create(symbol=symbol)
            
            # 1. 更新 Stock 基础信息
            stock.name = info.get('longName', info.get('shortName', ''))
            stock.exchange = info.get('exchange', '')
            stock.asset_type = info.get('quoteType', '')
            stock.save()
            
            # 2. 更新/创建 Profile
            profile_data = {
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'employees': info.get('fullTimeEmployees'),
                'website': info.get('website', ''),
                'description': info.get('longBusinessSummary', ''),
                'raw_info': info,
            }
            
            profile, _ = StockProfile.objects.update_or_create(
                stock=stock,
                defaults=profile_data
            )
            
            # 3. 更新/创建 Quote
            quote_data = {
                'price': info.get('currentPrice') or info.get('regularMarketPrice') or 0.0,
                'change': 0.0,
                'change_pct': 0.0,
                'volume': info.get('volume') or info.get('regularMarketVolume') or 0,
                'prev_close': info.get('previousClose') or 0.0,
                'open_price': info.get('open') or info.get('regularMarketOpen') or 0.0,
                'day_high': info.get('dayHigh') or info.get('regularMarketDayHigh') or 0.0,
                'day_low': info.get('dayLow') or info.get('regularMarketDayLow') or 0.0,
            }
            
            # 计算涨跌幅
            if quote_data['prev_close'] and quote_data['price']:
                quote_data['change'] = quote_data['price'] - quote_data['prev_close']
                quote_data['change_pct'] = (quote_data['change'] / quote_data['prev_close']) * 100
                
            quote, _ = StockQuote.objects.update_or_create(
                stock=stock,
                defaults=quote_data
            )
            
        return stock, profile, quote
        
    except Exception as e:
        logger.error(f"刷新股票数据失败 {symbol}: {e}")
        return None, None, None


def get_or_update_stock_profile(symbol: str) -> Tuple[Stock, StockProfile | None]:
    """
    获取或更新股票基本面数据
    """
    try:
        stock, _ = Stock.objects.get_or_create(symbol=symbol)
        profile = getattr(stock, 'profile', None)
            
        # 如果不存在或已过期，则调用统一刷新
        if not profile or profile.is_stale(hours=24):
            _stock, _profile, _ = _refresh_stock_data(symbol)
            if _stock:
                stock, profile = _stock, _profile
                
        return stock, profile
        
    except Exception as e:
        logger.error(f"更新股票资料失败 {symbol}: {e}")
        return Stock.objects.filter(symbol=symbol).first(), StockProfile.objects.filter(stock__symbol=symbol).first()


def get_or_update_stock_quote(symbol: str) -> Tuple[Stock, StockQuote | None]:
    """
    获取或更新股票实时行情
    """
    try:
        stock, _ = Stock.objects.get_or_create(symbol=symbol)
        quote = getattr(stock, 'quote', None)
            
        # 如果不存在或已过期(1分钟)，则调用统一刷新
        if not quote or quote.is_stale(minutes=1):
            _stock, _, _quote = _refresh_stock_data(symbol)
            if _stock:
                stock, quote = _stock, _quote
                
        return stock, quote
    except Exception as e:
        logger.error(f"更新股票行情失败 {symbol}: {e}")
        return Stock.objects.filter(symbol=symbol).first(), StockQuote.objects.filter(stock__symbol=symbol).first()



def save_stock_info_if_available(symbol: str) -> Dict[str, Any] | None:
    """
    获取并缓存股票名称（使用 ORM），并返回获取到的股票信息
    (保留此函数名以兼容现有逻辑，但底层改为使用新的 Stock/Profile 模型)
    
    Args:
        symbol: 股票代码
        
    Returns:
        股票信息字典，如果获取失败则返回 None
    """
    stock, profile = get_or_update_stock_profile(symbol)
    
    if not stock:
        return None
        
    # 构建兼容旧版返回格式的字典
    # 优先使用 Profile 中的 raw_info，如果没有则构建基本信息
    if profile and profile.raw_info:
        return profile.raw_info
        
    return {
        'symbol': stock.symbol,
        'longName': stock.name,
        'exchange': stock.exchange,
        # 其他字段可能缺失，但至少保证基本可用
    }


def _get_start_date_from_duration(duration: str) -> datetime:
    """
    根据 duration 计算起始时间
    """
    now = timezone.now()
    duration = duration.strip().lower()
    
    # 默认回退 1 年
    default_start = now - timedelta(days=365)
    
    if not duration:
        return default_start
        
    try:
        if duration == 'max':
            return now - timedelta(days=365*50)
        
        # 提取数字和单位
        match = re.match(r'^(\d+)([a-z]+)$', duration)
        if not match:
            return default_start
            
        value, unit = int(match.group(1)), match.group(2)
        
        if unit in ['y', 'year', 'years']:
            return now - timedelta(days=value * 365)
        elif unit in ['mo', 'm', 'month', 'months']:
            return now - timedelta(days=value * 30)
        elif unit in ['wk', 'w', 'week', 'weeks']:
            return now - timedelta(weeks=value)
        elif unit in ['d', 'day', 'days']:
            return now - timedelta(days=value)
            
        return default_start
    except Exception:
        return default_start


def _fetch_klines_from_db(stock: Stock, period: str, duration: str) -> List[Dict[str, Any]]:
    """
    从数据库获取 K线数据并格式化
    """
    start_date = _get_start_date_from_duration(duration)
    
    klines = StockKLine.objects.filter(
        stock=stock,
        period=period,
        date__gte=start_date
    ).order_by('date')
    
    result = []
    is_intraday = period.lower() in ['1m', '2m', '5m', '15m', '30m', '60m', '1h']
    
    for k in klines:
        date_str = k.date.strftime('%Y-%m-%d %H:%M:%S' if is_intraday else '%Y-%m-%d')
        
        result.append({
            'time': date_str,
            'open': k.open,
            'high': k.high,
            'low': k.low,
            'close': k.close,
            'volume': k.volume,
        })
    return result


def get_cached_news(symbol: str) -> List[Dict[str, Any]]:
    """
    获取新闻数据（带缓存）
    """
    key = f"stock_news_{symbol}"
    news = cache.get(key)
    if not news:
        try:
            # 1. 从 yfinance 获取
            news = get_news(symbol)
            
            # 2. 如果配置了 NEWS_API_KEY，尝试从 NewsAPI 获取补充新闻
            news_api_results = fetch_news_api(symbol)
            if news_api_results:
                # 合并并去重（基于标题）
                existing_titles = {n.get('title') for n in news}
                for n in news_api_results:
                    if n.get('title') not in existing_titles:
                        news.append(n)
            
            if news:
                cache.set(key, news, timeout=60*15) # 15分钟缓存
        except Exception as e:
            logger.warning(f"获取新闻失败: {symbol}, {e}")
            news = []
    return news or []


def _get_kline_staleness_threshold(bar_size: str) -> int:
    """
    [内部函数] 根据 K线周期获取过时阈值（秒）
    """
    seconds_map = {
        '1m': 60, '1 min': 60,
        '2m': 120, '5m': 300, '5 mins': 300,
        '15m': 900, '15 mins': 900,
        '30m': 1800, '30 mins': 1800,
        '60m': 3600, '1h': 3600, '1 hour': 3600,
        '1d': 86400, '1 day': 86400,
    }
    return seconds_map.get(bar_size.lower(), 3600)


def _check_kline_continuity(stock: Stock, bar_size: str, duration: str, profile: StockProfile | None) -> bool:
    """
    [内部函数] 检查 K线数据是否连续，如果不连续返回 True (表示需要刷新)
    """
    if bar_size not in ['1d', '1 day']:
        return False

    try:
        target_start_date = _get_start_date_from_duration(duration)
        effective_start_date = target_start_date
        
        # 尝试利用 IPO 日期优化起始时间
        ipo_timestamp = profile.raw_info.get('firstTradeDateEpochUtc') if profile and profile.raw_info else None
        if ipo_timestamp:
            ipo_date = datetime.fromtimestamp(ipo_timestamp, tz=timezone.utc)
            if ipo_date > effective_start_date:
                effective_start_date = ipo_date
        
        # 获取 DB 中最早的一条记录
        first_kline = StockKLine.objects.filter(stock=stock, period=bar_size).order_by('date').first()
        if not first_kline:
            return True
            
        # 1. 检查头部缺失 (允许 10 天缓冲)
        if ipo_timestamp and first_kline.date > effective_start_date + timedelta(days=10):
            logger.info(f"数据头部缺失 {stock.symbol}: 最早 {first_kline.date}, 预期 {effective_start_date}")
            return True
            
        # 2. 检查内部断层 (仅针对跨度 > 30 天的数据)
        days_diff = (timezone.now() - first_kline.date).days
        if days_diff > 30:
            actual_count = StockKLine.objects.filter(stock=stock, period=bar_size, date__gte=first_kline.date).count()
            expected_min = int(days_diff * 0.65) # 估算交易日下限
            if actual_count < expected_min:
                logger.info(f"数据断层检测 {stock.symbol}: 实有 {actual_count}, 预期最少 {expected_min}")
                return True
                
    except Exception as e:
        logger.warning(f"连续性检查异常 {stock.symbol}: {e}")
        
    return False


def _sync_stock_klines(stock: Stock, bar_size: str, duration: str, profile: StockProfile | None) -> Tuple[bool, str | None]:
    """
    [内部函数] 同步 K线数据：检查时效性和连续性，必要时从 API 获取并存档
    
    Returns:
        (是否成功, 错误信息)
    """
    need_fetch = False
    last_kline = StockKLine.objects.filter(stock=stock, period=bar_size).order_by('-date').first()
    
    if not last_kline:
        need_fetch = True
    else:
        # 1. 检查时效性 (超过 2x 周期则认为过时)
        diff_seconds = (timezone.now() - last_kline.date).total_seconds()
        threshold = _get_kline_staleness_threshold(bar_size)
        if diff_seconds > threshold * 2:
            need_fetch = True
            
        # 2. 检查连续性
        if not need_fetch:
            need_fetch = _check_kline_continuity(stock, bar_size, duration, profile)

    if not need_fetch:
        return True, None

    # 执行获取
    hist_data_raw, hist_error = get_historical_data(stock.symbol, duration, bar_size)
    if hist_error:
        return False, hist_error
        
    if not hist_data_raw:
        return True, None

    # 归档到数据库
    try:
        kline_objs = []
        for row in hist_data_raw:
            date_str = row.get('date')
            if not date_str:
                continue
                
            try:
                if len(date_str) == 8:
                    dt = datetime.strptime(date_str, '%Y%m%d')
                else:
                    dt = datetime.strptime(date_str, '%Y%m%d %H:%M:%S')
                
                date_val = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            except:
                continue

            # 验证 OHLC
            vals = [row.get('open'), row.get('high'), row.get('low'), row.get('close')]
            if any(v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) for v in vals):
                continue

            kline_objs.append(StockKLine(
                stock=stock,
                date=date_val,
                period=bar_size,
                open=vals[0],
                high=vals[1],
                low=vals[2],
                close=vals[3],
                volume=int(row.get('volume', 0))
            ))
        
        if kline_objs:
            StockKLine.objects.bulk_create(
                kline_objs, 
                update_conflicts=True,
                unique_fields=['stock', 'date', 'period'],
                update_fields=['open', 'high', 'low', 'close', 'volume']
            )
            logger.info(f"已同步 K线数据: {stock.symbol}, 周期: {bar_size}, 数量: {len(kline_objs)}")
        return True, None
        
    except Exception as e:
        err_msg = f"归档 K线数据失败: {e}"
        logger.error(f"{stock.symbol} {err_msg}")
        return False, err_msg


def perform_analysis(symbol: str, duration: str, bar_size: str, use_cache: bool = True) -> Tuple[Dict[str, Any] | None, Tuple[Dict[str, Any], int] | None]:
    """
    执行技术分析：实时计算，基于 StockKLine 和 StockProfile
    
    Args:
        symbol: 股票代码
        duration: 数据周期
        bar_size: K线周期
        use_cache: 是否使用缓存 (默认 True)
        
    Returns:
        (分析结果字典, 错误响应元组) 或 (None, 错误响应元组)
    """
    # 1. 确保基础信息和实时行情是最新的
    stock, profile = get_or_update_stock_profile(symbol)
    if not stock:
        return None, ({"success": False, "message": f"股票不存在: {symbol}"}, 404)
        
    # 如果不使用缓存且 profile 已存在，强制更新一次
    if not use_cache and profile:
        _stock, _profile, _ = _refresh_stock_data(symbol)
        if _stock:
            stock, profile = _stock, _profile

    # 2. 同步 K线数据
    success, sync_error = _sync_stock_klines(stock, bar_size, duration, profile)
    
    # 如果同步失败且数据库中没有旧数据，则返回错误
    if not success and not StockKLine.objects.filter(stock=stock, period=bar_size).exists():
        return None, create_error_response(sync_error or "同步 K线数据失败")

    # 3. 从数据库读取 K线数据用于计算
    candles = _fetch_klines_from_db(stock, bar_size, duration)
    if not candles:
        return None, ({"success": False, "message": f"无历史 K线数据: {symbol}"}, 404)
    
    # 4. 计算指标
    indicators, ind_error = calculate_technical_indicators(symbol, duration, bar_size, hist_data=candles)
    if ind_error:
        logger.warning(f"指标计算异常: {symbol}, {ind_error}")
        indicators = indicators or {}

    # 5. 补充附加数据 (基本面、新闻、期权、持股)
    if profile and profile.raw_info:
        indicators['fundamental_data'] = profile.raw_info
    
    indicators['news_data'] = get_cached_news(symbol)
    
    # 获取期权和持股信息 (带缓存控制)
    indicators['options_summary'] = cache.get(f"stock_options_{symbol}") if use_cache else None
    if indicators['options_summary'] is None:
        indicators['options_summary'] = get_options_chain(symbol)
        cache.set(f"stock_options_{symbol}", indicators['options_summary'], timeout=60*60) # 1小时缓存
        
    indicators['holders_data'] = cache.get(f"stock_holders_{symbol}") if use_cache else None
    if indicators['holders_data'] is None:
        indicators['holders_data'] = get_holders(symbol)
        cache.set(f"stock_holders_{symbol}", indicators['holders_data'], timeout=60*60*24) # 24小时缓存

    # 6. 构建并返回结果
    currency_code = profile.raw_info.get("currency") if profile and profile.raw_info else "USD"
    
    result = create_success_response(indicators, None, candles, None, None)
    if currency_code:
        result["currency"] = currency_code
    if stock.name:
        result["stock_name"] = stock.name
    
    return result, None


def fetch_options(symbol: str) -> Dict[str, Any] | None:
    """
    获取期权数据
    """
    return get_options_chain(symbol)


def search_stocks(query: str) -> List[Dict[str, Any]]:
    """
    搜索股票代码 (结合本地数据库和远程 API)
    """
    results = []
    
    # 1. 优先搜索本地数据库 (Stock + StockProfile)
    try:
        from django.db.models import Q
        local_stocks = Stock.objects.filter(
            Q(symbol__icontains=query) | Q(name__icontains=query)
        )[:10]
        
        for stock in local_stocks:
            # 尝试获取 profile 信息
            try:
                profile = stock.profile
                sector = profile.sector
                industry = profile.industry
            except StockProfile.DoesNotExist:
                sector = ""
                industry = ""
                
            results.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'exchange': stock.exchange,
                'type': stock.asset_type,
                'sector': sector,
                'industry': industry,
                'category': 'Cached',
                'score': 1000  # 本地匹配权重最高
            })
            
        if len(results) >= 5:
            return results
    except Exception as e:
        logger.debug(f"本地搜索失败: {e}")

    # 2. 调用 yfinance 搜索补充
    yf_results = yf_search_symbols(query)
    
    # 合并结果
    seen = {r['symbol'] for r in results}
    for item in yf_results:
        if item['symbol'] not in seen:
            results.append(item)
            
    return results
