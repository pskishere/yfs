"""
服务层模块 - 处理股票分析业务逻辑
"""
import logging
import math
from typing import Any, Dict, Tuple, List

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from .analysis import (
    calculate_technical_indicators,
)
from datetime import datetime, timedelta
from .models import Stock, StockProfile, StockQuote, StockKLine
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
    search_symbols as yf_search_symbols,
)

logger = logging.getLogger(__name__)


def _refresh_stock_data(symbol: str) -> Tuple[Stock | None, StockProfile | None, StockQuote | None]:
    """
    [内部函数] 从 yfinance 获取最新数据，并同时更新 Stock, Profile, Quote
    """
    try:
        info = get_stock_info(symbol)
        if not info:
            return None, None, None
            
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
        
        profile, created = StockProfile.objects.update_or_create(
            stock=stock,
            defaults=profile_data
        )
        
        # 3. 更新/创建 Quote
        # 提取 Quote 相关字段
        quote_data = {
            'price': info.get('currentPrice') or info.get('regularMarketPrice') or 0.0,
            'change': 0.0, # yfinance info 这里的 change 可能不准，或者需要计算
            'change_pct': 0.0,
            'volume': info.get('volume') or info.get('regularMarketVolume') or 0,
            'prev_close': info.get('previousClose') or 0.0,
            'open_price': info.get('open') or info.get('regularMarketOpen') or 0.0,
            'day_high': info.get('dayHigh') or info.get('regularMarketDayHigh') or 0.0,
            'day_low': info.get('dayLow') or info.get('regularMarketDayLow') or 0.0,
        }
        
        # 简单计算涨跌幅 (如果 API 没给)
        if quote_data['prev_close'] and quote_data['price']:
            quote_data['change'] = quote_data['price'] - quote_data['prev_close']
            quote_data['change_pct'] = (quote_data['change'] / quote_data['prev_close']) * 100
            
        quote, created = StockQuote.objects.update_or_create(
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
        
        # 尝试获取 Profile
        try:
            profile = stock.profile
        except StockProfile.DoesNotExist:
            profile = None
            
        # 如果不存在或已过期，则调用统一刷新
        if not profile or profile.is_stale(hours=24):
            _stock, _profile, _ = _refresh_stock_data(symbol)
            if _stock:
                stock = _stock
            if _profile:
                profile = _profile
                
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
        
        # 尝试获取 Quote
        try:
            quote = stock.quote
        except StockQuote.DoesNotExist:
            quote = None
            
        # 如果不存在或已过期(1分钟)，则调用统一刷新
        if not quote or quote.is_stale(minutes=1):
            _stock, _, _quote = _refresh_stock_data(symbol)
            if _stock:
                stock = _stock
            if _quote:
                quote = _quote
                
        return stock, quote
    except Exception as e:
        logger.error(f"更新股票行情失败 {symbol}: {e}")
        # 尝试返回旧数据
        quote = StockQuote.objects.filter(stock__symbol=symbol).first()
        return stock, quote



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


def get_extra_analysis_data(symbol: str) -> Dict[str, Any]:
    """
    获取额外分析数据
    """
    return {}


def _get_start_date_from_duration(duration: str) -> datetime:
    """
    根据 duration 计算起始时间
    """
    now = timezone.now()
    duration = duration.strip().lower()
    
    try:
        if duration == 'max':
            return now - timedelta(days=365*50) # 50 years ago
        elif 'y' in duration:
            years = int(duration.replace('y', ''))
            return now - timedelta(days=years * 365)
        elif 'mo' in duration: # 1mo
            months = int(duration.replace('mo', ''))
            return now - timedelta(days=months * 30)
        elif 'm' in duration: # 1m could be minute or month, but standard duration usually uses 'mo' for month or 'm' for minute. 
                              # yfinance uses '1mo'. If '1m' is passed as duration, it's ambiguous.
                              # Assuming 'm' in duration context (like '1m', '3m') means month if not standard yfinance minute.
                              # But standard durations are 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            if duration.endswith('m'):
                 # Check if it's minute (usually not for duration) or month
                 # Let's assume month for safety in this context if it's > 10? No.
                 # Let's treat 'm' as month here for compatibility
                 months = int(duration.replace('m', ''))
                 return now - timedelta(days=months * 30)
        elif 'd' in duration:
            days = int(duration.replace('d', ''))
            return now - timedelta(days=days)
        elif 'wk' in duration:
            weeks = int(duration.replace('wk', ''))
            return now - timedelta(weeks=weeks)
        elif 'w' in duration:
            weeks = int(duration.replace('w', ''))
            return now - timedelta(weeks=weeks)
            
        # Default fallback
        return now - timedelta(days=365)
    except:
        return now - timedelta(days=365)


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
    for k in klines:
        # Format date similar to yfinance
        # StockKLine.date is DateTimeField (aware)
        date_obj = k.date
        if period in ['1d', '5d', '1wk', '1mo', '3mo']: # Daily+ usually returned as YYYYMMDD or YYYY-MM-DD
             # But yfinance history returns datetime index.
             # format_candle_data expects specific format?
             # Let's check format_candle_data usage. It expects 'Date' or 'date' key.
             pass
        
        # We construct the list of dicts that format_candle_data expects OR return formatted directly.
        # format_candle_data takes raw yfinance list.
        # Here we return formatted directly to match what perform_analysis returns in 'candles'
        
        date_str = date_obj.strftime('%Y-%m-%d')
        if period in ['1m', '2m', '5m', '15m', '30m', '60m', '1h']:
             date_str = date_obj.strftime('%Y-%m-%d %H:%M:%S')

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
            news = get_news(symbol)
            if news:
                cache.set(key, news, timeout=60*15) # 15分钟缓存
        except Exception as e:
            logger.warning(f"获取新闻失败: {symbol}, {e}")
            news = []
    return news or []


def perform_analysis(symbol: str, duration: str, bar_size: str, use_cache: bool = True) -> Tuple[Dict[str, Any] | None, Tuple[Dict[str, Any], int] | None]:
    """
    执行技术分析：实时计算，基于 StockKLine 和 StockProfile
    
    Args:
        symbol: 股票代码
        duration: 数据周期
        bar_size: K线周期
        use_cache: 是否允许使用现有 DB 数据（如果足够新）
        
    Returns:
        (分析结果字典, 错误响应元组) 或 (None, 错误响应元组)
    """
    # 1. 确保基础信息和实时行情是最新的
    # get_or_update_* 内部会检查 is_stale，如果 use_cache=False，我们可能需要强制刷新？
    # 目前 get_or_update_* 的逻辑是自动的。如果需要强制，可以在这里显式调用 _refresh_stock_data
    if not use_cache:
        _refresh_stock_data(symbol)
    
    stock, profile = get_or_update_stock_profile(symbol)
    if not stock:
        return None, ({"success": False, "message": f"股票不存在: {symbol}"}, 404)
        
    # 2. 检查并获取 K线数据
    # 如果 use_cache=False，或者 DB 中没有足够新的数据，则从 API 获取并归档
    need_fetch_history = not use_cache
    
    if use_cache:
        last_kline = StockKLine.objects.filter(stock=stock, period=bar_size).order_by('-date').first()
        if not last_kline:
            need_fetch_history = True
        else:
            # 简单检查时效性：如果是日线，且最后一条不是今天(或昨天)，则刷新
            # 这里简化处理：如果是日线，最后一条数据的日期与当前日期相差超过1天（考虑周末），则刷新
            # 更精确的逻辑交给 yfinance 处理，这里我们如果发现数据太旧就触发 fetch
            diff = timezone.now() - last_kline.date
            if bar_size == '1d' and diff.days > 3: # 考虑到周末，放宽一点
                 need_fetch_history = True
            elif bar_size in ['1m', '5m', '1h'] and diff.total_seconds() > 3600: # 1小时没更新
                 need_fetch_history = True
            
            # 增加数据连续性检查 (仅针对日线)
            if not need_fetch_history and bar_size == '1d':
                try:
                    # 1. 检查头部缺失 (Missing Head)
                    target_start_date = _get_start_date_from_duration(duration)
                    effective_start_date = target_start_date
                    
                    # 尝试利用 IPO 日期优化起始时间，避免对新股死循环请求
                    ipo_timestamp = None
                    if profile and profile.raw_info:
                        ipo_timestamp = profile.raw_info.get('firstTradeDateEpochUtc')
                    
                    if ipo_timestamp:
                        # ipo_timestamp 是 UTC 秒数
                        ipo_date = datetime.fromtimestamp(ipo_timestamp, tz=timezone.utc)
                        if ipo_date > effective_start_date:
                            effective_start_date = ipo_date
                    
                    # 获取 DB 中最早的一条记录
                    first_kline = StockKLine.objects.filter(stock=stock, period=bar_size).order_by('date').first()
                    
                    if first_kline:
                        # 允许 10 天的缓冲
                        # 仅当明确知道 IPO 日期时，才严格检查头部缺失，防止死循环
                        if ipo_timestamp and first_kline.date > effective_start_date + timedelta(days=10):
                            logger.info(f"数据头部缺失 {symbol}: 最早 {first_kline.date}, 预期 {effective_start_date}. 触发更新.")
                            need_fetch_history = True
                        
                        # 2. 检查内部断层 (Internal Gaps)
                        if not need_fetch_history:
                            # 检查从现有数据的起点到现在的连续性
                            check_start_date = first_kline.date
                            actual_count = StockKLine.objects.filter(stock=stock, period=bar_size, date__gte=check_start_date).count()
                            
                            days_diff = (timezone.now() - check_start_date).days
                            # 估算交易日: 5/7 ≈ 0.71, 扣除节假日, 使用 0.65 作为安全下限
                            if days_diff > 30: # 只有跨度超过30天才检查，避免短期波动误判
                                expected_min = int(days_diff * 0.65)
                                if actual_count < expected_min:
                                    logger.info(f"数据断层检测 {symbol}: 实有 {actual_count}, 预期最少 {expected_min} (跨度 {days_diff} 天). 触发更新.")
                                    need_fetch_history = True
                    else:
                        need_fetch_history = True
                except Exception as e:
                    logger.warning(f"数据连续性检查异常: {e}")

    hist_error = None
    if need_fetch_history:
        # 获取历史数据
        hist_data_raw, hist_error = get_historical_data(symbol, duration, bar_size)
        if hist_data_raw and not hist_error:
             # 归档到 DB
             try:
                kline_objs = []
                for row in hist_data_raw:
                    date_str = row.get('date')
                    date_val = None
                    try:
                        if date_str:
                            if len(date_str) == 8:
                                dt = datetime.strptime(date_str, '%Y%m%d')
                            else:
                                dt = datetime.strptime(date_str, '%Y%m%d %H:%M:%S')
                            
                            if timezone.is_naive(dt):
                                date_val = timezone.make_aware(dt)
                            else:
                                date_val = dt
                    except Exception:
                        continue

                    if not date_val:
                        continue
                    
                    # 检查 OHLC 是否有效
                    open_val = row.get('open')
                    high_val = row.get('high')
                    low_val = row.get('low')
                    close_val = row.get('close')
                    
                    # 过滤掉 None 或 NaN/Inf
                    if any(val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))) 
                           for val in [open_val, high_val, low_val, close_val]):
                        logger.warning(f"跳过无效 K线数据: {symbol} {date_val} open={open_val} high={high_val} low={low_val} close={close_val}")
                        continue
                    
                    vol = row.get('volume', 0)
                    try:
                        vol = int(vol)
                    except:
                        vol = 0

                    kline_objs.append(StockKLine(
                        stock=stock,
                        date=date_val,
                        period=bar_size,
                        open=open_val,
                        high=high_val,
                        low=low_val,
                        close=close_val,
                        volume=vol
                    ))
                
                StockKLine.objects.bulk_create(
                    kline_objs, 
                    update_conflicts=True,
                    unique_fields=['stock', 'date', 'period'],
                    update_fields=['open', 'high', 'low', 'close', 'volume']
                )
                logger.info(f"已归档 K线数据: {symbol}, 数量: {len(kline_objs)}")
             except Exception as e:
                logger.warning(f"归档 K线数据失败: {symbol}, 错误: {e}")

    if hist_error and not StockKLine.objects.filter(stock=stock).exists():
        return None, create_error_response(hist_error)

    # 3. 从 DB 读取 K线数据用于计算
    # 注意：这里我们重新从 DB 读取，确保使用统一的数据源
    candles = _fetch_klines_from_db(stock, bar_size, duration)
    
    # 转换为 analysis 模块需要的格式 (dict list)
    # analysis 模块需要: close, high, low, volume
    # candles 格式: time, open, high, low, close, volume
    # 转换一下 key 即可，其实大部分 key 是一样的，只是 analysis 可能用 'date' 或 'time'
    # calculate_technical_indicators 内部也是从 dict 取值
    
    # 4. 计算指标
    indicators, ind_error = calculate_technical_indicators(symbol, duration, bar_size, hist_data=candles)
    
    if ind_error:
        # 如果计算失败，但我们有 candles，还是返回 candles
        # 但通常 calculate_technical_indicators 会处理空数据
        logger.warning(f"指标计算失败: {symbol}, {ind_error}")
        indicators = {}

    # 5. 补充数据 (新闻、基本面)
    # 基本面从 Profile 获取
    if profile and profile.raw_info:
        indicators['fundamental_data'] = profile.raw_info
    
    # 新闻从缓存获取
    indicators['news_data'] = get_cached_news(symbol)

    # 6. 构建返回结果
    extra_data = get_extra_analysis_data(symbol)
    currency_code = profile.raw_info.get("currency") if profile and profile.raw_info else "USD"
    
    payload_extra = extra_data or {}
    payload_extra["currency"] = currency_code
    
    stock_name = stock.name

    result = create_success_response(indicators, None, candles, None, None)
    if currency_code:
        result["currency"] = currency_code
    if stock_name:
        result["stock_name"] = stock_name
    if payload_extra:
        result["extra_data"] = payload_extra
    
    result["cached"] = use_cache # 标记一下意图
    
    return result, None


def fetch_options(symbol: str) -> Dict[str, Any] | None:
    """
    获取期权数据
    """
    return get_options(symbol)


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
