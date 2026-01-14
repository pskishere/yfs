#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析模块 - 技术指标计算、交易信号生成和AI分析
"""

import numpy as np
import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from .yfinance import get_historical_data, get_fundamental_data, get_news, get_options

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

# 直接导入 ollama，如果失败会在导入时抛出异常
try:
    import ollama
except ImportError:
    ollama = None  # 如果未安装，设置为 None，在需要时检查

logger = logging.getLogger(__name__)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "deepseek-v3.2:cloud")


def check_ollama_available():
    """
    检查 Ollama 服务是否可用
    """
    if ollama is None:
        return False
    try:
        ollama_host = os.getenv("OLLAMA_HOST", OLLAMA_HOST)
        client = ollama.Client(host=ollama_host, timeout=5)
        # 尝试列出模型，如果能列出则表示服务可用
        client.list()
        return True
    except Exception:
        return False


def calculate_technical_indicators(symbol: str, duration: str = '1 M', bar_size: str = '1 day'):
    """
    计算技术指标（基于历史数据）
    返回：移动平均线、RSI、MACD等
    如果证券不存在，返回(None, error_info)
    """
    hist_data, error = get_historical_data(symbol, duration, bar_size)
    
    if error:
        return None, error
    
    if not hist_data or len(hist_data) == 0:
        return None, {"code": "NO_DATA", "message": f"无法获取历史数据: {symbol}"}
    
    # 数据不足时仍然尝试计算，但记录警告
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

    try:
        fundamental_data = get_fundamental_data(symbol)
        if fundamental_data:
            result['fundamental_data'] = fundamental_data
            logger.info(f"已获取基本面数据: {symbol}")
    except Exception as e:
        logger.warning(f"获取基本面数据失败: {symbol}, 错误: {e}")
        result['fundamental_data'] = None

    try:
        news_data = get_news(symbol)
        if news_data:
            result['news_data'] = news_data
            logger.info(f"已获取新闻数据: {symbol}, 共 {len(news_data)} 条")
        else:
            result['news_data'] = []
            logger.info(f"未获取到新闻数据: {symbol}")
    except Exception as e:
        logger.warning(f"获取新闻数据失败: {symbol}, 错误: {e}")
        result['news_data'] = []

    try:
        options_data = get_options(symbol)
        if options_data:
            result['options_data'] = options_data
            logger.info(f"已获取期权数据: {symbol}")
        else:
            result['options_data'] = None
    except Exception as e:
        logger.warning(f"获取期权数据失败: {symbol}, 错误: {e}")
        result['options_data'] = None

    if len(closes) >= 30:
        # 获取时间戳信息用于周期分析
        # 从hist_data中获取date字段，如果没有则从formatted_candles中获取time字段
        timestamps = []
        if hist_data:
            for bar in hist_data:
                date_str = bar.get('date', '')
                if date_str:
                    try:
                        if len(date_str) == 8:
                            from datetime import datetime
                            dt = datetime.strptime(date_str, '%Y%m%d')
                            timestamps.append(dt.strftime('%Y-%m-%d'))
                        elif ' ' in date_str:
                            from datetime import datetime
                            dt = datetime.strptime(date_str, '%Y%m%d %H:%M:%S')
                            timestamps.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
                        else:
                            timestamps.append(date_str)
                    except Exception:
                        timestamps.append(date_str)
                else:
                    timestamps.append(None)
        
        # 周期分析（已包含增强功能）
        cycle_data = calculate_cycle_analysis(
            closes, highs, lows,
            volumes=volumes if len(valid_volumes) > 0 else None,
            timestamps=timestamps if timestamps else None,
            use_adaptive=True,
            use_wavelet=True
        )
        result.update(cycle_data)
        
        # 计算年周期和月周期分析
        yearly_result = analyze_yearly_cycles(closes, highs, lows, timestamps if timestamps else None)
        monthly_result = analyze_monthly_cycles(closes, highs, lows, timestamps if timestamps else None)
        result['yearly_cycles'] = yearly_result.get('yearly_stats', [])
        result['monthly_cycles'] = monthly_result.get('monthly_stats', [])
        
    return result, None  # 返回结果和错误信息（无错误为None）


def perform_ai_analysis(symbol, indicators, duration, model=DEFAULT_AI_MODEL, extra_data=None):
    """
    执行AI分析的辅助函数
    """
    if ollama is None:
        raise RuntimeError("ollama 模块未安装，无法执行 AI 分析")
    
    try:
        # 确保所有可能用于格式化的值不是None
        indicators = indicators or {}
        currency_symbol = "$"
        currency_code = None
        if isinstance(extra_data, dict):
            currency_code = extra_data.get("currency") or extra_data.get("currencyCode")
            currency_symbol = (
                extra_data.get("currency_symbol")
                or extra_data.get("currencySymbol")
                or currency_symbol
            )
        if not currency_symbol and currency_code:
            currency_map = {
                "USD": "$",
                "HKD": "HK$",
                "CNY": "¥",
                "CNH": "¥",
                "JPY": "¥",
                "EUR": "€",
                "GBP": "£",
            }
            currency_symbol = currency_map.get(str(currency_code).upper(), f"{currency_code} ")

        def fmt_price(val):
            """统一格式化价格，匹配实际货币单位"""
            try:
                return f"{currency_symbol}{float(val):.2f}"
            except Exception:
                return f"{currency_symbol}{val}"
        
        def safe_indicators(d):
            """确保所有数值字段不是None"""
            result = {}
            for k, v in d.items():
                if v is None:
                    string_fields = ['direction', 'status', 'trend', 'signal', 'action', 'recommendation']
                    is_string_field = any(word in k.lower() for word in string_fields)
                    result[k] = 'unknown' if is_string_field else 0
                else:
                    result[k] = v
            return result
        
        indicators = safe_indicators(indicators)
        
        fundamental_data = indicators.get('fundamental_data', {})
        has_fundamental = (fundamental_data and 
                          isinstance(fundamental_data, dict) and 
                          'raw_xml' not in fundamental_data and
                          len(fundamental_data) > 0)
        
        # 格式化期权数据
        options_data = indicators.get('options_data')
        options_text = ""
        if options_data and options_data.get('expiration_dates'):
            options_text = "\n## 7. 期权数据\n"
            exp_dates = options_data.get('expiration_dates', [])
            options_text += f"- 可用到期日: {', '.join(exp_dates[:5])}等\n"
            
            # 取第一个到期日的数据作为示例分析
            first_exp = exp_dates[0] if exp_dates else None
            if first_exp:
                chain = options_data.get('chains', {}).get(first_exp, {})
                calls = chain.get('calls', [])
                puts = chain.get('puts', [])
                
                if calls or puts:
                    options_text += f"- 最近到期日 ({first_exp}) 概况:\n"
                    if calls:
                        try:
                            max_oi_call = max(calls, key=lambda x: x.get('openInterest') or 0)
                            options_text += f"  - 看涨期权(Calls): 共{len(calls)}档, 最大未平仓量行权价: {max_oi_call.get('strike')}\n"
                        except: pass
                    if puts:
                        try:
                            max_oi_put = max(puts, key=lambda x: x.get('openInterest') or 0)
                            options_text += f"  - 看跌期权(Puts): 共{len(puts)}档, 最大未平仓量行权价: {max_oi_put.get('strike')}\n"
                        except: pass
                    
                    # 计算 PCR (Put-Call Ratio) 如果可能
                    try:
                        call_oi = sum(c.get('openInterest') or 0 for c in calls)
                        put_oi = sum(p.get('openInterest') or 0 for p in puts)
                        if call_oi > 0:
                            options_text += f"  - Put/Call OI Ratio: {put_oi/call_oi:.2f}\n"
                    except: pass

        if has_fundamental:
            fundamental_sections = []
            
            if 'CompanyName' in fundamental_data:
                info_parts = [f"公司名称: {fundamental_data['CompanyName']}"]
                if 'Exchange' in fundamental_data:
                    info_parts.append(f"交易所: {fundamental_data['Exchange']}")
                if 'Employees' in fundamental_data:
                    info_parts.append(f"员工数: {fundamental_data['Employees']}人")
                if 'SharesOutstanding' in fundamental_data:
                    shares = fundamental_data['SharesOutstanding']
                    try:
                        shares_val = float(shares)
                        if shares_val >= 1e9:
                            shares_str = f"{shares_val/1e9:.2f}B股"
                        elif shares_val >= 1e6:
                            shares_str = f"{shares_val/1e6:.2f}M股"
                        else:
                            shares_str = f"{int(shares_val):,}股"
                        info_parts.append(f"流通股数: {shares_str}")
                    except:
                        info_parts.append(f"流通股数: {shares}")
                if info_parts:
                    fundamental_sections.append("基本信息:\n" + "\n".join([f"   - {p}" for p in info_parts]))
            
            price_parts = []
            if 'MarketCap' in fundamental_data and fundamental_data['MarketCap'] is not None:
                try:
                    mcap = float(fundamental_data['MarketCap'])
                    if mcap > 0:  # 只添加非零市值
                        if mcap >= 1e9:
                            price_parts.append(f"市值: ${mcap/1e9:.2f}B")
                        elif mcap >= 1e6:
                            price_parts.append(f"市值: ${mcap/1e6:.2f}M")
                        else:
                            price_parts.append(f"市值: ${mcap:.2f}")
                except:
                    pass
            if 'Price' in fundamental_data and fundamental_data['Price'] is not None:
                try:
                    price_val = float(fundamental_data['Price'])
                    if price_val > 0:  # 只添加有效价格
                        price_parts.append(f"当前价: ${price_val:.2f}")
                except:
                    pass
            if '52WeekHigh' in fundamental_data and '52WeekLow' in fundamental_data:
                try:
                    high_val = float(fundamental_data['52WeekHigh']) if fundamental_data['52WeekHigh'] is not None else 0
                    low_val = float(fundamental_data['52WeekLow']) if fundamental_data['52WeekLow'] is not None else 0
                    if high_val > 0 and low_val > 0:  # 只添加有效区间
                        price_parts.append(f"52周区间: ${low_val:.2f} - ${high_val:.2f}")
                except:
                    pass
            if price_parts:
                fundamental_sections.append("市值与价格:\n" + "\n".join([f"   - {p}" for p in price_parts]))
            
            financial_parts = []
            for key, label in [('RevenueTTM', '营收(TTM)'), ('NetIncomeTTM', '净利润(TTM)'), 
                              ('EBITDATTM', 'EBITDA(TTM)'), ('ProfitMargin', '利润率'), 
                              ('GrossMargin', '毛利率')]:
                if key in fundamental_data and fundamental_data[key] is not None:
                    value = fundamental_data[key]
                    try:
                        val = float(value)
                        if val != 0:  # 只添加非零值
                            if 'Margin' in key:
                                financial_parts.append(f"{label}: {val:.2f}%")
                            elif val >= 1e9:
                                financial_parts.append(f"{label}: ${val/1e9:.2f}B")
                            elif val >= 1e6:
                                financial_parts.append(f"{label}: ${val/1e6:.2f}M")
                            else:
                                financial_parts.append(f"{label}: {val:.2f}")
                    except:
                        pass
            if financial_parts:
                fundamental_sections.append("财务指标:\n" + "\n".join([f"   - {p}" for p in financial_parts]))
            
            per_share_parts = []
            for key, label in [('EPS', '每股收益(EPS)'), ('BookValuePerShare', '每股净资产'),
                              ('CashPerShare', '每股现金')]:
                if key in fundamental_data and fundamental_data[key] is not None:
                    value = fundamental_data[key]
                    try:
                        val = float(value)
                        if val != 0:  # 只添加非零值
                            per_share_parts.append(f"{label}: ${val:.2f}")
                    except:
                        pass
            if per_share_parts:
                fundamental_sections.append("每股数据:\n" + "\n".join([f"   - {p}" for p in per_share_parts]))
            
            valuation_parts = []
            for key, label in [('PE', '市盈率(PE)'), ('PriceToBook', '市净率(PB)'), ('ROE', '净资产收益率(ROE)')]:
                if key in fundamental_data and fundamental_data[key] is not None:
                    value = fundamental_data[key]
                    try:
                        val = float(value)
                        if val != 0:  # 只添加非零值
                            if key == 'ROE':
                                valuation_parts.append(f"{label}: {val:.2f}%")
                            else:
                                valuation_parts.append(f"{label}: {val:.2f}")
                    except:
                        pass
            if valuation_parts:
                fundamental_sections.append("估值指标:\n" + "\n".join([f"   - {p}" for p in valuation_parts]))
            
            forecast_parts = []
            if 'TargetPrice' in fundamental_data and fundamental_data['TargetPrice'] is not None:
                try:
                    target = float(fundamental_data['TargetPrice'])
                    if target > 0:  # 只添加有效目标价
                        forecast_parts.append(f"目标价: ${target:.2f}")
                except:
                    pass
            if 'ConsensusRecommendation' in fundamental_data and fundamental_data['ConsensusRecommendation'] is not None:
                try:
                    consensus = float(fundamental_data['ConsensusRecommendation'])
                    if consensus > 0:  # 只添加有效评级
                        if consensus <= 1.5:
                            rec = "强烈买入"
                        elif consensus <= 2.5:
                            rec = "买入"
                        elif consensus <= 3.5:
                            rec = "持有"
                        elif consensus <= 4.5:
                            rec = "卖出"
                        else:
                            rec = "强烈卖出"
                        forecast_parts.append(f"共识评级: {rec} ({consensus:.2f})")
                except:
                    pass
            if 'ProjectedEPS' in fundamental_data and fundamental_data['ProjectedEPS'] is not None:
                try:
                    proj_eps = float(fundamental_data['ProjectedEPS'])
                    if proj_eps != 0:  # 只添加非零EPS
                        forecast_parts.append(f"预测EPS: ${proj_eps:.2f}")
                except:
                    pass
            if 'ProjectedGrowthRate' in fundamental_data and fundamental_data['ProjectedGrowthRate'] is not None:
                try:
                    growth = float(fundamental_data['ProjectedGrowthRate'])
                    if growth != 0:  # 只添加非零增长率
                        forecast_parts.append(f"预测增长率: {growth:.2f}%")
                except:
                    pass
            if forecast_parts:
                fundamental_sections.append("分析师预测:\n" + "\n".join([f"   - {p}" for p in forecast_parts]))
            
            if fundamental_data.get('Financials'):
                try:
                    financials = fundamental_data['Financials']
                    if isinstance(financials, list) and len(financials) > 0:
                        financials_text = "年度财务报表:\n"
                        for record in financials[:2]:  # 最近2年
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                financials_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                financials_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                financials_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                financials_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            financials_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(financials_text)
                except Exception as e:
                    logger.warning(f"格式化年度财务报表失败: {e}")
            
            if fundamental_data.get('QuarterlyFinancials'):
                try:
                    quarterly = fundamental_data['QuarterlyFinancials']
                    if isinstance(quarterly, list) and len(quarterly) > 0:
                        quarterly_text = "季度财务报表:\n"
                        for record in quarterly[:8]:  # 最近8个季度（2年）
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                quarterly_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                quarterly_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                quarterly_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                quarterly_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            quarterly_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(quarterly_text)
                except Exception as e:
                    logger.warning(f"格式化季度财务报表失败: {e}")
            
            if fundamental_data.get('BalanceSheet'):
                try:
                    balance = fundamental_data['BalanceSheet']
                    if isinstance(balance, list) and len(balance) > 0:
                        balance_text = "年度资产负债表:\n"
                        for record in balance[:2]:  # 最近2年
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                balance_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                balance_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                balance_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                balance_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            balance_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(balance_text)
                except Exception as e:
                    logger.warning(f"格式化资产负债表失败: {e}")
            
            if fundamental_data.get('Cashflow'):
                try:
                    cashflow = fundamental_data['Cashflow']
                    if isinstance(cashflow, list) and len(cashflow) > 0:
                        cashflow_text = "年度现金流量表:\n"
                        for record in cashflow[:2]:  # 最近2年
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                cashflow_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                cashflow_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                cashflow_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                cashflow_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            cashflow_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(cashflow_text)
                except Exception as e:
                    logger.warning(f"格式化现金流量表失败: {e}")
            
            fundamental_text = "\n\n".join(fundamental_sections) if fundamental_sections else None
        else:
            fundamental_text = None
        
        extra_sections = []
        
        extra_text = "\n\n".join(extra_sections) if extra_sections else None
        
        # 评分系统已移除
        
        # 准备周期分析文本
        cycle_info = [
            f"- 主周期: {indicators.get('dominant_cycle', 0):.1f}天 (强度: {indicators.get('cycle_strength', 0):.1f}%)",
            f"- 状态: {indicators.get('cycle_status', 'unknown')}",
            f"- 预测方向: {indicators.get('cycle_prediction', 'neutral')}",
            f"- 下一个拐点: {indicators.get('next_turning_point', 'unknown')}"
        ]
        
        if indicators.get('avg_cycle_length'):
            cycle_info.append(f"- 平均周期长度: {indicators.get('avg_cycle_length'):.1f}天")
        if indicators.get('cycle_stability'):
            cycle_info.append(f"- 周期稳定性: {indicators.get('cycle_stability')} ({indicators.get('cycle_stability_desc', '')})")
        if indicators.get('sideways_market') is not None:
            sideways = "是" if indicators.get('sideways_market') else "否"
            cycle_info.append(f"- 是否横盘: {sideways}")
            if indicators.get('sideways_market'):
                cycle_info.append(f"  - 横盘强度: {indicators.get('sideways_strength', 0)*100:.0f}%")
                cycle_info.append(f"  - 20日振幅: {indicators.get('sideways_amplitude_20', 0):.2f}%")
        if indicators.get('cycle_phase'):
            cycle_info.append(f"- 周期阶段: {indicators.get('cycle_phase')} ({indicators.get('cycle_phase_desc', '')})")
            cycle_info.append(f"  - 周期位置: {indicators.get('cycle_position', 0)*100:.0f}% (距低点{indicators.get('days_from_last_trough', 0)}天)")
            
        # 添加年度和月度周期数据
        import json
        if indicators.get('yearly_cycles'):
            cycle_info.append(f"- 年度周期 (Yearly Cycles): {json.dumps(indicators.get('yearly_cycles'), ensure_ascii=False)}")
        if indicators.get('monthly_cycles'):
            cycle_info.append(f"- 月度周期 (Monthly Cycles): {json.dumps(indicators.get('monthly_cycles'), ensure_ascii=False)}")
        if indicators.get('cycle_summary'):
            cycle_info.append(f"- 周期总结: {indicators.get('cycle_summary')}")
        
        cycle_text_block = "\n".join(cycle_info)
        
        sar_val = indicators.get('sar')
        sar_str = fmt_price(sar_val) if sar_val is not None and sar_val != 0 else '未计算'
        
        # 准备新闻文本
        news_data = indicators.get('news_data', [])
        news_text = ""
        if news_data:
            news_text = "## 最新新闻\n"
            for item in news_data:
                title = item.get('title', '无标题')
                publisher = item.get('publisher', '未知来源')
                pub_time = item.get('provider_publish_time_fmt', '')
                time_str = f" [{pub_time}]" if pub_time else ""
                news_text += f"- **{title}** ({publisher}){time_str}\n"
        
        if has_fundamental:
            try:
                prompt = f"""# 分析对象
**股票代码:** {symbol.upper()}  
**当前价格:** {fmt_price(indicators.get('current_price', 0))}  
**货币单位:** {currency_symbol}{f" (代码: {currency_code})" if currency_code else ""}  
**分析周期:** {duration} ({indicators.get('data_points', 0)}个交易日)

---

# 技术指标数据

## 1. 趋势指标
- 移动平均线: MA5={fmt_price(indicators.get('ma5', 0))}, MA20={fmt_price(indicators.get('ma20', 0))}, MA50={fmt_price(indicators.get('ma50', 0))}
   - 趋势方向: {indicators.get('trend_direction', 'neutral')}
   - 趋势强度: {indicators.get('trend_strength', 0):.0f}%
- ADX: {indicators.get('adx', 0):.1f} (+DI={indicators.get('plus_di', 0):.1f}, -DI={indicators.get('minus_di', 0):.1f})
- SuperTrend: {fmt_price(indicators.get('supertrend', 0))} (方向: {indicators.get('supertrend_direction', 'neutral')})
- Ichimoku云层: {indicators.get('ichimoku_status', 'unknown')}
- SAR止损位: {fmt_price(indicators.get('sar', 0))}

## 2. 动量指标
- RSI(14): {indicators.get('rsi', 0):.1f}
- MACD: {indicators.get('macd', 0):.3f} (信号: {indicators.get('macd_signal', 0):.3f}, 柱状图: {indicators.get('macd_histogram', 0):.3f})
- KDJ: K={indicators.get('kdj_k', 0):.1f}, D={indicators.get('kdj_d', 0):.1f}, J={indicators.get('kdj_j', 0):.1f}
- CCI: {indicators.get('cci', 0):.1f}
- StochRSI: K={indicators.get('stoch_rsi_k', 0):.1f}, D={indicators.get('stoch_rsi_d', 0):.1f} (状态: {indicators.get('stoch_rsi_status', 'neutral')})

## 3. 波动性指标
- 布林带: 上轨={fmt_price(indicators.get('bb_upper', 0))}, 中轨={fmt_price(indicators.get('bb_middle', 0))}, 下轨={fmt_price(indicators.get('bb_lower', 0))}
- ATR: {fmt_price(indicators.get('atr', 0))} ({indicators.get('atr_percent', 0):.1f}%)
- 20日波动率: {indicators.get('volatility_20', 0):.2f}%

## 4. 成交量分析
- 成交量比率: {indicators.get('volume_ratio', 0):.2f}x (当前/20日均量)
- OBV趋势: {indicators.get('obv_trend', 'neutral')}
- 价量关系: {indicators.get('price_volume_confirmation', 'neutral')}
- Volume Profile: POC={fmt_price(indicators.get('vp_poc', 0))}, 状态={indicators.get('vp_status', 'neutral')}

## 5. 支撑压力位
- 20日高点: {fmt_price(indicators.get('resistance_20d_high', 0))}
- 20日低点: {fmt_price(indicators.get('support_20d_low', 0))}
- 枢轴点: {fmt_price(indicators.get('pivot', 0))}
- 斐波那契回撤: 23.6%={fmt_price(indicators.get('fib_23.6', 0))}, 38.2%={fmt_price(indicators.get('fib_38.2', 0))}, 61.8%={fmt_price(indicators.get('fib_61.8', 0))}

## 6. 周期分析
{cycle_text_block}

## 7. 其他指标
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}

{options_text}

{news_text}

{f'# 基本面数据{chr(10)}{fundamental_text}{chr(10)}' if fundamental_text else ''}# 市场数据
{extra_text if extra_text else '无额外市场数据'}

---

# 分析任务

请按照以下结构提供全面分析，每个部分都要有深度和洞察：

## 一、技术面综合分析

基于技术指标数据，详细分析（请结合最新新闻事件进行解读）：

1. **趋势方向维度**
   - 解释当前趋势状态（上涨/下跌/横盘）及其强度
   - 分析MA均线排列、ADX趋势强度、SuperTrend和Ichimoku云层的综合指示
   - 判断趋势的可靠性和持续性
   - **结合新闻分析**：评估最新新闻事件对趋势的影响，是否有重大利好/利空消息推动或改变趋势

2. **动量指标维度**
   - 分析RSI、MACD、KDJ等动量指标的综合信号
   - 评估当前市场动能状态（超买/超卖/中性）
   - 识别可能的反转或延续信号
   - **结合新闻分析**：判断新闻事件是否与动量指标信号一致，是否存在消息面与技术面的共振或背离

3. **成交量分析维度**
   - 深入分析价量关系（价涨量增/价跌量增/背离等）
   - 评估成交量的健康度和趋势确认作用
   - 分析OBV和Volume Profile显示的筹码分布情况
   - **结合新闻分析**：分析新闻事件是否引发异常放量，市场对消息的反应是否健康

4. **波动性维度**
   - 评估当前波动率水平对交易的影响
   - 分析布林带位置显示的短期价格区间
   - **结合新闻分析**：评估新闻事件是否增加了市场不确定性，是否需要调整风险控制策略

5. **支撑压力维度**
   - 识别关键支撑位和压力位
   - 评估当前价格位置的优势/劣势
   - 预测可能的突破或反弹点位
   - **结合新闻分析**：判断新闻事件是否可能成为突破关键位的催化剂，或提供新的支撑/压力参考

6. **高级指标维度**
   - 综合ML预测、连续涨跌天数等高级信号
   - 评估市场情绪和极端状态
   - **结合新闻分析**：综合新闻情绪与市场情绪指标，判断是否存在情绪极端或反转信号

## 二、技术面深度分析

1. **趋势分析**
   - 当前趋势方向、强度和可持续性
   - 关键均线的支撑/阻力作用
   - ADX显示的 trend strength 和 direction

2. **动量分析**
   - 各项动量指标的共振情况
   - 超买超卖状态及其可能影响
   - 可能的反转时点和信号

3. **成交量验证**
   - 成交量是否支持当前趋势
   - 价量背离的风险提示
   - 资金流向和筹码分布分析

4. **波动性评估**
   - ATR显示的波动风险
   - 布林带宽度和价格位置

## 三、基本面分析（如果有数据）

1. **财务状况评估**
   - 盈利能力（净利润、毛利率、净利率等）
   - 现金流健康度
   - 财务稳健性（负债率、流动比率等）

2. **业务趋势分析**
   - 营收和利润的增长趋势
   - 季度和年度对比
   - 行业地位和竞争力

3. **估值水平判断**
   - PE、PB、ROE等估值指标
   - 与行业和历史估值对比
   - 当前估值的合理性

4. **市场认可度**
   - 分析师评级和目标价
   - 市场情绪和预期

## 四、最新动态

1. **新闻事件**
   - 重要新闻及其可能影响
   - 市场关注焦点
   - 潜在催化剂

## 三、综合分析结论

1. **技术分析总结**
   - 基于以上所有技术维度的综合判断
   - 总结当前市场所处的阶段（如：超跌反弹、趋势延续、高位震荡等）

2. **风险提示**
   - 技术风险点（高波动、趋势不明、背离等）
   - 基本面风险点（财务恶化、估值过高、竞争加剧等）

3. **市场展望**
   - 短期（1-2周）价格走势预测
   - 中期（1-3个月）趋势展望
   - 不同市场情境下的应对策略

---

# 输出要求

1. **结构清晰**: 严格按照上述五个部分组织内容，使用明确的标题和分段
2. **数据引用**: 分析时要引用具体的技术指标数值和基本面数据
3. **逻辑严密**: 每个结论都要有数据支撑和逻辑推理
4. **重点突出**: 对于关键指标要深入分析，对于风险点要明确警示
5. **语言专业**: 使用专业术语但保持可读性，避免过度复杂
6. **分析客观**: 保持中立客观的分析立场，不提供确定性的投资指令

请开始分析。"""
            except Exception as format_error:
                logger.error(f"构建AI提示词失败（有基本面）: {format_error}")
                import traceback
                traceback.print_exc()
                raise format_error
        else:
            try:
                prompt = f"""# 分析对象
**股票代码:** {symbol.upper()}  
**当前价格:** {fmt_price(indicators.get('current_price', 0))}  
**货币单位:** {currency_symbol}{f" (代码: {currency_code})" if currency_code else ""}  
**分析周期:** {duration} ({indicators.get('data_points', 0)}个交易日)  
**⚠️ 注意:** 无基本面数据，仅基于技术分析

---
# 技术指标数据

## 1. 趋势指标
- 移动平均线: MA5={fmt_price(indicators.get('ma5', 0))}, MA20={fmt_price(indicators.get('ma20', 0))}, MA50={fmt_price(indicators.get('ma50', 0))}
   - 趋势方向: {indicators.get('trend_direction', 'neutral')}
   - 趋势强度: {indicators.get('trend_strength', 0):.0f}%
- ADX: {indicators.get('adx', 0):.1f} (+DI={indicators.get('plus_di', 0):.1f}, -DI={indicators.get('minus_di', 0):.1f})
- SuperTrend: {fmt_price(indicators.get('supertrend', 0))} (方向: {indicators.get('supertrend_direction', 'neutral')})
- Ichimoku云层: {indicators.get('ichimoku_status', 'unknown')}
- SAR止损位: {fmt_price(indicators.get('sar', 0))}

## 2. 动量指标
- RSI(14): {indicators.get('rsi', 0):.1f}
- MACD: {indicators.get('macd', 0):.3f} (信号: {indicators.get('macd_signal', 0):.3f}, 柱状图: {indicators.get('macd_histogram', 0):.3f})
- KDJ: K={indicators.get('kdj_k', 0):.1f}, D={indicators.get('kdj_d', 0):.1f}, J={indicators.get('kdj_j', 0):.1f}
- CCI: {indicators.get('cci', 0):.1f}
- StochRSI: K={indicators.get('stoch_rsi_k', 0):.1f}, D={indicators.get('stoch_rsi_d', 0):.1f} (状态: {indicators.get('stoch_rsi_status', 'neutral')})
- 威廉指标: {indicators.get('williams_r', 0):.1f}

## 3. 波动性指标
- 布林带: 上轨={fmt_price(indicators.get('bb_upper', 0))}, 中轨={fmt_price(indicators.get('bb_middle', 0))}, 下轨={fmt_price(indicators.get('bb_lower', 0))}
- ATR: {fmt_price(indicators.get('atr', 0))} ({indicators.get('atr_percent', 0):.1f}%)
- 20日波动率: {indicators.get('volatility_20', 0):.2f}%

## 4. 成交量分析
- 成交量比率: {indicators.get('volume_ratio', 0):.2f}x (当前/20日均量)
- OBV趋势: {indicators.get('obv_trend', 'neutral')}
- 价量关系: {indicators.get('price_volume_confirmation', 'neutral')}
- Volume Profile: POC={fmt_price(indicators.get('vp_poc', 0))}, 状态={indicators.get('vp_status', 'neutral')}

## 5. 支撑压力位
- 20日高点: {fmt_price(indicators.get('resistance_20d_high', 0))}
- 20日低点: {fmt_price(indicators.get('support_20d_low', 0))}
- 枢轴点: {fmt_price(indicators.get('pivot', 0))}
- 斐波那契回撤: 23.6%={fmt_price(indicators.get('fib_23.6', 0))}, 38.2%={fmt_price(indicators.get('fib_38.2', 0))}, 61.8%={fmt_price(indicators.get('fib_61.8', 0))}

## 6. 周期分析
{cycle_text_block}

## 7. 其他指标
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}

{options_text}

{news_text}

# 市场数据
{extra_text if extra_text else '无额外市场数据'}

---
# 分析任务

请按照以下结构提供纯技术分析，每个部分都要有深度：

## 一、技术面综合分析

基于技术指标数据，详细分析各维度的技术含义：

1. **趋势方向维度**
   - 解释当前趋势状态及其强度
   - 分析MA均线排列、ADX、SuperTrend的综合指示
   - 判断趋势的可靠性和持续性

2. **动量指标维度**
   - 分析RSI、MACD、KDJ等动量指标的综合信号
   - 评估当前市场动能状态
   - 识别可能的反转或延续信号

3. **成交量分析维度**
   - 深入分析价量关系
   - 评估成交量的健康度和趋势确认作用
   - 分析筹码分布情况

4. **波动性维度**
   - 评估当前波动率水平对交易的影响
   - 分析布林带位置显示的短期价格区间

5. **支撑压力维度**
   - 识别关键支撑位和压力位
   - 评估当前价格位置
   - 预测可能的突破或反弹点位

6. **高级指标维度**
   - 综合连续涨跌天数等高级信号
   - 评估市场情绪和极端状态

## 二、技术面深度分析

1. **趋势分析**
   - 当前趋势方向、强度和可持续性
   - 关键均线的支撑/阻力作用
   - ADX显示的trend strength

2. **动量分析**
   - 各项动量指标的共振情况
   - 超买超卖状态及其可能影响
   - 可能的反转时点和信号

3. **成交量验证**
   - 成交量是否支持当前趋势
   - 价量背离的风险提示
   - 资金流向分析

4. **波动性评估**
   - ATR显示的波动风险
   - 布林带宽度和价格位置

## 三、综合分析结论

1. **技术分析总结**
   - 基于以上所有技术维度的综合判断
   - 总结当前市场所处的阶段（如：超跌反弹、趋势延续、高位震荡等）

2. **风险提示**
   - 技术风险点（高波动、趋势不明、背离等）

3. **市场展望**
   - 短期价格走势预测
   - 中期趋势展望
   - 不同市场情境下的应对策略

---
# 输出要求

1. **结构清晰**: 严格按照上述五个部分组织内容，使用明确的标题和分段
2. **数据引用**: 分析时要引用具体的技术指标数值
3. **逻辑严密**: 每个结论都要有数据支撑
4. **重点突出**: 对于关键指标要深入分析
5. **语言专业**: 使用专业术语但保持可读性
6. **分析客观**: 保持中立客观的分析立场，不提供确定性的投资指令

请开始分析。"""
            except Exception as format_error:
                logger.error(f"构建AI提示词失败（无基本面）: {format_error}")
                import traceback
                traceback.print_exc()
                raise format_error
        
        ollama_host = os.getenv('OLLAMA_HOST', OLLAMA_HOST)
        ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', '240'))
        logger.info(f"使用 Ollama 主机: {ollama_host}, 模型: {model}, 超时: {ollama_timeout}秒")
        
        client = ollama.Client(host=ollama_host, timeout=ollama_timeout)
        logger.info(f"开始发送 AI 分析请求，模型: {model}")
        response = client.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt
            }]
        )
        logger.info(f"Ollama AI 分析请求成功，响应长度: {len(response.get('message', {}).get('content', ''))}")
        
        ai_result = response['message']['content']
        
        return ai_result, prompt
        
    except Exception as ai_error:
        logger.error(f"AI分析失败: {ai_error}")
        error_msg = f'AI分析不可用: {str(ai_error)}\n\n请确保Ollama已安装并运行: ollama serve'
        return error_msg, None

