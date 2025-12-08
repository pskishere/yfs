#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YFinance数据获取模块 - 从yfinance获取股票数据
包含所有可用的yfinance功能：股票信息、历史数据、基本面、期权、分红、持股、内部交易、新闻等
"""

import pandas as pd
import numpy as np
import pytz
import logging
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Any, Optional, Tuple
from .settings import logger, get_kline_from_cache, save_kline_to_cache


def get_stock_info(symbol: str):
    """
    获取股票详细信息
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info:
            return None
        
        return {
            'symbol': symbol,
            'longName': info.get('longName', info.get('shortName', symbol)),
            'shortName': info.get('shortName', ''),
            'exchange': info.get('exchange', ''),
            'currency': info.get('currency', 'USD'),
            'marketCap': info.get('marketCap', 0),
            'regularMarketPrice': info.get('regularMarketPrice', 0),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
        }
    except Exception as e:
        logger.error(f"获取股票信息失败: {symbol}, 错误: {e}")
        return None


def _format_financial_dataframe(df):
    """
    格式化财务报表DataFrame为列表格式（字典列表）
    将DataFrame转换为列表，每个元素是一个日期对应的记录
    """
    if df is None or df.empty:
        return []
    
    result = []
    # 转置DataFrame，使日期为键
    df_transposed = df.T
    
    for date in df_transposed.index:
        # 处理日期：转换为字符串
        if hasattr(date, 'strftime'):
            date_str = date.strftime('%Y-%m-%d')
        elif isinstance(date, pd.Timestamp):
            date_str = date.strftime('%Y-%m-%d')
        else:
            date_str = str(date)
        
        record = {'index': date_str, 'Date': date_str}
        for col in df_transposed.columns:
            value = df_transposed.loc[date, col]
            # 处理NaN值
            if pd.notna(value):
                # 处理 Timestamp 对象
                if isinstance(value, pd.Timestamp):
                    record[col] = value.strftime('%Y-%m-%d')
                elif isinstance(value, (int, float, np.number)):
                    record[col] = float(value)
                else:
                    record[col] = str(value)
            else:
                record[col] = None
        
        result.append(record)
    
    return result


def get_fundamental_data(symbol: str):
    """
    获取基本面数据（从yfinance）
    返回公司财务数据、估值指标、财务报表、资产负债表、现金流量表等
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # 静默处理，如果获取不到info就返回None
        try:
            info = ticker.info
        except Exception as e:
            logger.debug(f"无法获取股票信息: {symbol}, 错误: {e}")
            return None
        
        if not info or len(info) == 0:
            logger.debug(f"股票信息为空: {symbol}")
            return None
        
        # 计算每股现金（避免除零错误）
        shares_outstanding = info.get('sharesOutstanding', 0)
        total_cash = info.get('totalCash', 0)
        cash_per_share = (total_cash / shares_outstanding) if shares_outstanding and shares_outstanding > 0 else 0
        
        # 提取基本面关键指标
        fundamental = {
            # 公司信息
            'CompanyName': info.get('longName', info.get('shortName', symbol)),
            'ShortName': info.get('shortName', ''),
            'Exchange': info.get('exchange', ''),
            'Currency': info.get('currency', 'USD'),
            'Sector': info.get('sector', ''),
            'Industry': info.get('industry', ''),
            'Website': info.get('website', ''),
            'Employees': info.get('fullTimeEmployees', 0),
            'BusinessSummary': info.get('longBusinessSummary', ''),
            
            # 市值与价格
            'MarketCap': info.get('marketCap', 0),
            'EnterpriseValue': info.get('enterpriseValue', 0),
            'Price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'PreviousClose': info.get('previousClose', 0),
            '52WeekHigh': info.get('fiftyTwoWeekHigh', 0),
            '52WeekLow': info.get('fiftyTwoWeekLow', 0),
            'SharesOutstanding': shares_outstanding,
            
            # 估值指标
            'PE': info.get('trailingPE', 0),
            'ForwardPE': info.get('forwardPE', 0),
            'PriceToBook': info.get('priceToBook', 0),
            'PriceToSales': info.get('priceToSalesTrailing12Months', 0),
            'PEGRatio': info.get('pegRatio', 0),
            'EVToRevenue': info.get('enterpriseToRevenue', 0),
            'EVToEBITDA': info.get('enterpriseToEbitda', 0),
            
            # 盈利能力
            'ProfitMargin': info.get('profitMargins', 0),
            'OperatingMargin': info.get('operatingMargins', 0),
            'GrossMargin': info.get('grossMargins', 0),
            'ROE': info.get('returnOnEquity', 0),
            'ROA': info.get('returnOnAssets', 0),
            'ROIC': info.get('returnOnInvestedCapital', 0),
            
            # 财务健康
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
            
            # 每股数据
            'EPS': info.get('trailingEps', 0),
            'ForwardEPS': info.get('forwardEps', 0),
            'BookValuePerShare': info.get('bookValue', 0),
            'DividendPerShare': info.get('dividendRate', 0),
            
            # 股息
            'DividendRate': info.get('dividendRate', 0),
            'DividendYield': info.get('dividendYield', 0),
            'PayoutRatio': info.get('payoutRatio', 0),
            'ExDividendDate': info.get('exDividendDate', 0),
            
            # 成长性
            'RevenueGrowth': info.get('revenueGrowth', 0),
            'EarningsGrowth': info.get('earningsGrowth', 0),
            'EarningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth', 0),
            'QuarterlyRevenueGrowth': info.get('quarterlyRevenueGrowth', 0),
            
            # 分析师预期
            'TargetPrice': info.get('targetMeanPrice', 0),
            'TargetHighPrice': info.get('targetHighPrice', 0),
            'TargetLowPrice': info.get('targetLowPrice', 0),
            'ConsensusRecommendation': info.get('recommendationMean', 0),
            'RecommendationKey': info.get('recommendationKey', ''),
            'NumberOfAnalystOpinions': info.get('numberOfAnalystOpinions', 0),
            'ProjectedEPS': info.get('forwardEps', 0),
            'ProjectedGrowthRate': info.get('earningsQuarterlyGrowth', 0),
            
            # 其他指标
            'Beta': info.get('beta', 0),
            'AverageVolume': info.get('averageVolume', 0),
            'AverageVolume10days': info.get('averageVolume10days', 0),
            'FloatShares': info.get('floatShares', 0),
        }
        
        try:
            financials = ticker.financials
            if financials is not None and not financials.empty:
                fundamental['Financials'] = _format_financial_dataframe(financials)
                logger.debug(f"已获取财务报表数据: {symbol}")
        except Exception as e:
            logger.debug(f"获取财务报表失败（已跳过）: {symbol}")
            # 不添加到结果中，让前端不显示
        
        try:
            quarterly_financials = ticker.quarterly_financials
            if quarterly_financials is not None and not quarterly_financials.empty:
                fundamental['QuarterlyFinancials'] = _format_financial_dataframe(quarterly_financials)
                logger.debug(f"已获取季度财务报表数据: {symbol}")
        except Exception as e:
            logger.debug(f"获取季度财务报表失败（已跳过）: {symbol}")
            # 不添加到结果中
        
        try:
            balance_sheet = ticker.balance_sheet
            if balance_sheet is not None and not balance_sheet.empty:
                fundamental['BalanceSheet'] = _format_financial_dataframe(balance_sheet)
                logger.debug(f"已获取资产负债表数据: {symbol}")
        except Exception as e:
            logger.debug(f"获取资产负债表失败（已跳过）: {symbol}")
            # 不添加到结果中
        
        try:
            quarterly_balance_sheet = ticker.quarterly_balance_sheet
            if quarterly_balance_sheet is not None and not quarterly_balance_sheet.empty:
                fundamental['QuarterlyBalanceSheet'] = _format_financial_dataframe(quarterly_balance_sheet)
                logger.debug(f"已获取季度资产负债表数据: {symbol}")
        except Exception as e:
            logger.debug(f"获取季度资产负债表失败（已跳过）: {symbol}")
            # 不添加到结果中
        
        try:
            cashflow = ticker.cashflow
            if cashflow is not None and not cashflow.empty:
                fundamental['Cashflow'] = _format_financial_dataframe(cashflow)
                logger.debug(f"已获取现金流量表数据: {symbol}")
        except Exception as e:
            logger.debug(f"获取现金流量表失败（已跳过）: {symbol}")
            # 不添加到结果中
        
        try:
            quarterly_cashflow = ticker.quarterly_cashflow
            if quarterly_cashflow is not None and not quarterly_cashflow.empty:
                fundamental['QuarterlyCashflow'] = _format_financial_dataframe(quarterly_cashflow)
                logger.debug(f"已获取季度现金流量表数据: {symbol}")
        except Exception as e:
            logger.debug(f"获取季度现金流量表失败（已跳过）: {symbol}")
            # 不添加到结果中
        
        return fundamental
        
    except Exception as e:
        # 静默处理，不报错
        logger.debug(f"获取基本面数据失败（已跳过）: {symbol}")
        return None


def _is_trading_hours() -> bool:
    """
    判断当前是否在美股交易时间内
    美股交易时间：周一至周五 09:30-16:00 ET（东部时间）
    """
    try:
        et_tz = pytz.timezone('US/Eastern')
        now_et = pd.Timestamp.now(tz=et_tz)
        
        # 检查是否为工作日（周一到周五）
        if now_et.weekday() >= 5:  # 5=周六, 6=周日
            return False
        
        # 检查是否在交易时间内（09:30-16:00 ET）
        hour = now_et.hour
        minute = now_et.minute
        
        # 09:30 之前或 16:00 之后都不在交易时间内
        if hour < 9 or (hour == 9 and minute < 30):
            return False
        if hour >= 16:
            return False
        
        return True
    except Exception as e:
        logger.warning(f"判断交易时间失败: {e}")
        return False


def _get_realtime_data(symbol: str, interval: str) -> Optional[pd.DataFrame]:
    """
    获取实时数据（盘中）
    仅在交易时间内调用，获取当天的实时分钟级数据
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # 根据interval确定获取实时数据的粒度
        # 如果请求的是分钟级数据，获取1分钟数据；否则获取5分钟数据
        if interval in ['1m', '2m', '5m']:
            realtime_interval = interval
        elif interval in ['15m', '30m']:
            realtime_interval = '5m'  # 使用5分钟数据作为实时数据
        else:
            # 对于小时级或日级数据，不需要实时数据
            return None
        
        # 获取当天的数据（包含实时数据）
        today_data = ticker.history(period='1d', interval=realtime_interval)
        
        if today_data.empty:
            return None
        
        # 移除时区信息
        if today_data.index.tzinfo is not None:
            today_data.index = today_data.index.tz_localize(None)
        
        # 只返回今天的数据
        today = pd.Timestamp.now().normalize()
        today_data = today_data[today_data.index >= today]
        
        if today_data.empty:
            return None
        
        logger.info(f"获取实时数据: {symbol}, {len(today_data)}条, 最新: {today_data.index[-1]}")
        
        # 打印实时数据
        print(f"\n{'='*60}")
        print(f"📊 实时数据 ({symbol}, {realtime_interval}):")
        print(f"{'='*60}")
        print(f"实时数据条数: {len(today_data)}")
        print(f"时间范围: {today_data.index[0]} 至 {today_data.index[-1]}")
        print(f"\n最新10条实时数据:")
        print(today_data.tail(10).to_string())
        print(f"\n实时数据统计:")
        print(f"  最新价格: {today_data['Close'].iloc[-1]:.2f}")
        print(f"  最高价: {today_data['High'].max():.2f}")
        print(f"  最低价: {today_data['Low'].min():.2f}")
        if 'Volume' in today_data.columns:
            print(f"  总成交量: {today_data['Volume'].sum():,.0f}")
        print(f"{'='*60}\n")
        
        return today_data
        
    except Exception as e:
        logger.warning(f"获取实时数据失败: {symbol}, 错误: {e}")
        return None


def _format_historical_data(df: pd.DataFrame):
    """
    格式化历史数据
    """
    result = []
    # 检查是否有 Volume 列，如果没有或为 NaN 则使用 0
    has_volume = 'Volume' in df.columns
    
    for date, row in df.iterrows():
        date_str = date.strftime('%Y%m%d')
        if pd.notna(date.hour):  # 如果有时间
            date_str = date.strftime('%Y%m%d %H:%M:%S')
        
        # 处理成交量数据：如果不存在或为 NaN，使用 0
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
    获取历史数据，支持缓存和增量更新
    默认缓存至少1年以上数据，保证日期连续性和最新日期为当日
    duration: 数据周期，如 '1 D', '1 W', '1 M', '3 M', '1 Y'
    bar_size: K线周期，如 '1 min', '5 mins', '1 hour', '1 day'
    """
    try:
        # 转换bar_size为yfinance格式
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
        
        # 尝试从缓存获取数据
        cached_df = get_kline_from_cache(symbol, yf_interval)
        
        # 统一时区处理
        now_local = pd.Timestamp.now()
        et_tz = pytz.timezone('US/Eastern')
        now_et = now_local.tz_localize('UTC').astimezone(et_tz) if now_local.tzinfo is None else now_local.astimezone(et_tz)
        
        # 美股交易时间：09:30-16:00 ET
        if now_et.hour < 16 or (now_et.hour == 16 and now_et.minute == 0):
            expected_latest_date = (now_et.date() - timedelta(days=1))
        else:
            expected_latest_date = now_et.date()
        
        # 考虑周末：如果是周六/周日，往前推到周五
        while expected_latest_date.weekday() >= 5:  # 5=周六, 6=周日
            expected_latest_date -= timedelta(days=1)
        
        today = pd.Timestamp.now().normalize().tz_localize(None)
        one_year_ago = today - timedelta(days=365)
        
        # 检查缓存数据的完整性
        need_full_refresh = False
        
        if cached_df is None or cached_df.empty:
            need_full_refresh = True
            logger.info(f"无缓存数据，需要全量获取: {symbol}, {yf_interval}")
        else:
            if cached_df.index.tzinfo is not None:
                cached_df.index = cached_df.index.tz_localize(None)
            
            first_date = cached_df.index[0]
            last_date = cached_df.index[-1]
            
            if first_date > one_year_ago:
                logger.info(f"缓存数据不足1年（最早: {first_date}），需要全量刷新")
                need_full_refresh = True
            elif last_date.date() < (today - timedelta(days=7)).date():
                logger.info(f"缓存数据过旧（最新: {last_date}），需要全量刷新")
                need_full_refresh = True
        
        if need_full_refresh:
            logger.info(f"从 yfinance 获取全量数据: {symbol}, 2y, {yf_interval}")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period='2y', interval=yf_interval)
            
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
            
            # 所有数据都保存到缓存
            save_kline_to_cache(symbol, yf_interval, df)
            logger.info(f"全量数据已缓存: {symbol}, {yf_interval}, {len(df)}条, 时间范围: {df.index[0]} - {df.index[-1]}")
            
            # 盘中实时数据混入（仅在交易时间内）
            if yf_interval in ['1m', '2m', '5m', '15m', '30m']:
                if _is_trading_hours():
                    try:
                        realtime_data = _get_realtime_data(symbol, yf_interval)
                        if realtime_data is not None and not realtime_data.empty:
                            # 合并实时数据到历史数据
                            df = pd.concat([df, realtime_data])
                            df = df[~df.index.duplicated(keep='last')]
                            df = df.sort_index()
                            
                            logger.info(f"盘中实时数据已混入: {symbol}, 实时数据{len(realtime_data)}条, 总计{len(df)}条, 最新: {df.index[-1]}")
                    except Exception as e:
                        logger.warning(f"混入实时数据失败: {symbol}, 错误: {e}")
                else:
                    logger.debug(f"非交易时间，不混入实时数据: {symbol}, {yf_interval}")
            
            return _format_historical_data(df), None
        
        last_cached_date = cached_df.index[-1]
        logger.info(f"使用缓存数据并增量更新: {symbol}, {yf_interval}, 最新: {last_cached_date.date()}")
        
        # 对于日K线，如果缓存中已经有今天的数据，就不需要重新拉取
        is_daily = (yf_interval == '1d')
        today_date = today.date()
        last_cached_date_only = last_cached_date.date() if hasattr(last_cached_date, 'date') else last_cached_date
        
        # 检查是否在交易时间内（盘中状态）
        is_trading = _is_trading_hours()
        is_minute_interval = yf_interval in ['1m', '2m', '5m', '15m', '30m']
        
        # 初始化 final_df，默认使用缓存数据
        final_df = None
        
        # 盘中状态时，分钟级K线需要重新获取实时数据（跳过缓存检查）
        if is_trading and is_minute_interval:
            logger.info(f"盘中状态，分钟级K线需要重新获取实时数据: {symbol}, {yf_interval}")
            print(f"\n{'='*60}")
            print(f"📊 盘中状态检测 ({symbol}, {yf_interval}):")
            print(f"{'='*60}")
            print(f"状态: 交易时间内，强制重新获取实时数据")
            print(f"缓存日期: {last_cached_date_only}")
            print(f"缓存数据条数: {len(cached_df)}")
            print(f"最新数据时间: {cached_df.index[-1]}")
            print(f"{'='*60}\n")
            # 强制重新获取数据，不检查缓存是否最新
            final_df = None  # 标记需要重新获取
        elif is_daily and last_cached_date_only >= today_date:
            logger.info(f"日K线缓存已包含今天数据: {symbol}, 缓存日期={last_cached_date_only}, 今天={today_date}, 无需重新拉取")
            print(f"\n{'='*60}")
            print(f"📊 缓存状态 ({symbol}, {yf_interval}):")
            print(f"{'='*60}")
            print(f"状态: 日K线缓存已包含今天数据")
            print(f"缓存日期: {last_cached_date_only}")
            print(f"今天日期: {today_date}")
            print(f"缓存数据条数: {len(cached_df)}")
            print(f"最新数据时间: {cached_df.index[-1]}")
            print(f"{'='*60}\n")
            final_df = cached_df.copy()
        elif last_cached_date_only >= expected_latest_date:
            # 盘中状态时，即使缓存已是最新，也要重新获取实时数据
            if is_trading and is_minute_interval:
                logger.info(f"盘中状态，缓存已是最新但需要获取实时数据: {symbol}, {yf_interval}")
                print(f"\n{'='*60}")
                print(f"📊 盘中状态检测 ({symbol}, {yf_interval}):")
                print(f"{'='*60}")
                print(f"状态: 交易时间内，缓存已是最新，但需要获取实时数据")
                print(f"缓存日期: {last_cached_date_only}")
                print(f"缓存数据条数: {len(cached_df)}")
                print(f"最新数据时间: {cached_df.index[-1]}")
                print(f"{'='*60}\n")
                # 标记需要重新获取实时数据
                final_df = None
            else:
                logger.info(f"缓存已是最新数据: {symbol}, 缓存日期={last_cached_date_only}, 预期最新={expected_latest_date}")
                print(f"\n{'='*60}")
                print(f"📊 缓存状态 ({symbol}, {yf_interval}):")
                print(f"{'='*60}")
                print(f"状态: 缓存已是最新数据")
                print(f"缓存日期: {last_cached_date_only}")
                print(f"预期最新日期: {expected_latest_date}")
                print(f"缓存数据条数: {len(cached_df)}")
                print(f"最新数据时间: {cached_df.index[-1]}")
                print(f"{'='*60}\n")
                final_df = cached_df.copy()
        
        # 如果需要重新获取（盘中状态）或缓存不是最新的
        # final_df 为 None 表示需要重新获取，或者缓存日期过旧也需要重新获取
        if final_df is None or last_cached_date_only < expected_latest_date:
            try:
                ticker = yf.Ticker(symbol)
                # 盘中状态时，获取当天的数据以确保获取最新实时数据
                if is_trading and is_minute_interval:
                    period = '1d'  # 只获取当天的数据，包含实时数据
                    logger.info(f"盘中状态，获取当天实时数据: {symbol}, {yf_interval}")
                else:
                    period = '10d'
                new_data = ticker.history(period=period, interval=yf_interval)
                
                if not new_data.empty:
                    if new_data.index.tzinfo is not None:
                        new_data.index = new_data.index.tz_localize(None)
                    
                    # 盘中状态时，打印获取到的实时数据
                    if is_trading and is_minute_interval:
                        print(f"\n{'='*60}")
                        print(f"📊 盘中实时数据 ({symbol}, {yf_interval}):")
                        print(f"{'='*60}")
                        print(f"获取到的数据条数: {len(new_data)}")
                        print(f"时间范围: {new_data.index[0]} 至 {new_data.index[-1]}")
                        print(f"\n最新10条实时数据:")
                        print(new_data.tail(10).to_string())
                        print(f"\n实时数据统计:")
                        print(f"  最新价格: {new_data['Close'].iloc[-1]:.2f}")
                        print(f"  最高价: {new_data['High'].max():.2f}")
                        print(f"  最低价: {new_data['Low'].min():.2f}")
                        if 'Volume' in new_data.columns:
                            print(f"  总成交量: {new_data['Volume'].sum():,.0f}")
                        print(f"{'='*60}\n")
                    
                    new_data_filtered = new_data[new_data.index > last_cached_date]
                    
                    if not new_data_filtered.empty:
                        # 打印增量更新数据
                        print(f"\n{'='*60}")
                        print(f"📈 增量更新数据 ({symbol}, {yf_interval}):")
                        print(f"{'='*60}")
                        print(f"新增数据条数: {len(new_data_filtered)}")
                        print(f"时间范围: {new_data_filtered.index[0]} 至 {new_data_filtered.index[-1]}")
                        print(f"\n增量数据详情:")
                        print(new_data_filtered.to_string())
                        print(f"\n增量数据统计:")
                        print(f"  最新价格: {new_data_filtered['Close'].iloc[-1]:.2f}")
                        print(f"  最高价: {new_data_filtered['High'].max():.2f}")
                        print(f"  最低价: {new_data_filtered['Low'].min():.2f}")
                        if 'Volume' in new_data_filtered.columns:
                            print(f"  总成交量: {new_data_filtered['Volume'].sum():,.0f}")
                        print(f"{'='*60}\n")
                        logger.info(f"📈 增量更新数据 ({symbol}, {yf_interval}): 新增{len(new_data_filtered)}条, 时间范围: {new_data_filtered.index[0]} 至 {new_data_filtered.index[-1]}")
                        
                        combined_df = pd.concat([cached_df, new_data])
                        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                        combined_df = combined_df.sort_index()
                        
                        # 所有数据都保存到缓存（包括增量数据）
                        save_kline_to_cache(symbol, yf_interval, new_data)
                        logger.info(f"增量数据已保存到缓存: {symbol}, {yf_interval}, {len(new_data_filtered)}条")
                        
                        logger.info(f"增量更新完成: {symbol}, 新增{len(new_data_filtered)}条, 总计{len(combined_df)}条, 最新: {combined_df.index[-1].date()}")
                        final_df = combined_df
                    else:
                        # 盘中状态时，即使没有新数据，也合并获取到的数据（可能包含实时更新）
                        if is_trading and is_minute_interval:
                            logger.info(f"盘中状态，合并最新获取的数据（可能包含实时更新）: {symbol}, 缓存最新日期: {last_cached_date_only}")
                            # 合并获取到的数据（可能包含实时更新）
                            combined_df = pd.concat([cached_df, new_data])
                            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                            combined_df = combined_df.sort_index()
                            
                            # 打印合并后的数据信息
                            print(f"\n{'='*60}")
                            print(f"🔄 盘中数据合并 ({symbol}, {yf_interval}):")
                            print(f"{'='*60}")
                            print(f"缓存数据条数: {len(cached_df)}")
                            print(f"获取数据条数: {len(new_data)}")
                            print(f"合并后数据条数: {len(combined_df)}")
                            print(f"最新数据时间: {combined_df.index[-1]}")
                            print(f"最新价格: {combined_df['Close'].iloc[-1]:.2f}")
                            print(f"{'='*60}\n")
                            
                            # 保存合并后的数据到缓存
                            save_kline_to_cache(symbol, yf_interval, combined_df)
                            final_df = combined_df
                        else:
                            logger.info(f"无新数据，返回缓存数据: {symbol}, 缓存最新日期: {last_cached_date_only}")
                            final_df = cached_df.copy()
                else:
                    if is_trading and is_minute_interval:
                        logger.info(f"盘中状态，获取数据为空，返回缓存数据: {symbol}")
                    else:
                        logger.info(f"获取最新数据为空，返回缓存数据")
                    final_df = cached_df.copy()
                    
            except Exception as e:
                logger.warning(f"增量更新失败: {e}，返回缓存数据")
                final_df = cached_df.copy()
        
        # 保底检查：确保 final_df 不为 None
        if final_df is None:
            logger.warning(f"final_df 为 None，使用缓存数据作为备选: {symbol}, {yf_interval}")
            final_df = cached_df
        
        # 盘中实时数据混入（仅在交易时间内）
        if yf_interval in ['1m', '2m', '5m', '15m', '30m']:
            is_trading = _is_trading_hours()
            print(f"\n{'='*60}")
            print(f"⏰ 交易时间检查 ({symbol}, {yf_interval}):")
            print(f"{'='*60}")
            print(f"是否在交易时间内: {'是' if is_trading else '否'}")
            if is_trading:
                try:
                    realtime_data = _get_realtime_data(symbol, yf_interval)
                    if realtime_data is not None and not realtime_data.empty:
                        # 打印实时数据混入
                        print(f"\n{'='*60}")
                        print(f"⚡ 实时数据混入 ({symbol}, {yf_interval}):")
                        print(f"{'='*60}")
                        print(f"实时数据条数: {len(realtime_data)}")
                        print(f"时间范围: {realtime_data.index[0]} 至 {realtime_data.index[-1]}")
                        print(f"\n最新10条实时数据:")
                        print(realtime_data.tail(10).to_string())
                        print(f"\n实时数据统计:")
                        print(f"  最新价格: {realtime_data['Close'].iloc[-1]:.2f}")
                        print(f"  最高价: {realtime_data['High'].max():.2f}")
                        print(f"  最低价: {realtime_data['Low'].min():.2f}")
                        if 'Volume' in realtime_data.columns:
                            print(f"  总成交量: {realtime_data['Volume'].sum():,.0f}")
                        print(f"{'='*60}\n")
                        
                        # 合并实时数据到历史数据
                        # 移除重复的时间戳，保留实时数据（keep='last'）
                        final_df = pd.concat([final_df, realtime_data])
                        final_df = final_df[~final_df.index.duplicated(keep='last')]
                        final_df = final_df.sort_index()
                        
                        logger.info(f"盘中实时数据已混入: {symbol}, 实时数据{len(realtime_data)}条, 总计{len(final_df)}条, 最新: {final_df.index[-1]}")
                        # 实时数据作为增量数据的一部分，会在下次增量更新时入库
                        logger.debug(f"实时数据将在下次增量更新时入库: {symbol}, {yf_interval}")
                    else:
                        print(f"  实时数据为空，无法混入")
                        print(f"{'='*60}\n")
                except Exception as e:
                    logger.warning(f"混入实时数据失败: {symbol}, 错误: {e}")
                    print(f"  获取实时数据失败: {e}")
                    print(f"{'='*60}\n")
            else:
                logger.debug(f"非交易时间，不混入实时数据: {symbol}, {yf_interval}")
                print(f"  当前不在交易时间内，跳过实时数据混入")
                print(f"{'='*60}\n")
        
        return _format_historical_data(final_df), None
        
    except Exception as e:
        logger.error(f"获取历史数据失败: {symbol}, 错误: {e}")
        return None, {'code': 500, 'message': str(e)}


def get_dividends(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取股票分红历史
    """
    try:
        ticker = yf.Ticker(symbol)
        dividends = ticker.dividends
        
        if dividends is None or dividends.empty:
            return []
        
        result = []
        for date, value in dividends.items():
            result.append({
                'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                'dividend': float(value)
            })
        
        logger.info(f"已获取分红历史: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取分红历史失败: {symbol}, 错误: {e}")
        return None


def get_splits(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取股票拆分历史
    """
    try:
        ticker = yf.Ticker(symbol)
        splits = ticker.splits
        
        if splits is None or splits.empty:
            return []
        
        result = []
        for date, ratio in splits.items():
            result.append({
                'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                'ratio': float(ratio)
            })
        
        logger.info(f"已获取股票拆分历史: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取股票拆分历史失败: {symbol}, 错误: {e}")
        return None


def get_actions(symbol: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """
    获取公司行动（分红+拆分）
    """
    try:
        ticker = yf.Ticker(symbol)
        actions = ticker.actions
        
        if actions is None or actions.empty:
            return {'dividends': [], 'splits': []}
        
        result = {'dividends': [], 'splits': []}
        
        for date, row in actions.iterrows():
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            
            if 'Dividends' in row and pd.notna(row['Dividends']) and row['Dividends'] > 0:
                result['dividends'].append({
                    'date': date_str,
                    'dividend': float(row['Dividends'])
                })
            
            if 'Stock Splits' in row and pd.notna(row['Stock Splits']) and row['Stock Splits'] > 0:
                result['splits'].append({
                    'date': date_str,
                    'ratio': float(row['Stock Splits'])
                })
        
        logger.info(f"已获取公司行动: {symbol}, 分红{len(result['dividends'])}条, 拆分{len(result['splits'])}条")
        return result
        
    except Exception as e:
        logger.error(f"获取公司行动失败: {symbol}, 错误: {e}")
        return None


def get_institutional_holders(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取机构持股信息
    """
    try:
        ticker = yf.Ticker(symbol)
        holders = ticker.institutional_holders
        
        if holders is None or holders.empty:
            return []
        
        result = []
        for _, row in holders.iterrows():
            record = {}
            for col in holders.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        logger.info(f"已获取机构持股: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取机构持股失败: {symbol}, 错误: {e}")
        return None


def get_major_holders(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取主要持股人摘要
    """
    try:
        ticker = yf.Ticker(symbol)
        holders = ticker.major_holders
        
        if holders is None or holders.empty:
            return {}
        
        result = {}
        for idx, row in holders.iterrows():
            if len(row) >= 2:
                key = str(row[1]).replace(' ', '_')
                result[key] = str(row[0])
        
        logger.info(f"已获取主要持股人摘要: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取主要持股人摘要失败: {symbol}, 错误: {e}")
        return None


def get_mutualfund_holders(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取共同基金持股信息
    """
    try:
        ticker = yf.Ticker(symbol)
        holders = ticker.mutualfund_holders
        
        if holders is None or holders.empty:
            return []
        
        result = []
        for _, row in holders.iterrows():
            record = {}
            for col in holders.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        logger.info(f"已获取共同基金持股: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取共同基金持股失败: {symbol}, 错误: {e}")
        return None


def get_insider_transactions(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取内部交易信息
    """
    try:
        ticker = yf.Ticker(symbol)
        transactions = ticker.insider_transactions
        
        if transactions is None or transactions.empty:
            return []
        
        result = []
        for _, row in transactions.iterrows():
            record = {}
            for col in transactions.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        logger.info(f"已获取内部交易: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取内部交易失败: {symbol}, 错误: {e}")
        return None


def get_insider_purchases(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取内部人员购买信息
    """
    try:
        ticker = yf.Ticker(symbol)
        purchases = ticker.insider_purchases
        
        if purchases is None or purchases.empty:
            return []
        
        result = []
        for _, row in purchases.iterrows():
            record = {}
            for col in purchases.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        logger.info(f"已获取内部人员购买: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取内部人员购买失败: {symbol}, 错误: {e}")
        return None


def get_insider_roster_holders(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取内部人员名单
    """
    try:
        ticker = yf.Ticker(symbol)
        roster = ticker.insider_roster_holders
        
        if roster is None or roster.empty:
            return []
        
        result = []
        for _, row in roster.iterrows():
            record = {}
            for col in roster.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        logger.info(f"已获取内部人员名单: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取内部人员名单失败: {symbol}, 错误: {e}")
        return None


def get_recommendations(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取分析师推荐历史（评级升降级记录）
    """
    try:
        ticker = yf.Ticker(symbol)
        # 使用 upgrades_downgrades 获取具体的评级变化记录
        upgrades = ticker.upgrades_downgrades

        if upgrades is None or upgrades.empty:
            return []

        result = []
        for date, row in upgrades.iterrows():
            record = {}
            
            # 添加日期
            if hasattr(date, 'strftime'):
                record['Date'] = date.strftime('%Y-%m-%d')
            else:
                record['Date'] = str(date)
            
            # 添加其他字段
            for col in upgrades.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            
            # 规范化字段名（兼容前端）
            if 'ToGrade' in record:
                record['To Grade'] = record['ToGrade']
            if 'FromGrade' in record:
                record['From Grade'] = record['FromGrade']
                
            result.append(record)

        logger.info(f"已获取分析师推荐历史: {symbol}, 共{len(result)}条")
        return result

    except Exception as e:
        logger.error(f"获取分析师推荐历史失败: {symbol}, 错误: {e}")
        return None


def get_recommendations_summary(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取分析师推荐摘要
    """
    try:
        ticker = yf.Ticker(symbol)
        summary = ticker.recommendations_summary
        
        if summary is None or summary.empty:
            return {}
        
        result = {}
        for col in summary.columns:
            if col == 'period':
                result[col] = str(summary[col].iloc[0])
            else:
                result[col] = int(summary[col].iloc[0]) if pd.notna(summary[col].iloc[0]) else 0
        
        logger.info(f"已获取分析师推荐摘要: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取分析师推荐摘要失败: {symbol}, 错误: {e}")
        return None


def get_upgrades_downgrades(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取评级升降级历史
    """
    try:
        ticker = yf.Ticker(symbol)
        upgrades = ticker.upgrades_downgrades
        
        if upgrades is None or upgrades.empty:
            return []
        
        result = []
        for date, row in upgrades.iterrows():
            record = {'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)}
            for col in upgrades.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        logger.info(f"已获取评级升降级历史: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取评级升降级历史失败: {symbol}, 错误: {e}")
        return None


def get_earnings(symbol: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """
    获取收益数据（年度和季度）
    注意：ticker.earnings 已废弃，如果获取不到数据就返回空
    """
    try:
        ticker = yf.Ticker(symbol)
        
        result = {'yearly': [], 'quarterly': []}
        
        # 年度收益（已废弃，静默处理）
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=DeprecationWarning)
                earnings = ticker.earnings
                if earnings is not None and not earnings.empty:
                    for year, row in earnings.iterrows():
                        record = {'year': str(year)}
                        for col in earnings.columns:
                            value = row[col]
                            if pd.notna(value):
                                record[col] = float(value) if isinstance(value, (int, float, np.number)) else str(value)
                            else:
                                record[col] = None
                        result['yearly'].append(record)
        except Exception as e:
            logger.debug(f"获取年度收益失败（已跳过）: {symbol}")
        
        # 季度收益（已废弃，静默处理）
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=DeprecationWarning)
                quarterly_earnings = ticker.quarterly_earnings
                if quarterly_earnings is not None and not quarterly_earnings.empty:
                    for quarter, row in quarterly_earnings.iterrows():
                        record = {'quarter': str(quarter)}
                        for col in quarterly_earnings.columns:
                            value = row[col]
                            if pd.notna(value):
                                record[col] = float(value) if isinstance(value, (int, float, np.number)) else str(value)
                            else:
                                record[col] = None
                        result['quarterly'].append(record)
        except Exception as e:
            logger.debug(f"获取季度收益失败（已跳过）: {symbol}")
        
        # 如果没有任何数据，返回None而不是空字典
        if not result['yearly'] and not result['quarterly']:
            return None
        
        logger.debug(f"已获取收益数据: {symbol}, 年度{len(result['yearly'])}条, 季度{len(result['quarterly'])}条")
        return result
        
    except Exception as e:
        # 静默处理，不报错
        logger.debug(f"获取收益数据失败（已跳过）: {symbol}")
        return None


def get_earnings_dates(symbol: str, limit: int = 12) -> Optional[List[Dict[str, Any]]]:
    """
    获取收益日期（过去和未来的财报日期）
    """
    try:
        ticker = yf.Ticker(symbol)
        earnings_dates = ticker.earnings_dates
        
        if earnings_dates is None or earnings_dates.empty:
            return None
        
        result = []
        for date, row in earnings_dates.head(limit).iterrows():
            record = {'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)}
            for col in earnings_dates.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        if not result:
            return None
        
        logger.debug(f"已获取收益日期: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        # 静默处理，不报错
        logger.debug(f"获取收益日期失败（已跳过）: {symbol}")
        return None


def get_earnings_history(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取历史收益（实际vs预期）
    """
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.earnings_history
        
        if history is None or history.empty:
            return None
        
        result = []
        for _, row in history.iterrows():
            record = {}
            for col in history.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        if not result:
            return None
        
        logger.debug(f"已获取历史收益: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        # 静默处理，不报错
        logger.debug(f"获取历史收益失败（已跳过）: {symbol}")
        return None


def get_calendar(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取公司日历（收益日期等）
    """
    try:
        ticker = yf.Ticker(symbol)
        calendar = ticker.calendar
        
        if calendar is None or calendar.empty:
            return {}
        
        result = {}
        if isinstance(calendar, pd.DataFrame):
            for col in calendar.columns:
                value = calendar[col].iloc[0] if len(calendar) > 0 else None
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        result[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        result[col] = float(value)
                    else:
                        result[col] = str(value)
                else:
                    result[col] = None
        elif isinstance(calendar, dict):
            result = calendar
        
        logger.info(f"已获取公司日历: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取公司日历失败: {symbol}, 错误: {e}")
        return None


def get_sustainability(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取ESG（环境、社会、治理）可持续性评分
    """
    try:
        ticker = yf.Ticker(symbol)
        sustainability = ticker.sustainability
        
        if sustainability is None or sustainability.empty:
            return {}
        
        result = {}
        for idx in sustainability.index:
            value = sustainability.loc[idx].iloc[0]
            if pd.notna(value):
                if isinstance(value, (int, float, np.number)):
                    result[idx] = float(value)
                else:
                    result[idx] = str(value)
            else:
                result[idx] = None
        
        logger.info(f"已获取ESG数据: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取ESG数据失败: {symbol}, 错误: {e}")
        return None


def get_analyst_price_target(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取分析师价格目标
    """
    try:
        ticker = yf.Ticker(symbol)
        target = ticker.analyst_price_target
        
        if target is None or target.empty:
            return {}
        
        result = {}
        for key in target.index:
            value = target.loc[key].iloc[0]
            if pd.notna(value):
                if isinstance(value, (int, float, np.number)):
                    result[key] = float(value)
                else:
                    result[key] = str(value)
            else:
                result[key] = None
        
        logger.info(f"已获取分析师价格目标: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取分析师价格目标失败: {symbol}, 错误: {e}")
        return None


def get_revenue_forecasts(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取收入预测
    """
    try:
        ticker = yf.Ticker(symbol)
        forecasts = ticker.revenue_forecasts
        
        if forecasts is None or forecasts.empty:
            return []
        
        result = []
        for _, row in forecasts.iterrows():
            record = {}
            for col in forecasts.columns:
                value = row[col]
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, np.number)):
                        record[col] = float(value)
                    else:
                        record[col] = str(value)
                else:
                    record[col] = None
            result.append(record)
        
        logger.info(f"已获取收入预测: {symbol}, 共{len(result)}条")
        return result
        
    except Exception as e:
        logger.error(f"获取收入预测失败: {symbol}, 错误: {e}")
        return None


def get_options(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取期权数据（所有到期日的期权链）
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # 获取所有期权到期日
        expiration_dates = ticker.options
        
        if not expiration_dates:
            logger.info(f"没有期权数据: {symbol}")
            return {'expiration_dates': [], 'chains': {}}
        
        result = {
            'expiration_dates': list(expiration_dates),
            'chains': {}
        }
        
        # 获取每个到期日的期权链（限制前5个日期，避免数据过大）
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


def get_news(symbol: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    获取股票相关新闻
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        
        if not news:
            return []
        
        result = []
        for idx, item in enumerate(news[:limit]):
            if not isinstance(item, dict):
                logger.warning(f"新闻项不是字典类型: {type(item)}")
                continue
            
            # yfinance新版本数据结构：item = {'id': '...', 'content': {...}}
            # 需要从 content 中提取实际数据
            if 'content' in item and isinstance(item['content'], dict):
                content = item['content']
            else:
                content = item
            
            news_item = {}
            
            # 调试：记录原始数据的键（仅第一条）
            if idx == 0:
                logger.debug(f"新闻原始数据字段: {list(content.keys())}")
            
            # 提取标题
            title = content.get('title') or content.get('headline') or content.get('summary') or ''
            news_item['title'] = str(title).strip() if title else None
            
            # 提取发布者
            publisher = (content.get('publisher') or 
                        content.get('publisherName') or 
                        content.get('provider') or 
                        content.get('contentProvider', {}).get('displayName') if isinstance(content.get('contentProvider'), dict) else None or
                        '')
            news_item['publisher'] = str(publisher).strip() if publisher else None
            
            # 提取链接
            link = content.get('link') or content.get('url') or content.get('canonicalUrl', {}).get('url') if isinstance(content.get('canonicalUrl'), dict) else None or ''
            news_item['link'] = str(link).strip() if link else None
            
            # 处理发布时间
            provider_publish_time = content.get('pubDate') or content.get('providerPublishTime') or content.get('publishTime')
            if provider_publish_time:
                if isinstance(provider_publish_time, (int, float)):
                    news_item['providerPublishTime'] = datetime.fromtimestamp(provider_publish_time).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    news_item['providerPublishTime'] = str(provider_publish_time)
            else:
                news_item['providerPublishTime'] = None
            
            # 只添加有标题或有链接的新闻
            if news_item.get('title') or news_item.get('link'):
                result.append(news_item)
            else:
                logger.debug(f"跳过无效新闻项: 无标题且无链接")
            
            # 调试：记录第一条新闻的最终结构
            if len(result) == 1:
                logger.debug(f"第一条新闻处理后的字段: {list(news_item.keys())}, title: '{news_item.get('title')}', publisher: '{news_item.get('publisher')}', link: '{news_item.get('link')}'")
        
        logger.info(f"已获取新闻: {symbol}, 共{len(result)}条有效新闻")
        if result:
            logger.debug(f"新闻数据示例: title='{result[0].get('title')}', publisher='{result[0].get('publisher')}', link='{result[0].get('link')}'")
            # 只在调试模式下打印详细数据
            if logger.isEnabledFor(logging.DEBUG):
                print(f"\n{'='*60}")
                print(f"📰 新闻数据 ({symbol}): 共{len(result)}条")
                print(f"{'='*60}")
                for i, item in enumerate(result, 1):
                    print(f"\n新闻 {i}:")
                    print(f"  标题: {item.get('title', 'N/A')}")
                    print(f"  发布者: {item.get('publisher', 'N/A')}")
                    print(f"  链接: {item.get('link', 'N/A')}")
                    print(f"  发布时间: {item.get('providerPublishTime', 'N/A')}")
                    print(f"  所有字段: {list(item.keys())}")
                print(f"{'='*60}\n")
        return result
        
    except Exception as e:
        logger.error(f"获取新闻失败: {symbol}, 错误: {e}")
        return None


def get_fast_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取快速实时信息（价格、市值等）
    使用fast_info属性获取更快的实时数据
    """
    try:
        ticker = yf.Ticker(symbol)
        fast_info = ticker.fast_info
        
        if not fast_info:
            return {}
        
        result = {}
        # fast_info是一个特殊对象，需要遍历其属性
        for attr in dir(fast_info):
            if not attr.startswith('_'):
                try:
                    value = getattr(fast_info, attr)
                    if not callable(value):
                        if isinstance(value, (int, float, np.number)):
                            result[attr] = float(value)
                        else:
                            result[attr] = str(value) if value is not None else None
                except Exception:
                    continue
        
        logger.info(f"已获取快速实时信息: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取快速实时信息失败: {symbol}, 错误: {e}")
        return None


def get_history_metadata(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取历史数据元信息
    """
    try:
        ticker = yf.Ticker(symbol)
        metadata = ticker.history_metadata
        
        if not metadata:
            return {}
        
        result = {}
        for key, value in metadata.items():
            if isinstance(value, (int, float, np.number)):
                result[key] = float(value)
            elif isinstance(value, pd.Timestamp):
                result[key] = value.strftime('%Y-%m-%d')
            else:
                result[key] = str(value) if value is not None else None
        
        logger.info(f"已获取历史数据元信息: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取历史数据元信息失败: {symbol}, 错误: {e}")
        return None


def get_all_data(symbol: str, include_options: bool = False, 
                include_news: bool = True, news_limit: int = 10) -> Optional[Dict[str, Any]]:
    """
    获取股票的所有可用数据（一站式获取）
    
    参数:
        symbol: 股票代码
        include_options: 是否包含期权数据（数据量大，默认False）
        include_news: 是否包含新闻（默认True）
        news_limit: 新闻数量限制（默认10）
    """
    try:
        logger.info(f"开始获取完整数据: {symbol}")
        
        result = {
            'symbol': symbol,
            'info': get_stock_info(symbol),
            'fundamental': get_fundamental_data(symbol),
            'fast_info': get_fast_info(symbol),
            'dividends': get_dividends(symbol),
            'splits': get_splits(symbol),
            'actions': get_actions(symbol),
            'institutional_holders': get_institutional_holders(symbol),
            'major_holders': get_major_holders(symbol),
            'mutualfund_holders': get_mutualfund_holders(symbol),
            'insider_transactions': get_insider_transactions(symbol),
            'insider_purchases': get_insider_purchases(symbol),
            'insider_roster': get_insider_roster_holders(symbol),
            'recommendations': get_recommendations(symbol),
            'recommendations_summary': get_recommendations_summary(symbol),
            'upgrades_downgrades': get_upgrades_downgrades(symbol),
            'earnings': get_earnings(symbol),
            'earnings_dates': get_earnings_dates(symbol),
            'earnings_history': get_earnings_history(symbol),
            'calendar': get_calendar(symbol),
            'sustainability': get_sustainability(symbol),
            'analyst_price_target': get_analyst_price_target(symbol),
            'revenue_forecasts': get_revenue_forecasts(symbol),
            'history_metadata': get_history_metadata(symbol),
        }
        
        if include_options:
            result['options'] = get_options(symbol)
        
        if include_news:
            result['news'] = get_news(symbol, limit=news_limit)
        
        logger.info(f"完整数据获取完成: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"获取完整数据失败: {symbol}, 错误: {e}")
        return None

