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
        
        return fundamental
        
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
        return _format_historical_data(filtered_df), None
        
    except Exception as e:
        logger.error(f"获取历史数据失败: {symbol}, 错误: {e}")
        return None, {'code': 500, 'message': str(e)}


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
                
                logger.info(f"已获取期权链: {symbol}, 到期日: {exp_date}, Calls: {len(calls)}, Puts: {len(puts)}")
                
            except Exception as e:
                logger.warning(f"获取期权链失败: {symbol}, 到期日: {exp_date}, 错误: {e}")
                continue
        
        logger.info(f"已获取期权数据: {symbol}, 共{len(result['chains'])}个到期日")
        return result
        
    except Exception as e:
        logger.error(f"获取期权数据失败: {symbol}, 错误: {e}")
        return None


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
                logger.info(f"yfinance 返回了 {len(yf_news)} 条原始新闻数据: {symbol}")
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

                    # 安全地获取发布者
                    publisher = item.get('publisher')
                    if not publisher:
                        provider = content.get('provider') or {}
                        publisher = provider.get('displayName') if isinstance(provider, dict) else None
                    
                    # 处理发布时间
                    publish_time = item.get('providerPublishTime')
                    if publish_time is None:
                        pub_date_str = content.get('pubDate')
                        if pub_date_str:
                            try:
                                dt = datetime.strptime(pub_date_str, '%Y-%m-%dT%H:%M:%SZ')
                                publish_time = int(dt.timestamp())
                            except Exception:
                                publish_time = 0
                        else:
                            publish_time = 0

                    formatted_item = {
                        'uuid': uuid,
                        'title': title,
                        'publisher': publisher,
                        'link': link,
                        'provider_publish_time': publish_time,
                        'type': item.get('type') or content.get('contentType'),
                        'thumbnail': item.get('thumbnail') or content.get('thumbnail')
                    }
                    formatted_news.append(formatted_item)
                    seen_links.add(link)
                    seen_titles.add(title)
        except Exception as e:
            logger.warning(f"从 yfinance 获取新闻失败: {symbol}, 错误: {e}")

        # 2. 如果不足 count 条，尝试从 RSS 获取补充
        if len(formatted_news) < count:
            try:
                rss_url = f"https://finance.yahoo.com/rss/headline?s={symbol}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(rss_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    rss_items = root.findall('.//item')
                    logger.info(f"RSS 返回了 {len(rss_items)} 条新闻数据: {symbol}")
                    
                    for item in rss_items:
                        if len(formatted_news) >= count:
                            break
                            
                        title = item.find('title').text if item.find('title') is not None else ""
                        link = item.find('link').text if item.find('link') is not None else ""
                        
                        if not title or not link:
                            continue
                            
                        if link in seen_links or title in seen_titles:
                            continue
                            
                        # 解析发布时间 (RSS 格式通常是: Mon, 13 Jan 2026 16:30:50 +0000)
                        pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ""
                        publish_time = 0
                        if pub_date_str:
                            try:
                                # 去掉末尾的时区部分或简单处理
                                # email.utils.parsedate_to_datetime 是处理这种格式的好方法
                                import email.utils
                                dt = email.utils.parsedate_to_datetime(pub_date_str)
                                publish_time = int(dt.timestamp())
                            except Exception:
                                publish_time = 0
                                
                        # 获取描述作为类型参考或保持为空
                        description = item.find('description').text if item.find('description') is not None else ""
                        
                        formatted_item = {
                            'uuid': f"rss-{hash(link)}",
                            'title': title,
                            'publisher': "Yahoo Finance (RSS)",
                            'link': link,
                            'provider_publish_time': publish_time,
                            'type': 'STORY',
                            'thumbnail': None
                        }
                        formatted_news.append(formatted_item)
                        seen_links.add(link)
                        seen_titles.add(title)
            except Exception as e:
                logger.warning(f"从 RSS 获取新闻失败: {symbol}, 错误: {e}")

        # 按时间倒序排序
        formatted_news.sort(key=lambda x: x['provider_publish_time'], reverse=True)
        return formatted_news
    except Exception as e:
        logger.error(f"获取股票新闻总流程失败: {symbol}, 错误: {e}")
        return []

