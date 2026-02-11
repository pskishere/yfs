#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YFinance数据获取模块 - 从yfinance获取股票数据
包含所有可用的yfinance功能：股票信息、历史数据、基本面、期权、分红、持股、内部交易、新闻等
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from django.db import models

# 在 Python 3.14 下强制使用 protobuf 纯 Python 实现，避免 upb 编译问题
# 必须在导入任何可能使用 protobuf 的模块之前设置
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 尝试删除可能已加载的 protobuf C 扩展模块
import sys
if 'google.protobuf.pyext._message' in sys.modules:
    del sys.modules['google.protobuf.pyext._message']
if 'google._upb' in sys.modules:
    del sys.modules['google._upb']

import numpy as np
import pandas as pd
import pytz
import requests
import xml.etree.ElementTree as ET
import threading
import queue

# 直接导入 yfinance，如果失败会在导入时抛出异常
import yfinance as yf

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


def sanitize_data(data: Any) -> Any:
    """
    递归清理数据中的 NaN 和 Inf，使其符合 JSON 规范。
    NaN -> None, Inf -> None
    """
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(v) for v in data]
    elif isinstance(data, (float, np.float64, np.float32)):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
    elif isinstance(data, (int, np.int64, np.int32)):
        return int(data)
    elif isinstance(data, (pd.Timestamp, datetime)):
        return data.isoformat()
    return data


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
    获取股票详细信息
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info:
            return None
        
        # 尝试获取更实时的价格 (yfinance live 功能)
        live_price = get_live_price(symbol)
        
        currency_code = _resolve_currency_code(info, ticker)
        currency_symbol = _resolve_currency_symbol(currency_code)

        # 返回完整信息以便调用方筛选，同时保留已处理字段
        result = info.copy()
        
        # 优先使用 live 价格
        current_price = live_price if live_price else (info.get('currentPrice') or info.get('regularMarketPrice') or 0.0)
        
        # 如果 live 价格和 info 价格都拿不到，尝试 fast_info
        if not current_price or current_price == 0.0:
            try:
                fast_price = ticker.fast_info.get('last_price')
                if fast_price:
                    current_price = fast_price
            except Exception:
                pass
        
        result.update({
            'symbol': symbol,
            'longName': info.get('longName', info.get('shortName', symbol)),
            'shortName': info.get('shortName', ''),
            'exchange': info.get('exchange', ''),
            'currency': currency_code,
            'currencySymbol': currency_symbol,
            'marketCap': info.get('marketCap', 0),
            'regularMarketPrice': current_price,
            'currentPrice': current_price,
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
            'is_live_price': live_price is not None
        })
        return sanitize_data(result)
    except Exception as e:
        logger.error(f"获取股票信息失败: {symbol}, 错误: {e}")
        return None


def get_live_price(symbol: str, timeout: float = 2.0) -> float | None:
    """
    通过 yfinance 的 WebSocket (live.py) 实时获取股票价格
    
    Args:
        symbol: 股票代码
        timeout: 等待实时数据的超时时间（秒）
        
    Returns:
        最新价格或 None
    """
    # 如果是某些不支持 live 的代码，可以直接返回
    if not symbol or '^' in symbol: # 指数通常在 info 中已经很快了
        return None

    res_queue = queue.Queue()
    
    def on_message(data):
        # data 是 PricingData 对象，包含 price 属性
        try:
            price = getattr(data, 'price', None)
            if price:
                res_queue.put(price)
        except Exception:
            pass

    ws = None
    # 使用 monkey-patch 方式外科手术式修复 yfinance WebSocket 代理问题
    from unittest.mock import patch
    import yfinance.live
    import websockets.sync.client
    
    original_connect = websockets.sync.client.connect
    
    def no_proxy_connect(*args, **kwargs):
        kwargs['proxy'] = None
        return original_connect(*args, **kwargs)
        
    try:
        # 针对 yfinance.live 中已经导入的 sync_connect 进行 patch
        with patch('yfinance.live.sync_connect', side_effect=no_proxy_connect):
            ws = yf.WebSocket()
            ws.subscribe([symbol])
    except Exception as e:
        logger.debug(f"Surgical proxy bypass failed for {symbol}: {e}")
        try:
            ws = yf.WebSocket()
            ws.subscribe([symbol])
        except Exception:
            return None

    try:
        # 在子线程中监听，避免主线程阻塞过久
        def listen_thread():
            try:
                ws.listen(on_message)
            except Exception:
                pass

        t = threading.Thread(target=listen_thread, daemon=True)
        t.start()
        
        # 等待队列中的数据
        price = res_queue.get(timeout=timeout)
        return price
    except queue.Empty:
        # 超时未获取到实时数据
        return None
    except Exception as e:
        logger.debug(f"获取实时价格失败 {symbol}: {e}")
        return None
    finally:
        if ws:
            try:
                ws.close()
            except Exception:
                pass


def search_symbols(query: str) -> List[Dict[str, Any]]:
    """
    通过查询关键词搜索股票代码 (仅从 Yahoo Finance 获取)
    
    Args:
        query: 关键词，如 "Apple", "腾讯", "AAPL"
        
    Returns:
        匹配的股票列表
    """
    results = []
    
    # 尝试从 Yahoo Finance 获取
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
        }
        # 使用 quote 对中文进行编码
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

        # 回退到 yf.Search (虽然它可能也会被 rate limit)
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





def get_fundamental_data(symbol: str):
    """
    获取基本面数据（从yfinance）
    返回公司财务数据、估值指标、财务报表、资产负债表、现金流量表等
    """
    try:
        ticker = yf.Ticker(symbol)
        
        try:
            info = ticker.info
        except Exception as e:
            logger.debug(f"无法获取股票信息: {symbol}, 错误: {e}")
            return None
        
        if not info or len(info) == 0:
            logger.debug(f"股票信息为空: {symbol}")
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
        
        return sanitize_data(fundamental)
        
    except Exception as e:
        logger.debug(f"获取基本面数据失败（已跳过）: {symbol}")
        return None




def _calculate_period_from_duration(duration: str) -> str:
    """
    根据duration参数计算yfinance的period参数
    duration是最大值，但至少2年起步
    
    Args:
        duration: 数据周期，如 '1M', '3M', '1Y', '2Y'
    
    Returns:
        yfinance的period字符串，如 '2y', '3y'等
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
        elif 'M' in duration:
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
        logger.warning(f"解析duration失败: {duration}, 错误: {e}，使用默认2y")
        return "2y"


def _filter_by_duration(df: pd.DataFrame, duration: str) -> pd.DataFrame:
    """
    根据duration参数截取对应周期的数据
    
    Args:
        df: 完整的历史数据DataFrame
        duration: 数据周期，如 '1M', '3M', '1Y'
    
    Returns:
        截取后的DataFrame
    """
    if df is None or df.empty:
        return df
    
    try:
        duration = duration.strip().upper()
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
        else:
            return df
        
        if len(df) > days:
            return df.tail(days)
        else:
            return df
    except Exception as e:
        logger.warning(f"解析duration失败: {duration}, 错误: {e}，返回全部数据")
        return df


def _format_historical_data(df: pd.DataFrame):
    """
    格式化历史数据
    """
    result = []
    has_volume = 'Volume' in df.columns
    
    for date, row in df.iterrows():
        # 检查 OHLC 是否有效，如果无效则跳过
        if pd.isna(row['Open']) or pd.isna(row['High']) or pd.isna(row['Low']) or pd.isna(row['Close']):
            continue

        date_str = date.strftime('%Y%m%d')
        if pd.notna(date.hour):
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
    duration: 数据周期，如 '1 D', '1 W', '1 M', '3 M', '1 Y'
    bar_size: K线周期，如 '1 min', '5 mins', '1 hour', '1 day'
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
            logger.warning(f"无法获取历史数据: {symbol}")
            return None, {'code': 200, 'message': f'证券 {symbol} 不存在或没有数据'}

        if 'Volume' not in df.columns:
            logger.warning(f"警告: {symbol} 的数据中没有 Volume 列，成交量相关指标将无法计算")
        elif df['Volume'].isna().all():
            logger.warning(f"警告: {symbol} 的成交量数据全部为 NaN，成交量相关指标将无法计算")
        elif df['Volume'].isna().any():
            nan_count = df['Volume'].isna().sum()
            logger.warning(f"警告: {symbol} 有 {nan_count} 条数据的成交量为 NaN，将使用 0 代替")

        if df.index.tzinfo is not None:
            df.index = df.index.tz_localize(None)

        filtered_df = _filter_by_duration(df, duration)
        logger.info(f"已获取历史数据: {symbol}, {len(filtered_df)} 条")
        return sanitize_data(_format_historical_data(filtered_df)), None
        
    except Exception as e:
        logger.error(f"获取历史数据失败: {symbol}, 错误: {e}")
        return None, {'code': 500, 'message': str(e)}


def get_news(symbol: str) -> List[Dict[str, Any]]:
    """
    获取股票新闻
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        results = []
        for item in news:
            content = item.get('content', {})
            # 处理新旧两种格式
            title = content.get('title') or item.get('title')
            publisher = (content.get('provider') or {}).get('displayName') or item.get('publisher')
            link = (content.get('clickThroughUrl') or {}).get('url') or item.get('link')
            pub_time_str = content.get('pubDate') or item.get('providerPublishTime')
            summary = content.get('summary') or content.get('description') or item.get('summary') or item.get('description', '')
            
            # 格式化发布时间
            pub_time_fmt = ""
            if pub_time_str:
                try:
                    if isinstance(pub_time_str, (int, float)):
                        dt = datetime.fromtimestamp(pub_time_str)
                        pub_time_fmt = dt.strftime('%Y-%m-%d')
                    else:
                        # 尝试解析 ISO 格式或其他格式
                        from dateutil import parser
                        dt = parser.parse(str(pub_time_str))
                        pub_time_fmt = dt.strftime('%Y-%m-%d')
                except Exception:
                    pub_time_fmt = str(pub_time_str)
            
            # 处理缩略图
            thumbnail = None
            thumb_data = content.get('thumbnail') or item.get('thumbnail')
            if thumb_data:
                resolutions = (thumb_data or {}).get('resolutions', [])
                if resolutions:
                    thumbnail = (resolutions[0] or {}).get('url')

            results.append({
                'uuid': item.get('id') or item.get('uuid'),
                'title': title,
                'publisher': publisher,
                'link': link,
                'provider_publish_time': pub_time_str,
                'provider_publish_time_fmt': pub_time_fmt,
                'type': content.get('contentType') or item.get('type'),
                'summary': summary,
                'thumbnail': thumbnail,
                'related_tickers': item.get('relatedTickers', []) # 暂时保持原样，如果新格式没有则为空
            })
        return sanitize_data(results)
    except Exception as e:
        logger.error(f"获取新闻失败: {symbol}, {e}")
        return []


def crawl_news_article(url: str) -> Dict[str, Any]:
    """
    使用 newspaper3k 抓取新闻详情
    参考: https://github.com/pskishere/gos/blob/main/src/news_crawler.py
    """
    try:
        from newspaper import Article, Config
        
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 10
        
        article = Article(url, config=config)
        article.download()
        article.parse()
        
        # 如果需要 NLP (摘要、关键词)，需要先下载 nltk 数据
        try:
            article.nlp()
        except Exception as e:
            logger.debug(f"NLP 分析失败 (可能缺失 nltk 数据): {e}")

        return {
            'title': article.title,
            'text': article.text,
            'authors': article.authors,
            'publish_date': article.publish_date.isoformat() if article.publish_date else None,
            'top_image': article.top_image,
            'movies': article.movies,
            'keywords': article.keywords,
            'summary': article.summary,
        }
    except Exception as e:
        logger.error(f"抓取新闻详情失败: {url}, {e}")
        return {}


def get_options_chain(symbol: str) -> Dict[str, Any]:
    """
    获取完整期权链数据
    """
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            logger.info(f"{symbol} 没有期权到期日数据")
            return {'expirations': [], 'calls': [], 'puts': []}
            
        # 默认获取最近一个到期日的数据
        latest_expiry = expirations[0]
        try:
            opt = ticker.option_chain(latest_expiry)
        except Exception as e:
            logger.error(f"获取 {symbol} 到期日 {latest_expiry} 的期权链失败: {e}")
            return {'expirations': list(expirations), 'calls': [], 'puts': []}
        
        calls = opt.calls.to_dict(orient='records') if not opt.calls.empty else []
        puts = opt.puts.to_dict(orient='records') if not opt.puts.empty else []
        
        result = {
            'expirations': list(expirations),
            'current_expiry': latest_expiry,
            'calls': calls,
            'puts': puts
        }
        return sanitize_data(result)
    except Exception as e:
        logger.error(f"获取期权链总体失败: {symbol}, {e}")
        return {'expirations': [], 'calls': [], 'puts': []}


def get_holders(symbol: str) -> Dict[str, Any]:
    """
    获取持股信息
    """
    try:
        ticker = yf.Ticker(symbol)
        major = ticker.major_holders.to_dict() if ticker.major_holders is not None else {}
        inst = ticker.institutional_holders.to_dict(orient='records') if ticker.institutional_holders is not None else []
        return sanitize_data({
            'major_holders': major,
            'institutional_holders': inst
        })
    except Exception as e:
        logger.error(f"获取持股信息失败: {symbol}, {e}")
        return {}


def get_financials(symbol: str) -> Dict[str, Any]:
    """
    获取财务报表摘要
    """
    try:
        ticker = yf.Ticker(symbol)
        result = {
            'income_stmt': ticker.income_stmt.to_dict() if ticker.income_stmt is not None else {},
            'balance_sheet': ticker.balance_sheet.to_dict() if ticker.balance_sheet is not None else {},
            'cashflow': ticker.cashflow.to_dict() if ticker.cashflow is not None else {},
        }
        return sanitize_data(result)
    except Exception as e:
        logger.error(f"获取财务数据失败: {symbol}, {e}")
        return {}

