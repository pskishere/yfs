#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务层模块 - 处理股票分析业务逻辑
包含技术指标计算、交易信号生成、数据获取与缓存等
"""
import os
import sys
import logging
import math
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from django.db import transaction, models
from django.utils import timezone
from django.core.cache import cache

# 在 Python 3.14 下强制使用 protobuf 纯 Python 实现，避免 upb 编译问题
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 尝试删除可能已加载的 protobuf C 扩展模块
if 'google.protobuf.pyext._message' in sys.modules:
    del sys.modules['google.protobuf.pyext._message']
if 'google._upb' in sys.modules:
    del sys.modules['google._upb']

from .models import Stock, StockProfile, StockQuote, StockKLine
from .utils import (
    format_candle_data,
    extract_stock_name,
    create_error_response,
    create_success_response,
    clean_nan_values,
)

from .indicators import (
    calculate_ma, calculate_rsi, calculate_bollinger, calculate_macd,
    calculate_volume, calculate_price_change, calculate_volatility,
    calculate_support_resistance, calculate_kdj, calculate_atr,
    calculate_williams_r, calculate_obv, analyze_trend_strength,
    calculate_fibonacci_retracement, get_trend,
    calculate_cci, calculate_adx, calculate_sar,
    calculate_supertrend, calculate_stoch_rsi, calculate_volume_profile,
    calculate_ichimoku, calculate_cycle_analysis, analyze_yearly_cycles, analyze_monthly_cycles
)

logger = logging.getLogger(__name__)

CURR_SYMBOL_MAP = {
    "USD": "$",
    "CNY": "¥",
    "CNH": "¥",
    "JPY": "¥",
    "HKD": "HK$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
    "SGD": "S$",
    "CHF": "CHF",
    "KRW": "₩",
    "INR": "₹",
}

# -----------------------------------------------------------------------------
# YFinance 基础数据获取函数
# -----------------------------------------------------------------------------

def _resolve_currency_code(info: dict | None, ticker: yf.Ticker) -> str:
    """
    根据yfinance返回的信息推断货币代码，优先info，其次fast_info。
    """
    if info and info.get("currency"):
        return info["currency"]

    try:
        fast_info = ticker.fast_info
        if hasattr(fast_info, "get"):
            code = fast_info.get("currency")
            if code:
                return str(code)
        code = getattr(fast_info, "currency", None)
        if code:
            return str(code)
    except Exception:
        logger.debug("读取 fast_info 货币失败，使用默认USD")

    return "USD"


def _resolve_currency_symbol(currency_code: str) -> str:
    """
    将货币代码映射成常见符号，未知时回退为代码本身。
    """
    if not currency_code:
        return "$"
    return CURR_SYMBOL_MAP.get(currency_code.upper(), currency_code.upper())


def get_stock_info(symbol: str):
    """
    获取股票详细信息 (直接调用 yfinance)
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info:
            return None
        
        currency_code = _resolve_currency_code(info, ticker)
        currency_symbol = _resolve_currency_symbol(currency_code)

        # 返回完整信息以便调用方筛选，同时保留已处理字段
        result = info.copy()
        result.update({
            'symbol': symbol,
            'longName': info.get('longName', info.get('shortName', symbol)),
            'shortName': info.get('shortName', ''),
            'exchange': info.get('exchange', ''),
            'currency': currency_code,
            'currencySymbol': currency_symbol,
            'marketCap': info.get('marketCap', 0),
            'regularMarketPrice': info.get('regularMarketPrice', 0),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
        })
        return result
    except Exception as e:
        logger.error(f"获取股票信息失败: {symbol}, 错误: {e}")
        return None


def search_symbols(query: str) -> List[Dict[str, Any]]:
    """
    通过查询关键词搜索股票代码 (仅从 Yahoo Finance 获取)
    """
    results = []
    
    # 尝试从 Yahoo Finance 获取
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
        }
        from urllib.parse import quote
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote(query)}&quotesCount=10&newsCount=0"
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            quotes = data.get('quotes', [])
            
            for quote_item in quotes:
                symbol = quote_item.get('symbol')
                if symbol:
                    results.append({
                        'symbol': symbol,
                        'name': quote_item.get('longname') or quote_item.get('shortname'),
                        'exchange': quote_item.get('exchange'),
                        'type': quote_item.get('quoteType'),
                        'category': quote_item.get('quoteType', 'Unknown'),
                        'score': quote_item.get('score', 0)
                    })
            if results:
                return results

        # 回退到 yf.Search
        if not results:
            search = yf.Search(query, max_results=10)
            if search.quotes:
                for quote_item in search.quotes:
                    results.append({
                        'symbol': quote_item.get('symbol'),
                        'name': quote_item.get('longname') or quote_item.get('shortname'),
                        'exchange': quote_item.get('exchange'),
                        'type': quote_item.get('quoteType'),
                        'category': quote_item.get('quoteType', 'Unknown'),
                        'score': quote_item.get('score', 0)
                    })
        
        return results
    except Exception as e:
        logger.error(f"搜索股票代码失败: {query}, 错误: {e}")
        return results

# Alias for search_symbols to match views.py usage
search_stocks = search_symbols


def get_fundamental_data(symbol: str):
    """
    获取基本面数据（从yfinance）
    """
    try:
        ticker = yf.Ticker(symbol)
        try:
            info = ticker.info
        except Exception as e:
            logger.debug(f"无法获取股票信息: {symbol}, 错误: {e}")
            return None
        
        if not info or len(info) == 0:
            return None
        
        currency_code = _resolve_currency_code(info, ticker)
        currency_symbol = _resolve_currency_symbol(currency_code)
        shares_outstanding = info.get('sharesOutstanding', 0)
        total_cash = info.get('totalCash', 0)
        cash_per_share = (total_cash / shares_outstanding) if shares_outstanding and shares_outstanding > 0 else 0
        
        fundamental = {
            'CompanyName': info.get('longName', info.get('shortName', symbol)),
            'ShortName': info.get('shortName', ''),
            'Exchange': info.get('exchange', ''),
            'Currency': currency_code,
            'CurrencySymbol': currency_symbol,
            'Sector': info.get('sector', ''),
            'Industry': info.get('industry', ''),
            'Website': info.get('website', ''),
            'Employees': info.get('fullTimeEmployees', 0),
            'BusinessSummary': info.get('longBusinessSummary', ''),
            
            'MarketCap': info.get('marketCap', 0),
            'EnterpriseValue': info.get('enterpriseValue', 0),
            'Price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'PreviousClose': info.get('previousClose', 0),
            '52WeekHigh': info.get('fiftyTwoWeekHigh', 0),
            '52WeekLow': info.get('fiftyTwoWeekLow', 0),
            'SharesOutstanding': shares_outstanding,
            
            'PE': info.get('trailingPE', 0),
            'ForwardPE': info.get('forwardPE', 0),
            'PriceToBook': info.get('priceToBook', 0),
            'PriceToSales': info.get('priceToSalesTrailing12Months', 0),
            'PEGRatio': info.get('pegRatio', 0),
            'EVToRevenue': info.get('enterpriseToRevenue', 0),
            'EVToEBITDA': info.get('enterpriseToEbitda', 0),
            
            'ProfitMargin': info.get('profitMargins', 0),
            'OperatingMargin': info.get('operatingMargins', 0),
            'GrossMargin': info.get('grossMargins', 0),
            'ROE': info.get('returnOnEquity', 0),
            'ROA': info.get('returnOnAssets', 0),
            'ROIC': info.get('returnOnInvestedCapital', 0),
            
            'RevenueTTM': info.get('totalRevenue', 0),
            'RevenuePerShare': info.get('revenuePerShare', 0),
            'NetIncomeTTM': info.get('netIncomeToCommon', 0),
            'EBITDATTM': info.get('ebitda', 0),
            'TotalDebt': info.get('totalDebt', 0),
            'TotalCash': total_cash,
            'CashPerShare': cash_per_share,
            'DebtToEquity': info.get('debtToEquity', 0),
            'CurrentRatio': info.get('currentRatio', 0),
            'QuickRatio': info.get('quickRatio', 0),
            'CashFlow': info.get('operatingCashflow', 0),
            
            'EPS': info.get('trailingEps', 0),
            'ForwardEPS': info.get('forwardEps', 0),
            'BookValuePerShare': info.get('bookValue', 0),
            
            'RevenueGrowth': info.get('revenueGrowth', 0),
            'EarningsGrowth': info.get('earningsGrowth', 0),
            'EarningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth', 0),
            'QuarterlyRevenueGrowth': info.get('quarterlyRevenueGrowth', 0),
            
            'Beta': info.get('beta', 0),
            'AverageVolume': info.get('averageVolume', 0),
            'AverageVolume10days': info.get('averageVolume10days', 0),
            'FloatShares': info.get('floatShares', 0),
        }
        
        return fundamental
    except Exception as e:
        logger.debug(f"获取基本面数据失败（已跳过）: {symbol}")
        return None


def get_options(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取期权数据（所有到期日的期权链）
    """
    try:
        ticker = yf.Ticker(symbol)
        
        expiration_dates = ticker.options
        
        if not expiration_dates:
            logger.info(f"没有期权数据: {symbol}")
            return {'expiration_dates': [], 'chains': {}}
        
        result = {
            'expiration_dates': list(expiration_dates),
            'chains': {}
        }
        
        for exp_date in expiration_dates[:5]:
            try:
                opt_chain = ticker.option_chain(exp_date)
                
                calls = []
                if opt_chain.calls is not None and not opt_chain.calls.empty:
                    for _, row in opt_chain.calls.iterrows():
                        call_record = {}
                        for col in opt_chain.calls.columns:
                            value = row[col]
                            if pd.notna(value):
                                if isinstance(value, pd.Timestamp):
                                    call_record[col] = value.strftime('%Y-%m-%d')
                                elif isinstance(value, (int, float, np.number)):
                                    call_record[col] = float(value)
                                else:
                                    call_record[col] = str(value)
                            else:
                                call_record[col] = None
                        calls.append(call_record)
                
                puts = []
                if opt_chain.puts is not None and not opt_chain.puts.empty:
                    for _, row in opt_chain.puts.iterrows():
                        put_record = {}
                        for col in opt_chain.puts.columns:
                            value = row[col]
                            if pd.notna(value):
                                if isinstance(value, pd.Timestamp):
                                    put_record[col] = value.strftime('%Y-%m-%d')
                                elif isinstance(value, (int, float, np.number)):
                                    put_record[col] = float(value)
                                else:
                                    put_record[col] = str(value)
                            else:
                                put_record[col] = None
                        puts.append(put_record)
                
                result['chains'][exp_date] = {
                    'calls': calls,
                    'puts': puts
                }
                
            except Exception as e:
                logger.warning(f"获取期权链失败: {symbol}, 到期日: {exp_date}, 错误: {e}")
                continue
        
        return result
        
    except Exception as e:
        logger.error(f"获取期权数据失败: {symbol}, 错误: {e}")
        return None

# Alias for get_options to match views.py usage
fetch_options = get_options


def get_news(symbol: str, count: int = 100) -> List[Dict[str, Any]]:
    """
    获取股票新闻，合并 yfinance 和 RSS 源以获取更多数据 (目标 100 条)
    """
    try:
        formatted_news = []
        seen_links = set()
        seen_titles = set()

        # 1. 尝试从 yfinance 获取
        try:
            ticker = yf.Ticker(symbol)
            yf_news = ticker.news
            if yf_news:
                for item in yf_news:
                    if not isinstance(item, dict):
                        continue
                        
                    content = item.get('content') or {}
                    uuid = item.get('uuid') or item.get('id')
                    title = item.get('title') or content.get('title')
                    link = item.get('link')
                    if not link:
                        click_through = content.get('clickThroughUrl') or {}
                        link = click_through.get('url') if isinstance(click_through, dict) else None
                    
                    if not title or not link:
                        continue
                        
                    if link in seen_links or title in seen_titles:
                        continue

                    publisher = item.get('publisher')
                    if not publisher:
                        # 尝试从 content 获取
                        pass

                    provider_publish_time = item.get('providerPublishTime')
                    if not provider_publish_time:
                         pub_date = content.get('pubDate')
                         if pub_date:
                             try:
                                 dt = datetime.strptime(pub_date, '%Y-%m-%dT%H:%M:%SZ')
                                 provider_publish_time = int(dt.timestamp())
                             except:
                                 pass

                    formatted_news.append({
                        'uuid': uuid,
                        'title': title,
                        'publisher': publisher if isinstance(publisher, str) else 'Unknown',
                        'link': link,
                        'providerPublishTime': provider_publish_time,
                        'type': item.get('type', 'STORY'),
                        'thumbnail': item.get('thumbnail', {}),
                        'relatedTickers': item.get('relatedTickers', [symbol])
                    })
                    seen_links.add(link)
                    seen_titles.add(title)
        except Exception as e:
            logger.warning(f"yfinance 获取新闻失败: {symbol}, {e}")

        # 排序
        formatted_news.sort(key=lambda x: x.get('providerPublishTime') or 0, reverse=True)
        
        # 格式化时间
        for item in formatted_news:
            ts = item.get('providerPublishTime')
            if ts:
                item['provider_publish_time_fmt'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            else:
                item['provider_publish_time_fmt'] = ''

        return formatted_news[:count]
    except Exception as e:
        logger.error(f"获取新闻综合流程失败: {symbol}, 错误: {e}")
        return []


def _calculate_period_from_duration(duration: str) -> str:
    """
    根据duration参数计算yfinance的period参数
    """
    try:
        duration = duration.strip().upper()
        if 'Y' in duration:
            years = int(duration.replace('Y', '').strip())
            return f"{max(years, 2)}y"
        elif 'MO' in duration:
            months = int(duration.replace('MO', '').strip())
            years = max((months / 12), 2)
            return f"{int(years)}y"
        elif 'M' in duration: # Handle M as Month
            months = int(duration.replace('M', '').strip())
            years = max((months / 12), 2)
            return f"{int(years)}y"
        elif 'W' in duration:
            weeks = int(duration.replace('W', '').strip())
            years = max((weeks / 52), 2)
            return f"{int(years)}y"
        elif 'D' in duration:
            days = int(duration.replace('D', '').strip())
            years = max((days / 252), 2)
            return f"{int(years)}y"
        else:
            return "2y"
    except Exception as e:
        return "2y"


def _filter_by_duration(df: pd.DataFrame, duration: str) -> pd.DataFrame:
    """
    根据duration参数截取对应周期的数据
    """
    if df is None or df.empty:
        return df
    
    try:
        duration = duration.strip().upper()
        days = 365 * 2
        if 'MO' in duration:
            months = int(duration.replace('MO', '').strip())
            days = months * 22
        elif 'M' in duration:
            months = int(duration.replace('M', '').strip())
            days = months * 22
        elif 'Y' in duration:
            years = int(duration.replace('Y', '').strip())
            days = years * 252
        elif 'W' in duration:
            weeks = int(duration.replace('W', '').strip())
            days = weeks * 5
        elif 'D' in duration:
            days = int(duration.replace('D', '').strip())
        
        if len(df) > days:
            return df.tail(days)
        else:
            return df
    except Exception:
        return df


def _format_historical_data(df: pd.DataFrame):
    """
    格式化历史数据
    """
    result = []
    has_volume = 'Volume' in df.columns
    
    for date, row in df.iterrows():
        if pd.isna(row['Open']) or pd.isna(row['High']) or pd.isna(row['Low']) or pd.isna(row['Close']):
            continue

        date_str = date.strftime('%Y%m%d')
        if pd.notna(date.hour) and (date.hour != 0 or date.minute != 0):
            date_str = date.strftime('%Y%m%d %H:%M:%S')
        
        volume = 0
        if has_volume and pd.notna(row.get('Volume')):
            try:
                volume = int(row['Volume'])
            except (ValueError, TypeError):
                volume = 0
        
        result.append({
            'date': date_str,
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': volume,
            'average': float((row['High'] + row['Low'] + row['Close']) / 3),
            'barCount': 1
        })
    
    return result


def get_historical_data(symbol: str, duration: str = '1 D', 
                       bar_size: str = '5 mins', exchange: str = '', 
                       currency: str = 'USD'):
    """
    获取历史数据（不使用本地缓存，直接调用 yfinance）
    """
    try:
        interval_map = {
            '1 min': '1m',
            '2 mins': '2m',
            '5 mins': '5m',
            '15 mins': '15m',
            '30 mins': '30m',
            '1 hour': '1h',
            '1 day': '1d',
            '1 week': '1wk',
            '1 month': '1mo'
        }
        
        yf_interval = interval_map.get(bar_size, '1d')
        period = _calculate_period_from_duration(duration)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=yf_interval)

        if df.empty:
            return None, {'code': 200, 'message': f'证券 {symbol} 不存在或没有数据'}

        if df.index.tzinfo is not None:
            df.index = df.index.tz_localize(None)

        filtered_df = _filter_by_duration(df, duration)
        return _format_historical_data(filtered_df), None
        
    except Exception as e:
        logger.error(f"获取历史数据失败: {symbol}, 错误: {e}")
        return None, {'code': 500, 'message': str(e)}


# -----------------------------------------------------------------------------
# 核心数据管理函数 (Stock Data Management)
# -----------------------------------------------------------------------------

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
        try:
            profile = stock.profile
        except StockProfile.DoesNotExist:
            profile = None
            
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
        try:
            quote = stock.quote
        except StockQuote.DoesNotExist:
            quote = None
            
        if not quote or quote.is_stale(minutes=1):
            _stock, _, _quote = _refresh_stock_data(symbol)
            if _stock:
                stock = _stock
            if _quote:
                quote = _quote
                
        return stock, quote
    except Exception as e:
        logger.error(f"更新股票行情失败 {symbol}: {e}")
        quote = StockQuote.objects.filter(stock__symbol=symbol).first()
        return stock, quote


def save_stock_info_if_available(symbol: str) -> Dict[str, Any] | None:
    """
    获取并缓存股票名称（使用 ORM），并返回获取到的股票信息
    """
    stock, profile = get_or_update_stock_profile(symbol)
    
    if not stock:
        return None
        
    if profile and profile.raw_info:
        return profile.raw_info
        
    return {
        'symbol': stock.symbol,
        'longName': stock.name,
        'exchange': stock.exchange,
    }


def get_extra_analysis_data(symbol: str) -> Dict[str, Any]:
    """
    获取额外分析数据
    """
    return {}


def _get_start_date_from_duration(duration: str) -> datetime:
    """
    根据 duration 计算起始时间 (用于 DB 查询)
    """
    now = timezone.now()
    duration = duration.strip().lower()
    
    try:
        if duration == 'max':
            return now - timedelta(days=365*50)
        elif 'y' in duration:
            years = int(duration.replace('y', ''))
            return now - timedelta(days=years * 365)
        elif 'mo' in duration:
            months = int(duration.replace('mo', ''))
            return now - timedelta(days=months * 30)
        elif 'm' in duration:
            if duration.endswith('m'):
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
        date_obj = k.date
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


# -----------------------------------------------------------------------------
# 核心分析函数 (Core Analysis Logic)
# -----------------------------------------------------------------------------

def calculate_technical_indicators(symbol: str, duration: str = '1 M', bar_size: str = '1 day', hist_data: List[Dict] = None):
    """
    计算技术指标（基于历史数据）
    """
    if hist_data is None:
        hist_data, error = get_historical_data(symbol, duration, bar_size)
        if error:
            return None, error
    
    if not hist_data or len(hist_data) == 0:
        return None, {"code": "NO_DATA", "message": f"无法获取历史数据: {symbol}"}
    
    if len(hist_data) < 20:
        logger.warning(f"数据不足，部分指标可能无法计算: {symbol} (当前只有{len(hist_data)}条数据，建议至少20条)")
    
    closes = np.array([bar['close'] for bar in hist_data])
    highs = np.array([bar['high'] for bar in hist_data])
    lows = np.array([bar['low'] for bar in hist_data])
    volumes = np.array([bar['volume'] for bar in hist_data])
    
    valid_volumes = volumes[volumes > 0]
    if len(valid_volumes) == 0:
        logger.warning(f"警告: {symbol} 所有成交量数据为 0，成交量相关指标将无法正常计算")
    
    result = {
        'symbol': symbol,
        'current_price': float(closes[-1]),
        'data_points': int(len(closes)),
    }
    
    ma_data = calculate_ma(closes)
    result.update(ma_data)
        
    rsi_data = calculate_rsi(closes)
    result.update(rsi_data)
            
    bb_data = calculate_bollinger(closes)
    result.update(bb_data)
        
    macd_data = calculate_macd(closes)
    result.update(macd_data)
                
    volume_data = calculate_volume(volumes)
    result.update(volume_data)
        
    price_change_data = calculate_price_change(closes)
    result.update(price_change_data)
        
    volatility_data = calculate_volatility(closes)
    result.update(volatility_data)
        
    support_resistance = calculate_support_resistance(closes, highs, lows)
    result.update(support_resistance)
    
    if len(closes) >= 9:
        kdj = calculate_kdj(closes, highs, lows)
        result.update(kdj)
    
    if len(closes) >= 14:
        atr = calculate_atr(closes, highs, lows)
        result['atr'] = atr
        result['atr_percent'] = float((atr / closes[-1]) * 100)
    
    if len(closes) >= 14:
        wr = calculate_williams_r(closes, highs, lows)
        result['williams_r'] = wr
    
    if len(volumes) >= 20:
        obv = calculate_obv(closes, volumes)
        result['obv_current'] = float(obv[-1]) if len(obv) > 0 else 0.0
        result['obv_trend'] = get_trend(obv[-10:]) if len(obv) >= 10 else 'neutral'
    
    trend_info = analyze_trend_strength(closes, highs, lows)
    result.update(trend_info)

    fibonacci_levels = calculate_fibonacci_retracement(highs, lows)
    result.update(fibonacci_levels)

    if len(closes) >= 14:
        cci_data = calculate_cci(closes, highs, lows)
        result.update(cci_data)
    
    if len(closes) >= 28:
        adx_data = calculate_adx(closes, highs, lows)
        result.update(adx_data)
    
    if len(closes) >= 10:
        sar_data = calculate_sar(closes, highs, lows)
        result.update(sar_data)

    if len(closes) >= 11:
        st_data = calculate_supertrend(closes, highs, lows)
        result.update(st_data)
        
    if len(closes) >= 28:
        stoch_rsi_data = calculate_stoch_rsi(closes)
        result.update(stoch_rsi_data)
        
    if len(closes) >= 20:
        vp_data = calculate_volume_profile(closes, highs, lows, volumes)
        result.update(vp_data)

    if len(closes) >= 52:
        ichimoku_data = calculate_ichimoku(closes, highs, lows)
        result.update(ichimoku_data)

    # 尝试获取基本面、新闻、期权数据
    try:
        fundamental_data = get_fundamental_data(symbol)
        if fundamental_data:
            result['fundamental_data'] = fundamental_data
    except Exception:
        result['fundamental_data'] = None

    try:
        news_data = get_news(symbol)
        result['news_data'] = news_data or []
    except Exception:
        result['news_data'] = []

    try:
        options_data = get_options(symbol)
        result['options_data'] = options_data
    except Exception:
        result['options_data'] = None

    if len(closes) >= 30:
        timestamps = []
        if hist_data:
            for bar in hist_data:
                date_val = bar.get('date') or bar.get('time', '')
                date_str = str(date_val) if date_val is not None else ''
                
                if date_str:
                    try:
                        if len(date_str) == 8 and date_str.isdigit():
                            dt = datetime.strptime(date_str, '%Y%m%d')
                            timestamps.append(dt.strftime('%Y-%m-%d'))
                        elif ' ' in date_str:
                            dt = datetime.strptime(date_str, '%Y%m%d %H:%M:%S')
                            timestamps.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
                        else:
                            timestamps.append(date_str)
                    except Exception:
                        timestamps.append(date_str)
                else:
                    timestamps.append(None)
        
        cycle_data = calculate_cycle_analysis(
            closes, highs, lows,
            volumes=volumes if len(valid_volumes) > 0 else None,
            timestamps=timestamps if timestamps else None,
            use_adaptive=True,
            use_wavelet=True
        )
        result.update(cycle_data)
        
        yearly_result = analyze_yearly_cycles(closes, highs, lows, timestamps if timestamps else None)
        monthly_result = analyze_monthly_cycles(closes, highs, lows, timestamps if timestamps else None)
        result['yearly_cycles'] = yearly_result.get('yearly_stats', [])
        result['monthly_cycles'] = monthly_result.get('monthly_stats', [])
        
    return result, None


def perform_analysis(symbol: str, duration: str, bar_size: str, use_cache: bool = True) -> Tuple[Dict[str, Any] | None, Tuple[Dict[str, Any], int] | None]:
    """
    执行技术分析：实时计算，基于 StockKLine 和 StockProfile
    """
    # 1. 确保基础信息和实时行情是最新的
    if not use_cache:
        _refresh_stock_data(symbol)
    
    stock, profile = get_or_update_stock_profile(symbol)
    if not stock:
        return None, ({"success": False, "message": f"股票不存在: {symbol}"}, 404)
        
    # 2. 检查并获取 K线数据
    need_fetch_history = not use_cache
    
    if use_cache:
        last_kline = StockKLine.objects.filter(stock=stock, period=bar_size).order_by('-date').first()
        if not last_kline:
            need_fetch_history = True
        else:
            diff = timezone.now() - last_kline.date
            if bar_size == '1d' and diff.days > 3:
                 need_fetch_history = True
            elif bar_size in ['1m', '5m', '1h'] and diff.total_seconds() > 3600:
                 need_fetch_history = True
            
            if not need_fetch_history and bar_size == '1d':
                try:
                    target_start_date = _get_start_date_from_duration(duration)
                    effective_start_date = target_start_date
                    
                    ipo_timestamp = None
                    if profile and profile.raw_info:
                        ipo_timestamp = profile.raw_info.get('firstTradeDateEpochUtc')
                    
                    if ipo_timestamp:
                        ipo_date = datetime.fromtimestamp(ipo_timestamp, tz=timezone.utc)
                        if ipo_date > effective_start_date:
                            effective_start_date = ipo_date
                    
                    first_kline = StockKLine.objects.filter(stock=stock, period=bar_size).order_by('date').first()
                    
                    if first_kline:
                        if ipo_timestamp and first_kline.date > effective_start_date + timedelta(days=10):
                            logger.info(f"数据头部缺失 {symbol}: 最早 {first_kline.date}, 预期 {effective_start_date}. 触发更新.")
                            need_fetch_history = True
                        
                        if not need_fetch_history:
                            check_start_date = first_kline.date
                            actual_count = StockKLine.objects.filter(stock=stock, period=bar_size, date__gte=check_start_date).count()
                            
                            days_diff = (timezone.now() - check_start_date).days
                            if days_diff > 30:
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
        hist_data_raw, hist_error = get_historical_data(symbol, duration, bar_size)
        if hist_data_raw and not hist_error:
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
                    
                    open_val = row.get('open')
                    high_val = row.get('high')
                    low_val = row.get('low')
                    close_val = row.get('close')
                    
                    if any(val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))) 
                           for val in [open_val, high_val, low_val, close_val]):
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
    candles = _fetch_klines_from_db(stock, bar_size, duration)
    
    # 4. 计算指标
    indicators, ind_error = calculate_technical_indicators(symbol, duration, bar_size, hist_data=candles)
    
    if ind_error:
        logger.warning(f"指标计算失败: {symbol}, {ind_error}")
        indicators = {}

    # 5. 补充数据 (新闻、基本面)
    if profile and profile.raw_info:
        indicators['fundamental_data'] = profile.raw_info
    
    indicators['news_data'] = get_cached_news(symbol)

    # 6. 构建返回结果
    extra_data = get_extra_analysis_data(symbol)
    
    payload_extra = extra_data or {}
    
    result = {
        'symbol': stock.symbol,
        'name': stock.name,
        'timestamp': timezone.now().isoformat(),
        'candles': format_candle_data(candles),
        'indicators': indicators,
        'extra': payload_extra
    }
    
    return result, None
