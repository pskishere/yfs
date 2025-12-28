#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析模块 - 技术指标计算、交易信号生成和AI分析
"""

import numpy as np
import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from .yfinance import get_historical_data, get_fundamental_data

from .indicators import (
    calculate_ma, calculate_rsi, calculate_bollinger, calculate_macd,
    calculate_volume, calculate_price_change, calculate_volatility,
    calculate_support_resistance, calculate_kdj, calculate_atr,
    calculate_williams_r, calculate_obv, analyze_trend_strength,
    calculate_fibonacci_retracement, get_trend,
    calculate_cci, calculate_adx, calculate_sar,
    calculate_supertrend, calculate_stoch_rsi, calculate_volume_profile,
    calculate_ichimoku, calculate_cycle_analysis
)
from .indicators.ml_predictions import calculate_ml_predictions

# 直接导入 ollama，如果失败会在导入时抛出异常
try:
    import ollama
except ImportError:
    ollama = None  # 如果未安装，设置为 None，在需要时检查

logger = logging.getLogger(__name__)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "deepseek-v3.2:cloud")


def calculate_technical_indicators(symbol: str, duration: str = '1 M', bar_size: str = '1 day'):
    """
    计算技术指标（基于历史数据）
    返回：移动平均线、RSI、MACD等
    如果证券不存在，返回(None, error_info)
    """
    hist_data, error = get_historical_data(symbol, duration, bar_size)
    
    if error:
        return None, error
    
    if not hist_data or len(hist_data) < 20:
        logger.warning(f"数据不足，无法计算技术指标: {symbol}")
        return None, None
    
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
        cycle_data = calculate_cycle_analysis(closes, highs, lows, timestamps if timestamps else None)
        result.update(cycle_data)

    if len(closes) >= 20 and len(valid_volumes) > 0:
        ml_data = calculate_ml_predictions(closes, highs, lows, volumes)
        result.update(ml_data)

    try:
        fundamental_data = get_fundamental_data(symbol)
        if fundamental_data:
            result['fundamental_data'] = fundamental_data
            logger.info(f"已获取基本面数据: {symbol}")
    except Exception as e:
        logger.warning(f"获取基本面数据失败: {symbol}, 错误: {e}")
        result['fundamental_data'] = None
        
    return result, None  # 返回结果和错误信息（无错误为None）


def generate_signals(indicators: dict, account_value: float = 100000, risk_percent: float = 2.0):
    """
    基于技术指标生成买卖信号
    """
    if not indicators:
        return None
        
    signals = {
        'symbol': indicators.get('symbol'),
        'current_price': indicators.get('current_price'),
        'signals': [],
        'score': 0,
    }
    
    signals_list = signals['signals']
    
    add_ma_signals(signals_list, indicators)
    add_rsi_signals(signals_list, indicators)
    add_bollinger_signals(signals_list, indicators)
    add_macd_signals(signals_list, indicators)
    add_volume_signals(signals_list, indicators)
    add_trend_signals(signals_list, indicators)
    add_advanced_indicator_signals(signals_list, indicators)
    
    current_price = indicators.get('current_price')
    if current_price:
        support_keys = [k for k in indicators.keys() if 'support' in k.lower()]
        resistance_keys = [k for k in indicators.keys() if 'resistance' in k.lower()]
        
        nearest_support = None
        nearest_support_dist = float('inf')
        for key in support_keys:
            support = indicators[key]
            if support < current_price:
                dist = current_price - support
                dist_pct = (dist / current_price) * 100
                if dist_pct < nearest_support_dist:
                    nearest_support = support
                    nearest_support_dist = dist_pct
        
        nearest_resistance = None
        nearest_resistance_dist = float('inf')
        for key in resistance_keys:
            resistance = indicators[key]
            if resistance > current_price:
                dist = resistance - current_price
                dist_pct = (dist / current_price) * 100
                if dist_pct < nearest_resistance_dist:
                    nearest_resistance = resistance
                    nearest_resistance_dist = dist_pct
        
        if nearest_support and nearest_support_dist < 2:
            signals['signals'].append(f'🟢 接近支撑位${nearest_support:.2f} (距离{nearest_support_dist:.1f}%) - 可能反弹')
        
        if nearest_resistance and nearest_resistance_dist < 2:
            signals['signals'].append(f'🔴 接近压力位${nearest_resistance:.2f} (距离{nearest_resistance_dist:.1f}%) - 可能回调')
        
        if 'resistance_20d_high' in indicators:
            high_20 = indicators['resistance_20d_high']
            if current_price >= high_20 * 0.99:
                signals['signals'].append(f'🚀 突破20日高点${high_20:.2f} - 强势信号')
        
        if 'support_20d_low' in indicators:
            low_20 = indicators['support_20d_low']
            if current_price <= low_20 * 1.01:
                signals['signals'].append(f'⚠️ 跌破20日低点${low_20:.2f} - 弱势信号')
    
    if 'vp_poc' in indicators:
        poc = indicators['vp_poc']
        current_price = indicators.get('current_price', 0)
        vp_status = indicators.get('vp_status', 'inside_va')
        
        dist_pct = (current_price - poc) / poc * 100
        
        if abs(dist_pct) < 0.5:
            signals['signals'].append(f'⚖️ 价格在POC(${poc:.2f})附近 - 筹码密集区平衡')
        elif vp_status == 'above_va':
            signals['signals'].append(f'📈 价格在价值区域上方(POC ${poc:.2f}) - 强势失衡')
        elif vp_status == 'below_va':
            signals['signals'].append(f'📉 价格在价值区域下方(POC ${poc:.2f}) - 弱势失衡')
    
    if 'ml_trend' in indicators:
        ml_trend = indicators['ml_trend']
        ml_confidence = indicators.get('ml_confidence', 0)
        ml_prediction = indicators.get('ml_prediction', 0)
        
        if ml_confidence > 50:
            if ml_trend == 'up':
                signals['signals'].append(f'🤖 ML预测: 看涨趋势(置信度{ml_confidence:.1f}%, 预期涨幅{ml_prediction*100:.2f}%) - AI看多')
            elif ml_trend == 'down':
                signals['signals'].append(f'🤖 ML预测: 看跌趋势(置信度{ml_confidence:.1f}%, 预期跌幅{ml_prediction*100:.2f}%) - AI看空')
            else:
                signals['signals'].append(f'🤖 ML预测: 横盘整理(置信度{ml_confidence:.1f}%) - AI中性')
        elif ml_confidence > 30:
            if ml_trend == 'up':
                signals['signals'].append(f'🤖 ML预测: 轻微看涨(置信度{ml_confidence:.1f}%) - 谨慎乐观')
            elif ml_trend == 'down':
                signals['signals'].append(f'🤖 ML预测: 轻微看跌(置信度{ml_confidence:.1f}%) - 谨慎悲观')
            
    # 评分系统已移除
    signals['recommendation'] = 'N/A'
    signals['action'] = 'hold'
    
    risk_assessment = assess_risk(indicators)
    signals['risk'] = {
        'level': risk_assessment['level'],
        'score': risk_assessment['score'],
        'factors': risk_assessment['factors']
    }
    signals['risk_level'] = risk_assessment['level']
    signals['risk_score'] = risk_assessment['score']
    signals['risk_factors'] = risk_assessment['factors']
    
    stop_loss_profit = calculate_stop_loss_profit(indicators, action='buy', account_value=account_value, risk_percent=risk_percent)
    signals['stop_loss'] = stop_loss_profit.get('stop_loss')
    signals['take_profit'] = stop_loss_profit.get('take_profit')
    signals['risk_reward_ratio'] = stop_loss_profit.get('risk_reward_ratio')
    signals['position_sizing'] = stop_loss_profit.get('position_sizing_advice')
        
    return signals


def assess_risk(indicators: dict):
    """
    评估投资风险等级
    """
    risk_score = 0
    risk_factors = []
    
    if 'volatility_20' in indicators:
        vol = indicators['volatility_20']
        if vol > 5:
            risk_score += 30
            risk_factors.append(f'极高波动率({vol:.1f}%)')
        elif vol > 3:
            risk_score += 20
            risk_factors.append(f'高波动率({vol:.1f}%)')
        elif vol > 2:
            risk_score += 10
            risk_factors.append(f'中等波动率({vol:.1f}%)')
    
    if 'rsi' in indicators:
        rsi = indicators['rsi']
        if rsi > 85 or rsi < 15:
            risk_score += 20
            risk_factors.append(f'RSI极端值({rsi:.1f})')
    
    if 'consecutive_up_days' in indicators:
        up_days = indicators['consecutive_up_days']
        if up_days >= 7:
            risk_score += 25
            risk_factors.append(f'连续上涨{up_days}天(回调风险)')
        elif up_days >= 5:
            risk_score += 15
            risk_factors.append(f'连续上涨{up_days}天')
    
    if 'consecutive_down_days' in indicators:
        down_days = indicators['consecutive_down_days']
        if down_days >= 7:
            risk_score += 25
            risk_factors.append(f'连续下跌{down_days}天(继续下跌风险)')
        elif down_days >= 5:
            risk_score += 15
            risk_factors.append(f'连续下跌{down_days}天')
    
    current_price = indicators.get('current_price')
    if current_price and 'support_20d_low' in indicators:
        support = indicators['support_20d_low']
        dist_to_support = ((current_price - support) / current_price) * 100
        if dist_to_support < 2:
            risk_score += 15
            risk_factors.append('接近重要支撑位')
    
    if current_price and 'resistance_20d_high' in indicators:
        resistance = indicators['resistance_20d_high']
        dist_to_resistance = ((resistance - current_price) / current_price) * 100
        if dist_to_resistance < 2:
            risk_score += 15
            risk_factors.append('接近重要压力位')
    
    if 'trend_strength' in indicators:
        strength = indicators['trend_strength']
        if strength < 15:
            risk_score += 10
            risk_factors.append('趋势不明确')
    
    if 'obv_trend' in indicators:
        obv_trend = indicators['obv_trend']
        price_change = indicators.get('price_change_pct', 0)
        
        if (obv_trend == 'up' and price_change < -1) or (obv_trend == 'down' and price_change > 1):
            risk_score += 15
            risk_factors.append('量价背离')
    
    if 'adx' in indicators:
        adx = indicators['adx']
        if adx < 20:
            risk_score += 10
            risk_factors.append(f'ADX({adx:.1f})趋势不明确')
        elif adx > 60:
            risk_score += 15
            risk_factors.append(f'ADX({adx:.1f})趋势过强可能反转')
    
    if risk_score >= 70:
        level = 'very_high'
    elif risk_score >= 50:
        level = 'high'
    elif risk_score >= 30:
        level = 'medium'
    elif risk_score >= 15:
        level = 'low'
    else:
        level = 'very_low'
    
    return {
        'level': level,
        'score': int(risk_score),
        'factors': risk_factors
    }


def calculate_stop_loss_profit(indicators: dict, action: str = 'buy', account_value: float = 100000, risk_percent: float = 2.0):
    """
    计算建议的止损和止盈价位
    
    Args:
        indicators: 技术指标字典
        action: 操作类型 'buy' 或 'sell'
        account_value: 账户金额（美元）
        risk_percent: 单笔交易风险百分比（默认2%）
    """
    current_price = indicators.get('current_price')
    if not current_price:
        return {}
    
    result = {}
    volatility = indicators.get('volatility_20', 2.0)
    
    if volatility > 4:
        atr_stop_multiplier = 2.5
        atr_profit_multiplier = 4.0
    elif volatility > 2.5:  # 中等波动
        atr_stop_multiplier = 2.0
        atr_profit_multiplier = 3.5
    else:  # 低波动
        atr_stop_multiplier = 1.5
        atr_profit_multiplier = 3.0
    
    if 'atr' in indicators:
        atr = indicators['atr']
        if action == 'buy':
            result['stop_loss'] = float(current_price - atr_stop_multiplier * atr)
            result['take_profit'] = float(current_price + atr_profit_multiplier * atr)
        else:  # sell
            result['stop_loss'] = float(current_price + atr_stop_multiplier * atr)
            result['take_profit'] = float(current_price - atr_profit_multiplier * atr)
    elif 'support_20d_low' in indicators and 'resistance_20d_high' in indicators:
        support = indicators['support_20d_low']
        resistance = indicators['resistance_20d_high']
        if action == 'buy':
            result['stop_loss'] = float(support * 0.98)
            result['take_profit'] = float(resistance)
        else:  # sell
            result['stop_loss'] = float(resistance * 1.02)
            result['take_profit'] = float(support)
    else:
        if action == 'buy':
            result['stop_loss'] = float(current_price * 0.95)
            result['take_profit'] = float(current_price * 1.10)
        else:  # sell
            result['stop_loss'] = float(current_price * 1.05)
            result['take_profit'] = float(current_price * 0.90)
    
    if action == 'buy':
        risk = current_price - result['stop_loss']
        reward = result['take_profit'] - current_price
    else:  # sell
        risk = result['stop_loss'] - current_price
        reward = current_price - result['take_profit']
    
    if risk > 0:
        result['risk_reward_ratio'] = float(reward / risk)
    
    position_sizing = calculate_position_sizing(indicators, result, account_value, risk_percent)
    result.update(position_sizing)
    
    return result


def calculate_position_sizing(indicators: dict, stop_loss_data: dict, account_value: float = 100000, risk_percent: float = 2.0):
    """
    计算建议的仓位大小和风险管理
    
    Args:
        indicators: 技术指标字典
        stop_loss_data: 止损数据（包含 stop_loss）
        account_value: 账户金额（美元）
        risk_percent: 单笔交易风险百分比
    """
    result = {}
    
    current_price = indicators.get('current_price')
    stop_loss = stop_loss_data.get('stop_loss')
    
    if not current_price or not stop_loss:
        return result
        
    risk_per_share = abs(current_price - stop_loss)
    max_risk_amount = account_value * (risk_percent / 100.0)
    
    if risk_per_share > 0:
        suggested_position_size = int(max_risk_amount / risk_per_share)
        result['suggested_position_size'] = suggested_position_size
        result['position_risk_amount'] = float(suggested_position_size * risk_per_share)
        
        position_value = suggested_position_size * current_price
        result['position_value'] = float(position_value)
        
        position_ratio = (position_value / account_value) * 100
        result['position_ratio'] = float(position_ratio)
        
        risk_level = indicators.get('risk_level', 'medium')
        risk_multiplier = {
            'very_low': 1.5,
            'low': 1.2,
            'medium': 1.0,
            'high': 0.7,
            'very_high': 0.5
        }
        
        adjusted_position_size = int(suggested_position_size * risk_multiplier.get(risk_level, 1.0))
        result['adjusted_position_size'] = adjusted_position_size
        
        result['position_sizing_advice'] = {
            'max_risk_percent': float(risk_percent),
            'risk_per_share': float(risk_per_share),
            'suggested_size': suggested_position_size,
            'adjusted_size': adjusted_position_size,
            'position_value': float(position_value),
            'account_value': float(account_value)
        }
    
    return result


def check_ollama_available():
    """
    检查 Ollama 是否可用
    """
    if ollama is None:
        return False
    
    import requests
    
    ollama_host = os.getenv('OLLAMA_HOST', OLLAMA_HOST)
    try:
        # 检查服务是否可达
        response = requests.get(f'{ollama_host}/api/tags', timeout=5)
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        logger.debug(f"Ollama 服务不可用: {e}")
        return False


def _safe_get(d, key, default=0):
    """
    安全地从字典获取数值，确保返回值不是None
    """
    val = d.get(key, default) if isinstance(d, dict) else default
    return default if val is None else val


def perform_ai_analysis(symbol, indicators, signals, duration, model=DEFAULT_AI_MODEL, extra_data=None):
    """
    执行AI分析的辅助函数
    """
    if ollama is None:
        raise RuntimeError("ollama 模块未安装，无法执行 AI 分析")
    
    try:
        # 确保所有可能用于格式化的值不是None
        indicators = indicators or {}
        signals = signals or {}
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
        if extra_data:
            if extra_data.get('institutional_holders'):
                inst = extra_data['institutional_holders']
                inst_text = f"机构持仓 (前{min(len(inst), 10)}大机构):\n"
                for i, holder in enumerate(inst[:10], 1):
                    name = holder.get('Holder', '未知')
                    shares = holder.get('Shares', 0) or 0
                    value = holder.get('Value', 0) or 0
                    pct = (holder.get('% Out') or holder.get('%Out') or holder.get('pctHeld') or 
                           holder.get('Percent') or holder.get('% Held') or holder.get('pct_held'))
                    if pct is not None:
                        try:
                            pct_val = float(pct)
                            if pct_val < 1:
                                pct_str = f"{(pct_val * 100):.2f}%"
                            else:
                                pct_str = f"{pct_val:.2f}%"
                        except:
                            pct_str = str(pct)
                    else:
                        pct_str = 'N/A'
                    inst_text += f"   {i}. {name}\n"
                    try:
                        inst_text += f"      持股: {int(shares):,}, 市值: ${int(value):,.0f}, 占比: {pct_str}\n"
                    except:
                        inst_text += f"      持股: {shares}, 市值: ${value}, 占比: {pct_str}\n"
                extra_sections.append(inst_text)
            
            # 分析师推荐
            if extra_data.get('analyst_recommendations'):
                recs = extra_data['analyst_recommendations']
                rec_text = f"分析师推荐 (最近{min(len(recs), 8)}条):\n"
                for i, rec in enumerate(recs[:8], 1):
                    firm = rec.get('Firm', '未知')
                    to_grade = rec.get('To Grade', '未知')
                    from_grade = rec.get('From Grade', '')
                    action = rec.get('Action', '')
                    if from_grade and action:
                        rec_text += f"   {i}. {firm}: {from_grade} → {to_grade} ({action})\n"
                    else:
                        rec_text += f"   {i}. {firm}: {to_grade}\n"
                extra_sections.append(rec_text)
            
            if extra_data.get('earnings'):
                earnings_data = extra_data['earnings']
                quarterly = earnings_data.get('quarterly', [])
                if quarterly:
                    earn_text = f"季度收益 (最近{min(len(quarterly), 8)}个季度):\n"
                    for q in quarterly[:8]:
                        quarter = q.get('quarter', '未知')
                        revenue = q.get('Revenue', 0) or 0
                        earnings_val = q.get('Earnings', 0) or 0
                        try:
                            rev_b = float(revenue) / 1e9 if revenue else 0
                            earn_b = float(earnings_val) / 1e9 if earnings_val else 0
                            earn_text += f"   {quarter}: 营收 ${rev_b:.2f}B, 盈利 ${earn_b:.2f}B\n"
                        except:
                            earn_text += f"   {quarter}: 营收 {revenue}, 盈利 {earnings_val}\n"
                    extra_sections.append(earn_text)
            
            if extra_data.get('news'):
                news = extra_data['news']
                news_text = f"最新新闻 (最近{len(news)}条标题):\n"
                for i, item in enumerate(news, 1):
                    title = item.get('title', '未知')
                    publisher = item.get('publisher', '')
                    news_text += f"   {i}. {title}"
                    if publisher:
                        news_text += f" [{publisher}]"
                    news_text += "\n"
                extra_sections.append(news_text)
        
        extra_text = "\n\n".join(extra_sections) if extra_sections else None
        
        # 评分系统已移除
        
        stop_loss_val = signals.get('stop_loss')
        stop_loss_str = fmt_price(stop_loss_val) if stop_loss_val is not None else '未计算'
        take_profit_val = signals.get('take_profit')
        take_profit_str = fmt_price(take_profit_val) if take_profit_val is not None else '未计算'
        sar_val = indicators.get('sar')
        sar_str = fmt_price(sar_val) if sar_val is not None and sar_val != 0 else '未计算'
        atr_val = indicators.get('atr')
        atr_str = fmt_price(atr_val) if atr_val is not None and atr_val != 0 else '未计算'
        
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

## 6. 其他指标
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}
- ML预测: {indicators.get('ml_trend', 'unknown')} (置信度: {indicators.get('ml_confidence', 0):.1f}%, 预期: {indicators.get('ml_prediction', 0)*100:.2f}%)

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
   - 给出风险控制和仓位建议
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
   - 止损止盈位设置建议

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
   - 机构持仓情况
   - 分析师评级和目标价
   - 市场情绪和预期

## 四、市场行为分析（如果有数据）

1. **机构投资者行为**
   - 主要机构持仓分析
   - 机构持仓变化趋势
   - 机构认可度评估

2. **分析师观点**
   - 评级变化趋势
   - 目标价合理性
   - 市场共识判断

3. **最新动态**
   - 重要新闻事件
   - 市场关注焦点
   - 潜在催化剂

## 五、综合分析结论

1. **买卖建议**
   - 基于技术指标的综合判断
   - 明确的操作建议（买入/卖出/观望）及理由

2. **具体操作价位（必须明确给出）**
   
   **如果建议买入:**
   - **建议买入价位:** {currency_symbol}[具体价格或价格区间，例如: {currency_symbol}150.50 或 {currency_symbol}149.00-{currency_symbol}151.00]
     - 说明：为什么选择这个价位？基于什么技术指标？（如支撑位、均线、布林带等）
   - **建议止损价位:** {currency_symbol}[具体价格，例如: {currency_symbol}147.00]
     - 说明：基于什么计算？（SAR={fmt_price(indicators.get('sar', 0))}、ATR={fmt_price(indicators.get('atr', 0))}、支撑位等）
     - 止损百分比: [X]% （相对于买入价）
   - **建议止盈价位:** {currency_symbol}[具体价格，例如: {currency_symbol}158.00]
     - 说明：基于什么计算？（压力位、阻力位、目标价等）
     - 止盈百分比: [X]% （相对于买入价）
     - 风险收益比: 1:[X] （止盈空间/止损空间）
   
   **如果建议卖出:**
   - **建议卖出价位:** {currency_symbol}[具体价格或价格区间]
     - 说明：为什么选择这个价位？
   - **止损/保护价位:** {currency_symbol}[如果卖出后可能上涨，设置保护价位]
   
   **如果建议观望:**
   - **等待的买入价位:** {currency_symbol}[如果价格达到这个价位才考虑买入]
   - **等待的卖出价位:** {currency_symbol}[如果价格达到这个价位才考虑卖出]

3. **风险提示**
   - 技术风险点（高波动、趋势不明、背离等）
   - 基本面风险点（财务恶化、估值过高、竞争加剧等）
   - 综合风险评估
   - 止损位设置的理由和风险控制说明

4. **仓位和资金管理**
   - 建议仓位大小（根据风险等级和资金情况）
   - 分批建仓建议（如有）
   - 资金管理建议（根据风险等级）

5. **市场展望**
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
6. **建议明确**: 操作建议要具体可执行，避免模糊表述
7. **价位必须明确**: 在"具体操作价位"部分，必须明确给出具体的买入价位、止损价位和止盈价位，包括具体价格数字、百分比和风险收益比，不能只给建议不给具体价格

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

## 6. 其他指标
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}
- ML预测: {indicators.get('ml_trend', 'unknown')} (置信度: {indicators.get('ml_confidence', 0):.1f}%, 预期: {indicators.get('ml_prediction', 0)*100:.2f}%)

# 市场数据
{extra_text if extra_text else '无额外市场数据'}

---
# 分析任务

请按照以下结构提供纯技术分析，每个部分都要有深度：

## 一、技术面综合分析

基于技术指标数据，详细分析各维度的技术含义（请结合最新新闻事件进行解读）：

1. **趋势方向维度**
   - 解释当前趋势状态及其强度
   - 分析MA均线排列、ADX、SuperTrend的综合指示
   - 判断趋势的可靠性和持续性
   - **结合新闻分析**：评估最新新闻事件对趋势的影响，是否有重大利好/利空消息推动或改变趋势

2. **动量指标维度**
   - 分析RSI、MACD、KDJ等动量指标的综合信号
   - 评估当前市场动能状态
   - 识别可能的反转或延续信号
   - **结合新闻分析**：判断新闻事件是否与动量指标信号一致，是否存在消息面与技术面的共振或背离

3. **成交量分析维度**
   - 深入分析价量关系
   - 评估成交量的健康度和趋势确认作用
   - 分析筹码分布情况
   - **结合新闻分析**：分析新闻事件是否引发异常放量，市场对消息的反应是否健康

4. **波动性维度**
   - 评估当前波动率水平对交易的影响
   - 分析布林带位置显示的短期价格区间
   - 给出风险控制建议
   - **结合新闻分析**：评估新闻事件是否增加了市场不确定性，是否需要调整风险控制策略

5. **支撑压力维度**
   - 识别关键支撑位和压力位
   - 评估当前价格位置
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
   - 止损止盈位设置建议

## 三、综合分析结论

1. **买卖建议**
   - 基于技术指标的综合判断
   - 明确的操作建议及理由

2. **具体操作价位（必须明确给出）**
   
   **如果建议买入:**
   - **建议买入价位:** $[具体价格或价格区间，例如: $150.50 或 $149.00-$151.00]
     - 说明：为什么选择这个价位？基于什么技术指标？（如支撑位、均线、布林带等）
   - **建议止损价位:** $[具体价格，例如: $147.00]
     - 说明：基于什么计算？（SAR=${indicators.get('sar', 0):.2f}、ATR=${indicators.get('atr', 0):.2f}、支撑位等）
     - 止损百分比: [X]% （相对于买入价）
   - **建议止盈价位:** $[具体价格，例如: $158.00]
     - 说明：基于什么计算？（压力位、阻力位、目标价等）
     - 止盈百分比: [X]% （相对于买入价）
     - 风险收益比: 1:[X] （止盈空间/止损空间）
   
   **如果建议卖出:**
   - **建议卖出价位:** $[具体价格或价格区间]
     - 说明：为什么选择这个价位？
   - **止损/保护价位:** $[如果卖出后可能上涨，设置保护价位]
   
   **如果建议观望:**
   - **等待的买入价位:** $[如果价格达到这个价位才考虑买入]
   - **等待的卖出价位:** $[如果价格达到这个价位才考虑卖出]

3. **风险提示**
   - 技术风险点（高波动、趋势不明、背离等）
   - 纯技术分析的局限性
   - 综合风险评估
   - 止损位设置的理由和风险控制说明

4. **仓位和资金管理**
   - 建议仓位大小（根据风险等级和资金情况）
   - 分批建仓建议（如有）
   - 资金管理建议（根据风险等级）

5. **市场展望**
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
6. **建议明确**: 操作建议要具体可执行
7. **价位必须明确**: 在"具体操作价位"部分，必须明确给出具体的买入价位、止损价位和止盈价位，包括具体价格数字、百分比和风险收益比，不能只给建议不给具体价格

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


# === merged from scoring.py ===
# 评分系统模块已移除 - 以下类保留以避免导入错误，但不再使用


class ScoringSystem:
    """
    多维度加权评分系统
    
    评分体系：
    - 各维度内部评分：0 到 100（百分制）
    - 最终综合评分：0 到 100（百分制）
    - 评分等级：
      * 70-100分：强烈买入/买入/轻度买入
      * 46-69分：中性观望
      * 0-45分：轻度卖出/卖出/强烈卖出
    """
    
    # 各维度权重配置
    WEIGHTS = {
        'trend': 0.25,        # 趋势方向权重
        'momentum': 0.20,     # 动量指标权重
        'volume': 0.15,       # 成交量分析权重
        'volatility': 0.10,   # 波动性权重
        'support_resistance': 0.15,  # 支撑压力权重
        'advanced': 0.15      # 高级指标权重
    }
    
    def __init__(self):
        """初始化评分系统"""
        pass
    
    def _get_adaptive_weights(self, indicators: Dict) -> Dict[str, float]:
        """
        根据股票特征动态调整权重（优化版）
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            调整后的权重字典
        """
        weights = self.WEIGHTS.copy()
        
        volatility = indicators.get('volatility_20', 2.0)
        trend_strength = indicators.get('trend_strength', 0)
        adx = indicators.get('adx', 0)
        volume_ratio = indicators.get('volume_ratio', 1.0)
        price_change = indicators.get('price_change_pct', 0)
        
        # 1. 高波动股票：增加风险管理权重，但不过度降低趋势权重
        if volatility > 4.0:
            weights['volatility'] *= 1.4  # 从1.5降低
            weights['trend'] *= 0.85      # 从0.8提高
            weights['momentum'] *= 0.95   # 从0.9提高
        # 2. 低波动股票：增加动量权重（寻找突破机会）
        elif volatility < 1.5:
            weights['momentum'] *= 1.25   # 从1.3降低，避免过度依赖
            weights['volatility'] *= 0.75  # 从0.7提高
        
        # 3. 强趋势股票：增加趋势和动量权重
        if trend_strength > 70 or adx > 40:
            weights['trend'] *= 1.25       # 从1.3降低
            weights['momentum'] *= 1.15    # 从1.2降低
            weights['support_resistance'] *= 0.85  # 从0.8提高
        # 4. 弱趋势/震荡股票：增加支撑压力位和动量权重（捕捉反弹）
        elif trend_strength < 30 or adx < 20:
            weights['support_resistance'] *= 1.3  # 从1.4降低
            weights['momentum'] *= 1.2     # 新增：震荡市更关注超买超卖
            weights['trend'] *= 0.75       # 从0.7提高
        # 5. 中等趋势（30-70）：均衡权重
        else:
            weights['trend'] *= 1.1
            weights['momentum'] *= 1.1
        
        # 6. 成交量异常：增加成交量权重
        if volume_ratio > 2.0:
            weights['volume'] *= 1.4       # 从1.5降低
        elif volume_ratio < 0.5:
            weights['volume'] *= 0.7       # 从0.6提高
        
        # 7. 反弹信号：价跌量缩后价涨
        if price_change > 0 and volume_ratio < 0.8:
            prev_change = indicators.get('prev_price_change_pct', 0)
            if prev_change < 0:
                weights['momentum'] *= 1.2
                weights['support_resistance'] *= 1.2
        
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def calculate_score(self, indicators: Dict, apply_risk_adjustment: bool = True, use_adaptive_weights: bool = True) -> Tuple[int, Dict]:
        """
        计算综合评分
        
        Args:
            indicators: 技术指标字典
            apply_risk_adjustment: 是否应用风险调整因子（默认True）
            use_adaptive_weights: 是否使用自适应权重（默认True）
            
        Returns:
            (综合评分, 详细评分字典)
            评分范围: 0 到 100（百分制）
        """
        if not indicators:
            return 50, {}
        
        if use_adaptive_weights:
            weights = self._get_adaptive_weights(indicators)
        else:
            weights = self.WEIGHTS
        
        # 各维度评分
        trend_score = self._score_trend(indicators)
        momentum_score = self._score_momentum(indicators)
        volume_score = self._score_volume(indicators)
        volatility_score = self._score_volatility(indicators)
        support_resistance_score = self._score_support_resistance(indicators)
        advanced_score = self._score_advanced(indicators)
        
        def to_weighted_score(score_0_100):
            """将0-100评分转换为-100到100用于加权计算"""
            return (score_0_100 - 50) * 2
        
        base_score = (
            to_weighted_score(trend_score) * weights['trend'] +
            to_weighted_score(momentum_score) * weights['momentum'] +
            to_weighted_score(volume_score) * weights['volume'] +
            to_weighted_score(volatility_score) * weights['volatility'] +
            to_weighted_score(support_resistance_score) * weights['support_resistance'] +
            to_weighted_score(advanced_score) * weights['advanced']
        )
        
        risk_adjustment_factor = 1.0
        risk_level = indicators.get('risk_level', 'medium')
        
        if apply_risk_adjustment:
            risk_adjustment_map = {
                'very_low': 1.12,   # 低风险加成12%
                'low': 1.06,        # 低风险加成6%
                'medium': 1.0,      # 中等风险不调整
                'high': 0.90,       # 高风险惩罚10%
                'very_high': 0.80   # 极高风险惩罚20%
            }
            risk_adjustment_factor = risk_adjustment_map.get(risk_level, 1.0)
        
        adjusted_score = base_score * risk_adjustment_factor
        
        total_score = int(round((adjusted_score + 100) / 2))
        total_score = max(0, min(100, total_score))
        
        score_details = {
            'total': total_score,
            'base_score': round(base_score, 1),
            'adjusted_score': round(adjusted_score, 1),
            'risk_adjustment_factor': round(risk_adjustment_factor, 3),
            'risk_level': risk_level,
            'adaptive_weights_used': use_adaptive_weights,
            'dimensions': {
                'trend': round(trend_score, 1),
                'momentum': round(momentum_score, 1),
                'volume': round(volume_score, 1),
                'volatility': round(volatility_score, 1),
                'support_resistance': round(support_resistance_score, 1),
                'advanced': round(advanced_score, 1)
            },
            'weights': {k: round(v, 3) for k, v in weights.items()},
            'base_weights': self.WEIGHTS
        }
        
        return total_score, score_details
    
    def _score_trend(self, indicators: Dict) -> float:
        """
        趋势方向评分 (0 到 100)
        
        考虑因素:
        - MA均线排列
        - ADX趋势强度
        - SuperTrend
        - Ichimoku云层
        """
        score = 50.0  # 基准分50（中性）
        
        ma_score = 0.0
        if all(k in indicators for k in ['ma5', 'ma20', 'ma50']):
            ma5 = indicators['ma5']
            ma20 = indicators['ma20']
            ma50 = indicators['ma50']
            current_price = indicators.get('current_price', 0)
            
            if current_price > 0:
                if current_price > ma5 > ma20 > ma50:
                    ma_score = 30
                elif current_price < ma5 < ma20 < ma50:
                    ma_score = -30
                elif current_price > ma5 and ma5 > ma20:
                    ma_score = 20
                elif current_price > ma20 and ma20 > ma50:
                    ma_score = 18
                elif current_price > ma5 and ma5 < ma20:
                    ma_score = 12
                elif ma5 < current_price < ma20 or ma20 < current_price < ma5:
                    ma_score = 5
                elif ma5 < ma20 and current_price < ma5:
                    ma_score = -15
                elif current_price < ma20 < ma50:
                    ma_score = -20
        
        score += ma_score * 0.3
        
        adx_score = 0.0
        if 'adx' in indicators:
            adx = indicators['adx']
            adx_signal = indicators.get('adx_signal', 'weak_trend')
            plus_di = indicators.get('plus_di', 0)
            minus_di = indicators.get('minus_di', 0)
            
            if adx_signal == 'strong_trend':
                if plus_di > minus_di:
                    intensity = min(adx / 50.0, 1.0)
                    adx_score = 30 * intensity
                else:
                    intensity = min(adx / 50.0, 1.0)
                    adx_score = -30 * intensity
            elif adx_signal == 'trend':
                if plus_di > minus_di:
                    adx_score = 15
                else:
                    adx_score = -15
        
        score += adx_score * 0.3
        
        supertrend_score = 0.0
        if 'supertrend' in indicators and 'supertrend_direction' in indicators:
            st_dir = indicators['supertrend_direction']
            current_price = indicators.get('current_price', 0)
            st_price = indicators.get('supertrend', 0)
            
            if current_price > 0 and st_price > 0:
                if st_dir == 'up' and current_price > st_price:
                    supertrend_score = 20
                elif st_dir == 'down' and current_price < st_price:
                    supertrend_score = -20
        
        score += supertrend_score * 0.2
        
        ichimoku_score = 0.0
        if all(k in indicators for k in ['ichimoku_cloud_top', 'ichimoku_cloud_bottom', 'ichimoku_status']):
            current_price = indicators.get('current_price', 0)
            cloud_top = indicators.get('ichimoku_cloud_top', 0)
            cloud_bottom = indicators.get('ichimoku_cloud_bottom', 0)
            status = indicators.get('ichimoku_status', 'unknown')
            
            if current_price > 0 and cloud_top > 0 and cloud_bottom > 0:
                if status == 'bullish':
                    ichimoku_score = 20
                elif status == 'bearish':
                    ichimoku_score = -20
                elif current_price > cloud_top:
                    ichimoku_score = 10
                elif current_price < cloud_bottom:
                    ichimoku_score = -10
        
        score += ichimoku_score * 0.2
        
        return max(0, min(100, score))
    
    def _score_momentum(self, indicators: Dict) -> float:
        """
        动量指标评分 (0 到 100)
        
        考虑因素:
        - RSI
        - MACD
        - KDJ
        - CCI
        - StochRSI
        """
        score = 50.0
        
        rsi_score = 0.0
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            if rsi < 30:
                rsi_score = 25 * (30 - rsi) / 30
            elif 30 <= rsi < 45:
                rsi_score = 20
            elif 45 <= rsi < 60:
                if trend_direction == 'up':
                    rsi_score = 18
                else:
                    rsi_score = 10
            elif 60 <= rsi <= 70:
                if trend_direction == 'up':
                    rsi_score = 8
                else:
                    rsi_score = -5
            elif rsi > 70:
                rsi_score = -25 * (rsi - 70) / 30
        
        score += rsi_score * 0.25
        
        macd_score = 0.0
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            histogram = indicators.get('macd_histogram', 0)
            
            if macd > signal:
                macd_score = 25 * min(abs(histogram) * 10, 1.0)
            else:
                macd_score = -25 * min(abs(histogram) * 10, 1.0)
        
        score += macd_score * 0.25
        
        kdj_score = 0.0
        if all(k in indicators for k in ['kdj_k', 'kdj_d', 'kdj_j']):
            k = indicators['kdj_k']
            d = indicators['kdj_d']
            j = indicators['kdj_j']
            
            if j < 20:
                kdj_score = 20 * (20 - j) / 20
            elif j > 80:
                kdj_score = -20 * (j - 80) / 20
            elif k > d:
                kdj_score = 10
            elif k < d:
                kdj_score = -10
        
        score += kdj_score * 0.2
        
        cci_score = 0.0
        if 'cci' in indicators:
            cci = indicators['cci']
            if cci < -100:
                cci_score = 15 * min((abs(cci) - 100) / 100, 1.0)
            elif cci > 100:
                cci_score = -15 * min((cci - 100) / 100, 1.0)
        
        score += cci_score * 0.15
        
        stoch_rsi_score = 0.0
        if 'stoch_rsi_k' in indicators and 'stoch_rsi_d' in indicators:
            k = indicators['stoch_rsi_k']
            d = indicators['stoch_rsi_d']
            status = indicators.get('stoch_rsi_status', 'neutral')
            
            if status == 'oversold':
                if k > d:
                    stoch_rsi_score = 15
                else:
                    stoch_rsi_score = 8
            elif status == 'overbought':
                if k < d:
                    stoch_rsi_score = -15
                else:
                    stoch_rsi_score = -8
        
        score += stoch_rsi_score * 0.15
        
        return max(0, min(100, score))
    
    def _score_volume(self, indicators: Dict) -> float:
        """
        成交量分析评分 (0 到 100)
        
        考虑因素:
        - 价量配合
        - OBV趋势
        - Volume Profile
        - 成交量比率
        """
        score = 50.0
        
        price_volume_score = 0.0
        if 'price_volume_confirmation' in indicators:
            confirmation = indicators['price_volume_confirmation']
            price_change = indicators.get('price_change_pct', 0)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            
            if confirmation == 'bullish':
                if volume_ratio > 2.0:
                    price_volume_score = 40
                elif volume_ratio > 1.5:
                    price_volume_score = 35
                else:
                    price_volume_score = 25
            elif confirmation == 'bearish':
                if volume_ratio > 2.0 and price_change < -5:
                    price_volume_score = -30
                else:
                    price_volume_score = -40
            elif confirmation == 'divergence':
                if price_change > 0:
                    price_volume_score = -15
                else:
                    price_volume_score = 10
            else:
                if volume_ratio > 1.5:
                    price_volume_score = 10
                elif volume_ratio < 0.6:
                    price_volume_score = -10
        
        score += price_volume_score * 0.4
        
        obv_score = 0.0
        if 'obv_trend' in indicators:
            obv_trend = indicators['obv_trend']
            price_change = indicators.get('price_change_pct', 0)
            
            if obv_trend == 'up' and price_change > 0:
                obv_score = 30
            elif obv_trend == 'down' and price_change < 0:
                obv_score = -30
            elif obv_trend == 'up':
                obv_score = 15
            elif obv_trend == 'down':
                obv_score = -15
        
        score += obv_score * 0.3
        
        vp_score = 0.0
        if 'vp_status' in indicators:
            vp_status = indicators['vp_status']
            if vp_status == 'above_va':
                vp_score = 20
            elif vp_status == 'below_va':
                vp_score = -20
        
        score += vp_score * 0.2
        
        volume_ratio_score = 0.0
        if 'volume_ratio' in indicators:
            ratio = indicators['volume_ratio']
            price_change = indicators.get('price_change_pct', 0)
            
            if ratio > 1.5 and price_change > 0:
                volume_ratio_score = 10
            elif ratio > 1.5 and price_change < 0:
                volume_ratio_score = -10
        
        score += volume_ratio_score * 0.1
        
        return max(0, min(100, score))
    
    def _score_volatility(self, indicators: Dict) -> float:
        """
        波动性评分 (0 到 100)
        
        考虑因素:
        - 波动率水平
        - 布林带位置
        - ATR
        """
        score = 50.0
        
        bb_score = 0.0
        if all(k in indicators for k in ['bb_upper', 'bb_lower', 'bb_middle', 'current_price']):
            price = indicators['current_price']
            upper = indicators['bb_upper']
            lower = indicators['bb_lower']
            middle = indicators['bb_middle']
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            if upper > lower > 0:
                band_width = upper - lower
                position = (price - lower) / band_width if band_width > 0 else 0.5
                
                if position <= 0.1:
                    bb_score = 50 * (0.1 - position) / 0.1
                elif 0.1 < position <= 0.25:
                    bb_score = 35
                elif 0.25 < position <= 0.4:
                    bb_score = 25
                elif 0.4 < position <= 0.6:
                    if trend_direction == 'up':
                        bb_score = 15
                    elif price > middle:
                        bb_score = 10
                    else:
                        bb_score = 5
                elif 0.6 < position <= 0.75:
                    if trend_direction == 'up':
                        bb_score = 8
                    else:
                        bb_score = 0
                elif 0.75 < position <= 0.9:
                    bb_score = -10
                elif position > 0.9:
                    bb_score = -50 * (position - 0.9) / 0.1
        
        score += bb_score * 0.5
        
        volatility_score = 0.0
        if 'volatility_20' in indicators:
            vol = indicators['volatility_20']
            if 2.0 <= vol <= 3.0:
                volatility_score = 30
            elif 1.5 <= vol < 2.0 or 3.0 < vol <= 4.0:
                volatility_score = 15
            elif vol < 1.0:
                volatility_score = -20
            elif vol > 5.0:
                volatility_score = -40
            elif vol > 4.0:
                volatility_score = -25
        
        score += volatility_score * 0.3
        
        atr_score = 0.0
        if 'atr_percent' in indicators:
            atr_pct = indicators['atr_percent']
            if atr_pct < 1.5:
                atr_score = 20
            elif atr_pct > 5.0:
                atr_score = -30
        
        score += atr_score * 0.2
        
        return max(0, min(100, score))
    
    def _score_support_resistance(self, indicators: Dict) -> float:
        """
        支撑压力位评分 (0 到 100)
        
        考虑因素:
        - 距离支撑/压力位的距离
        - 突破关键位
        - SAR位置
        """
        score = 50.0
        current_price = indicators.get('current_price', 0)
        
        if current_price <= 0:
            return 50.0
        
        support_score = 0.0
        if 'support_20d_low' in indicators:
            support = indicators['support_20d_low']
            dist_pct = ((current_price - support) / current_price) * 100
            
            if dist_pct < -5:
                support_score = -40
            elif -5 <= dist_pct < -2:
                support_score = -25
            elif -2 <= dist_pct < 0:
                support_score = 20
            elif 0 <= dist_pct < 3:
                support_score = 40
            elif 3 <= dist_pct < 8:
                support_score = 25
            elif 8 <= dist_pct < 15:
                support_score = 10
            else:
                support_score = 0
        
        score += support_score * 0.4
        
        resistance_score = 0.0
        if 'resistance_20d_high' in indicators:
            resistance = indicators['resistance_20d_high']
            dist_pct = ((resistance - current_price) / current_price) * 100
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            if dist_pct < -3:
                resistance_score = 30
            elif -3 <= dist_pct < 0:
                resistance_score = 20
            elif 0 <= dist_pct < 2:
                if trend_direction == 'up':
                    resistance_score = -5
                else:
                    resistance_score = -20
            elif 2 <= dist_pct < 5:
                resistance_score = -10
            elif 5 <= dist_pct < 10:
                resistance_score = 10
            elif 10 <= dist_pct < 20:
                resistance_score = 20
            else:
                resistance_score = 15
        
        score += resistance_score * 0.3
        
        sar_score = 0.0
        if 'sar' in indicators and 'sar_signal' in indicators:
            sar = indicators['sar']
            sar_signal = indicators.get('sar_signal', 'hold')
            sar_trend = indicators.get('sar_trend', 'neutral')
            
            if sar > 0:
                if sar_signal == 'buy':
                    if sar_trend == 'up':
                        sar_score = 25
                    else:
                        sar_score = 30
                elif sar_signal == 'sell':
                    if sar_trend == 'down':
                        sar_score = -25
                    else:
                        sar_score = -30
        
        score += sar_score * 0.3
        
        return max(0, min(100, score))
    
    def _score_advanced(self, indicators: Dict) -> float:
        """
        高级指标评分 (0 到 100)
        
        考虑因素:
        - ML预测
        - 连续涨跌天数
        - 趋势强度
        - 威廉指标
        """
        score = 50.0
        
        ml_score = 0.0
        if 'ml_trend' in indicators:
            ml_trend = indicators['ml_trend']
            ml_confidence = indicators.get('ml_confidence', 0)
            ml_prediction = indicators.get('ml_prediction', 0)
            
            if ml_confidence > 70:
                if ml_trend == 'up':
                    ml_score = 20 * (ml_confidence / 100)
                elif ml_trend == 'down':
                    ml_score = -20 * (ml_confidence / 100)
            elif ml_confidence > 50:
                if ml_trend == 'up':
                    ml_score = 10 * (ml_confidence / 100)
                elif ml_trend == 'down':
                    ml_score = -10 * (ml_confidence / 100)
        
        score += ml_score * 0.2
        
        trend_strength_score = 0.0
        if 'trend_strength' in indicators and 'trend_direction' in indicators:
            strength = indicators['trend_strength']
            direction = indicators['trend_direction']
            
            if strength > 50:
                if direction == 'up':
                    trend_strength_score = 35 * (strength / 100)
                elif direction == 'down':
                    trend_strength_score = -35 * (strength / 100)
        
        score += trend_strength_score * 0.35
        
        consecutive_score = 0.0
        up_days = indicators.get('consecutive_up_days', 0)
        down_days = indicators.get('consecutive_down_days', 0)
        price_change = indicators.get('price_change_pct', 0)
        
        if down_days >= 7:
            consecutive_score = 25
        elif down_days >= 5:
            consecutive_score = 20
        elif down_days >= 3:
            consecutive_score = 12
        elif down_days == 0 and price_change > 0:
            prev_down = indicators.get('prev_consecutive_down_days', 0)
            if prev_down >= 3:
                consecutive_score = 18
        elif up_days >= 7:
            consecutive_score = -20
        elif up_days >= 5:
            consecutive_score = -10
        elif up_days >= 1 and up_days <= 4:
            if price_change > 0 and price_change < 5:
                consecutive_score = 8
            elif price_change >= 5:
                consecutive_score = 5
        
        score += consecutive_score * 0.25
        
        wr_score = 0.0
        if 'williams_r' in indicators:
            wr = indicators['williams_r']
            if wr < -80:
                wr_score = 10 * (abs(wr) - 80) / 20
            elif wr > -20:
                wr_score = -10 * (20 - abs(wr)) / 20
        
        score += wr_score * 0.1
        
        return max(0, min(100, score))
    
    def get_recommendation(self, score: int) -> Tuple[str, str]:
        """
        根据评分获取建议（百分制，0-100分）
        
        Args:
            score: 综合评分 (0 到 100)
            
        Returns:
            (建议文字, 操作标识)
        """
        if score >= 70:
            return '🟢 强烈买入', 'strong_buy'
        elif score >= 60:
            return '🟢 买入', 'buy'
        elif score >= 54:
            return '🟢 轻度买入', 'buy_light'
        elif score >= 46:
            return '⚪ 中性观望', 'hold'
        elif score >= 40:
            return '🔴 轻度卖出', 'sell_light'
        elif score >= 30:
            return '🔴 卖出', 'sell'
        else:
            return '🔴 强烈卖出', 'strong_sell'


# 评分系统已移除
# 以下函数和类保留以避免导入错误，但不再使用
_scoring_system = None  # 已废弃

def calculate_comprehensive_score(indicators: Dict) -> Tuple[int, Dict]:
    """已废弃：评分系统已移除"""
    return 50, {}

def get_recommendation(score: int) -> Tuple[str, str]:
    """已废弃：评分系统已移除"""
    return 'N/A', 'hold'


# === merged from signal_generators.py ===
# 信号生成器模块 - 提取重复的信号生成逻辑


def add_ma_signals(signals_list: List[str], indicators: Dict):
    """
    添加MA均线交叉信号
    
    Args:
        signals_list: 信号列表，用于添加信号字符串
        indicators: 技术指标字典，包含ma5、ma20等数据
    """
    if 'ma5' in indicators and 'ma20' in indicators:
        if indicators['ma5'] > indicators['ma20']:
            signals_list.append('📈 短期均线(MA5)在长期均线(MA20)之上 - 看涨')
        else:
            signals_list.append('📉 短期均线(MA5)在长期均线(MA20)之下 - 看跌')


def add_rsi_signals(signals_list: List[str], indicators: Dict):
    """
    添加RSI超买超卖信号
    
    Args:
        signals_list: 信号列表，用于添加信号字符串
        indicators: 技术指标字典，包含rsi数据
    """
    if 'rsi' in indicators:
        rsi = indicators['rsi']
        if rsi < 30:
            signals_list.append(f'🟢 RSI={rsi:.1f} 超卖区域 - 可能反弹')
        elif rsi > 70:
            signals_list.append(f'🔴 RSI={rsi:.1f} 超买区域 - 可能回调')
        else:
            signals_list.append(f'⚪ RSI={rsi:.1f} 中性区域')


def add_bollinger_signals(signals_list: List[str], indicators: Dict):
    """
    添加布林带信号
    
    Args:
        signals_list: 信号列表，用于添加信号字符串
        indicators: 技术指标字典，包含bb_upper、bb_lower、current_price等数据
    """
    if all(k in indicators for k in ['bb_upper', 'bb_lower', 'current_price']):
        price = indicators['current_price']
        upper = indicators['bb_upper']
        lower = indicators['bb_lower']
        
        if price <= lower:
            signals_list.append('🟢 价格触及布林带下轨 - 可能反弹')
        elif price >= upper:
            signals_list.append('🔴 价格触及布林带上轨 - 可能回调')


def add_macd_signals(signals_list: List[str], indicators: Dict):
    """
    添加MACD信号
    
    Args:
        signals_list: 信号列表，用于添加信号字符串
        indicators: 技术指标字典，包含macd_histogram数据
    """
    if 'macd_histogram' in indicators:
        histogram = indicators['macd_histogram']
        if histogram > 0:
            signals_list.append('📈 MACD柱状图为正 - 看涨')
        else:
            signals_list.append('📉 MACD柱状图为负 - 看跌')


def add_volume_signals(signals_list: List[str], indicators: Dict):
    """
    添加成交量相关信号
    
    Args:
        signals_list: 信号列表，用于添加信号字符串
        indicators: 技术指标字典，包含volume_ratio、price_volume_confirmation等数据
    """
    # 成交量比率
    if 'volume_ratio' in indicators:
        ratio = indicators['volume_ratio']
        if ratio > 1.5:
            signals_list.append(f'📊 成交量放大{ratio:.1f}倍 - 趋势加强')
        elif ratio < 0.5:
            signals_list.append(f'📊 成交量萎缩 - 趋势减弱')
    
    # 价量配合
    if 'price_volume_confirmation' in indicators:
        confirmation = indicators['price_volume_confirmation']
        if confirmation == 'bullish':
            signals_list.append('✅ 价涨量增 - 看涨确认，趋势健康')
        elif confirmation == 'bearish':
            signals_list.append('❌ 价跌量增 - 看跌确认，下跌动能强')
        elif confirmation == 'divergence':
            signals_list.append('⚠️ 价量背离 - 趋势可能反转，需谨慎')
    
    # 成交量信号
    if 'volume_signal' in indicators:
        vol_signal = indicators['volume_signal']
        if vol_signal == 'high_volume':
            vol_ratio = indicators.get('volume_ratio', 1.0)
            signals_list.append(f'🔥 高成交量信号 - 当前成交量是均量的{vol_ratio:.1f}倍')
        elif vol_signal == 'low_volume':
            signals_list.append('💤 低成交量信号 - 市场观望情绪浓厚')


def add_trend_signals(signals_list: List[str], indicators: Dict):
    """
    添加趋势相关信号
    
    Args:
        signals_list: 信号列表，用于添加信号字符串
        indicators: 技术指标字典，包含trend_direction、trend_strength等数据
    """
    if 'trend_direction' in indicators:
        direction = indicators['trend_direction']
        strength = indicators.get('trend_strength', 0)
        
        if direction == 'up':
            if strength > 70:
                signals_list.append(f'🚀 强劲上升趋势 - 趋势强度{strength:.0f}%')
            else:
                signals_list.append(f'📈 温和上升趋势 - 趋势强度{strength:.0f}%')
        elif direction == 'down':
            if strength > 70:
                signals_list.append(f'💥 强劲下降趋势 - 趋势强度{strength:.0f}%')
            else:
                signals_list.append(f'📉 温和下降趋势 - 趋势强度{strength:.0f}%')
        else:
            signals_list.append(f'🔄 震荡行情 - 趋势强度{strength:.0f}%')


def add_advanced_indicator_signals(signals_list: List[str], indicators: Dict):
    """
    添加高级技术指标信号（ADX、SAR、Ichimoku、SuperTrend、StochRSI等）
    
    Args:
        signals_list: 信号列表，用于添加信号字符串
        indicators: 技术指标字典，包含各种高级指标数据
    """
    # ADX趋势强度
    if 'adx' in indicators:
        adx = indicators['adx']
        if adx > 40:
            signals_list.append(f'💪 ADX={adx:.1f} - 强趋势，跟随趋势交易')
        elif adx > 25:
            signals_list.append(f'⚡ ADX={adx:.1f} - 中等趋势')
        elif adx > 20:
            signals_list.append(f'🌤️ ADX={adx:.1f} - 弱趋势')
        else:
            signals_list.append(f'🌫️ ADX={adx:.1f} - 无明显趋势，适合区间交易')
    
    # SAR抛物线
    if 'sar_signal' in indicators:
        sar_signal = indicators['sar_signal']
        sar_distance = indicators.get('sar_distance_pct', 0)
        if sar_signal == 'bullish':
            signals_list.append(f'🔵 SAR看涨 - 止损位距离{abs(sar_distance):.1f}%')
        elif sar_signal == 'bearish':
            signals_list.append(f'🔴 SAR看跌 - 止损位距离{abs(sar_distance):.1f}%')
    
    # Ichimoku一目均衡表
    if 'ichimoku_status' in indicators:
        status = indicators['ichimoku_status']
        if status == 'above_cloud':
            signals_list.append('☁️ 价格在云层上方 - 看涨')
        elif status == 'below_cloud':
            signals_list.append('☁️ 价格在云层下方 - 看跌')
        else:
            signals_list.append('☁️ 价格在云层内 - 盘整')
    
    # SuperTrend
    if 'supertrend_direction' in indicators:
        st_dir = indicators['supertrend_direction']
        if st_dir == 'up':
            signals_list.append('🟢 SuperTrend看涨信号')
        else:
            signals_list.append('🔴 SuperTrend看跌信号')
    
    # StochRSI
    if 'stoch_rsi_status' in indicators:
        status = indicators['stoch_rsi_status']
        if status == 'oversold':
            signals_list.append('🟢 StochRSI超卖 - 短期可能反弹')
        elif status == 'overbought':
            signals_list.append('🔴 StochRSI超买 - 短期可能回调')


def calculate_risk_level(indicators: Dict) -> Dict:
    """
    计算风险等级
    
    Args:
        indicators: 技术指标字典，包含volatility_20、volume_ratio、adx等数据
        
    Returns:
        包含level、description和score的字典
    """
    volatility = indicators.get('volatility_20', 2.0)
    volume_ratio = indicators.get('volume_ratio', 1.0)
    adx = indicators.get('adx', 0)
    
    risk_score = 0
    
    # 波动率贡献
    if volatility > 5:
        risk_score += 3
    elif volatility > 3:
        risk_score += 2
    elif volatility > 2:
        risk_score += 1
    
    # 成交量贡献
    if volume_ratio > 2.0:
        risk_score += 1
    elif volume_ratio < 0.5:
        risk_score += 1
    
    # 趋势强度贡献
    if adx < 20:
        risk_score += 1
    
    # 确定风险等级
    if risk_score >= 5:
        level = 'very_high'
        desc = '极高风险 - 建议谨慎或观望'
    elif risk_score >= 4:
        level = 'high'
        desc = '高风险 - 建议小仓位操作'
    elif risk_score >= 2:
        level = 'medium'
        desc = '中等风险 - 正常仓位'
    elif risk_score >= 1:
        level = 'low'
        desc = '低风险 - 可适当加仓'
    else:
        level = 'very_low'
        desc = '很低风险 - 相对稳健'
    
    return {
        'level': level,
        'description': desc,
        'score': risk_score
    }


def calculate_stop_loss_take_profit(indicators: Dict) -> tuple:
    """
    计算止损和止盈价位
    
    Args:
        indicators: 技术指标字典，包含current_price、atr、volatility_20等数据
        
    Returns:
        (stop_loss, take_profit) 元组，如果计算失败则返回(None, None)
    """
    current_price = indicators.get('current_price', 0)
    atr = indicators.get('atr', 0)
    volatility = indicators.get('volatility_20', 2.0)
    
    if current_price <= 0:
        return None, None
    
    # 使用ATR或波动率计算
    if atr > 0:
        stop_loss = current_price - (atr * 2)
        take_profit = current_price + (atr * 3)
    else:
        # 基于波动率的fallback计算
        risk_range = current_price * (volatility / 100) * 2
        stop_loss = current_price - risk_range
        take_profit = current_price + (risk_range * 1.5)
    
    # 考虑支撑位和压力位
    if 'pivot_s1' in indicators and indicators['pivot_s1'] > 0:
        stop_loss = max(stop_loss, indicators['pivot_s1'])
    
    if 'pivot_r1' in indicators and indicators['pivot_r1'] > 0:
        take_profit = min(take_profit, indicators['pivot_r1'])
    
    return stop_loss, take_profit

from datetime import datetime
class StockAnalyzer:
    """股票全面分析器"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.analysis_results = {}
    
    def analyze_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行全面分析
        """
        try:
            results = {
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat(),
                'valuation': self.analyze_valuation(data.get('fundamental', {})),
                'financial_health': self.analyze_financial_health(data.get('fundamental', {})),
                'growth': self.analyze_growth(data.get('fundamental', {})),
                'profitability': self.analyze_profitability(data.get('fundamental', {})),
                'dividend': self.analyze_dividend(data),
                'institutional': self.analyze_institutional(data),
                'insider': self.analyze_insider(data),
                'analyst': self.analyze_analyst(data),
                'earnings': self.analyze_earnings(data),
                'esg': self.analyze_esg(data.get('sustainability', {})),
                'risk': self.assess_risk(data),
                'overall_score': {}
            }
            
            # 计算综合评分
            results['overall_score'] = self.calculate_overall_score(results)
            
            # 生成投资建议
            results['recommendation'] = self.generate_recommendation(results)
            
            logger.info(f"完成全面分析: {self.symbol}")
            return results
            
        except Exception as e:
            logger.error(f"全面分析失败: {self.symbol}, 错误: {e}")
            return None
    
    def analyze_valuation(self, fundamental: Dict) -> Dict[str, Any]:
        """
        估值分析：评估股票是否被高估或低估
        """
        try:
            pe = fundamental.get('PE', 0)
            forward_pe = fundamental.get('ForwardPE', 0)
            pb = fundamental.get('PriceToBook', 0)
            ps = fundamental.get('PriceToSales', 0)
            peg = fundamental.get('PEGRatio', 0)
            ev_revenue = fundamental.get('EVToRevenue', 0)
            ev_ebitda = fundamental.get('EVToEBITDA', 0)
            
            valuation_score = 0
            signals = []
            
            # PE分析
            if pe > 0:
                if pe < 15:
                    signals.append('✅ 市盈率偏低，可能被低估')
                    valuation_score += 2
                elif pe < 25:
                    signals.append('⚪ 市盈率适中')
                    valuation_score += 1
                elif pe < 40:
                    signals.append('⚠️ 市盈率偏高，需关注')
                else:
                    signals.append('❌ 市盈率过高，可能被高估')
            
            # PEG分析
            if peg > 0:
                if peg < 1:
                    signals.append('✅ PEG<1，价值相对合理')
                    valuation_score += 2
                elif peg < 2:
                    signals.append('⚪ PEG适中')
                    valuation_score += 1
                else:
                    signals.append('⚠️ PEG>2，估值偏高')
            
            # PB分析
            if pb > 0:
                if pb < 1:
                    signals.append('✅ 市净率<1，可能被低估')
                    valuation_score += 2
                elif pb < 3:
                    signals.append('⚪ 市净率正常')
                    valuation_score += 1
                else:
                    signals.append('⚠️ 市净率偏高')
            
            # 评估等级
            if valuation_score >= 5:
                rating = '优秀'
                level = 'excellent'
            elif valuation_score >= 3:
                rating = '良好'
                level = 'good'
            elif valuation_score >= 1:
                rating = '一般'
                level = 'fair'
            else:
                rating = '偏贵'
                level = 'expensive'
            
            return {
                'rating': rating,
                'level': level,
                'score': valuation_score,
                'metrics': {
                    'PE': pe,
                    'Forward_PE': forward_pe,
                    'PB': pb,
                    'PS': ps,
                    'PEG': peg,
                    'EV_Revenue': ev_revenue,
                    'EV_EBITDA': ev_ebitda
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"估值分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_financial_health(self, fundamental: Dict) -> Dict[str, Any]:
        """
        财务健康度分析：评估公司财务状况
        """
        try:
            current_ratio = fundamental.get('CurrentRatio', 0)
            quick_ratio = fundamental.get('QuickRatio', 0)
            debt_equity = fundamental.get('DebtToEquity', 0)
            total_debt = fundamental.get('TotalDebt', 0)
            total_cash = fundamental.get('TotalCash', 0)
            cash_flow = fundamental.get('CashFlow', 0)
            
            health_score = 0
            signals = []
            
            # 流动比率分析
            if current_ratio > 0:
                if current_ratio >= 2:
                    signals.append('✅ 流动比率优秀，短期偿债能力强')
                    health_score += 2
                elif current_ratio >= 1.5:
                    signals.append('⚪ 流动比率良好')
                    health_score += 1
                elif current_ratio >= 1:
                    signals.append('⚠️ 流动比率偏低')
                else:
                    signals.append('❌ 流动比率过低，短期偿债风险')
            
            # 速动比率分析
            if quick_ratio > 0:
                if quick_ratio >= 1:
                    signals.append('✅ 速动比率健康')
                    health_score += 1
                else:
                    signals.append('⚠️ 速动比率偏低')
            
            # 债务权益比分析
            if debt_equity >= 0:
                if debt_equity < 0.5:
                    signals.append('✅ 低杠杆，财务稳健')
                    health_score += 2
                elif debt_equity < 1:
                    signals.append('⚪ 债务水平适中')
                    health_score += 1
                elif debt_equity < 2:
                    signals.append('⚠️ 杠杆偏高')
                else:
                    signals.append('❌ 高杠杆，财务风险大')
            
            # 现金流分析
            if cash_flow > 0:
                signals.append('✅ 经营现金流为正')
                health_score += 2
            elif cash_flow < 0:
                signals.append('❌ 经营现金流为负，需关注')
            
            # 现金储备分析
            if total_cash > total_debt > 0:
                signals.append('✅ 现金储备充足，超过总债务')
                health_score += 1
            
            # 健康等级
            if health_score >= 7:
                rating = '优秀'
                level = 'excellent'
            elif health_score >= 5:
                rating = '良好'
                level = 'good'
            elif health_score >= 3:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': health_score,
                'metrics': {
                    'current_ratio': current_ratio,
                    'quick_ratio': quick_ratio,
                    'debt_to_equity': debt_equity,
                    'total_debt': total_debt,
                    'total_cash': total_cash,
                    'cash_flow': cash_flow
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"财务健康度分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_growth(self, fundamental: Dict) -> Dict[str, Any]:
        """
        成长性分析：评估公司增长潜力
        """
        try:
            revenue_growth = fundamental.get('RevenueGrowth', 0) * 100
            earnings_growth = fundamental.get('EarningsGrowth', 0) * 100
            quarterly_revenue_growth = fundamental.get('QuarterlyRevenueGrowth', 0) * 100
            earnings_quarterly_growth = fundamental.get('EarningsQuarterlyGrowth', 0) * 100
            
            growth_score = 0
            signals = []
            
            # 营收增长分析
            if revenue_growth > 20:
                signals.append('🚀 营收高增长，增速超过20%')
                growth_score += 3
            elif revenue_growth > 10:
                signals.append('📈 营收稳健增长')
                growth_score += 2
            elif revenue_growth > 0:
                signals.append('⚪ 营收正增长')
                growth_score += 1
            else:
                signals.append('📉 营收负增长，需关注')
            
            # 盈利增长分析
            if earnings_growth > 20:
                signals.append('🚀 盈利高增长')
                growth_score += 3
            elif earnings_growth > 10:
                signals.append('📈 盈利稳健增长')
                growth_score += 2
            elif earnings_growth > 0:
                signals.append('⚪ 盈利正增长')
                growth_score += 1
            else:
                signals.append('📉 盈利负增长')
            
            # 季度增长分析
            if quarterly_revenue_growth > 15:
                signals.append('✅ 季度营收增长强劲')
                growth_score += 1
            
            # 成长等级
            if growth_score >= 6:
                rating = '高成长'
                level = 'high'
            elif growth_score >= 4:
                rating = '稳健增长'
                level = 'moderate'
            elif growth_score >= 2:
                rating = '低速增长'
                level = 'low'
            else:
                rating = '增长乏力'
                level = 'negative'
            
            return {
                'rating': rating,
                'level': level,
                'score': growth_score,
                'metrics': {
                    'revenue_growth': revenue_growth,
                    'earnings_growth': earnings_growth,
                    'quarterly_revenue_growth': quarterly_revenue_growth,
                    'earnings_quarterly_growth': earnings_quarterly_growth
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"成长性分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_profitability(self, fundamental: Dict) -> Dict[str, Any]:
        """
        盈利能力分析：评估公司赚钱能力
        """
        try:
            profit_margin = fundamental.get('ProfitMargin', 0) * 100
            operating_margin = fundamental.get('OperatingMargin', 0) * 100
            gross_margin = fundamental.get('GrossMargin', 0) * 100
            roe = fundamental.get('ROE', 0) * 100
            roa = fundamental.get('ROA', 0) * 100
            roic = fundamental.get('ROIC', 0) * 100
            
            profit_score = 0
            signals = []
            
            # 净利润率分析
            if profit_margin > 20:
                signals.append('✅ 净利润率优秀，盈利能力强')
                profit_score += 3
            elif profit_margin > 10:
                signals.append('⚪ 净利润率良好')
                profit_score += 2
            elif profit_margin > 5:
                signals.append('⚠️ 净利润率一般')
                profit_score += 1
            else:
                signals.append('❌ 净利润率偏低')
            
            # ROE分析
            if roe > 20:
                signals.append('✅ ROE优秀，股东回报高')
                profit_score += 3
            elif roe > 15:
                signals.append('⚪ ROE良好')
                profit_score += 2
            elif roe > 10:
                signals.append('⚠️ ROE一般')
                profit_score += 1
            else:
                signals.append('❌ ROE偏低')
            
            # 毛利率分析
            if gross_margin > 50:
                signals.append('✅ 毛利率优秀，定价能力强')
                profit_score += 2
            elif gross_margin > 30:
                signals.append('⚪ 毛利率健康')
                profit_score += 1
            
            # 盈利能力等级
            if profit_score >= 7:
                rating = '卓越'
                level = 'excellent'
            elif profit_score >= 5:
                rating = '优秀'
                level = 'good'
            elif profit_score >= 3:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': profit_score,
                'metrics': {
                    'profit_margin': profit_margin,
                    'operating_margin': operating_margin,
                    'gross_margin': gross_margin,
                    'roe': roe,
                    'roa': roa,
                    'roic': roic
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"盈利能力分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_dividend(self, data: Dict) -> Dict[str, Any]:
        """
        股息分析：评估股息稳定性和收益率
        """
        try:
            fundamental = data.get('fundamental', {})
            dividends = data.get('dividends', [])
            
            dividend_yield = fundamental.get('DividendYield', 0) * 100
            payout_ratio = fundamental.get('PayoutRatio', 0) * 100
            dividend_rate = fundamental.get('DividendRate', 0)
            
            div_score = 0
            signals = []
            
            if not dividends or len(dividends) == 0:
                return {
                    'rating': '无股息',
                    'level': 'none',
                    'score': 0,
                    'metrics': {},
                    'signals': ['⚪ 该股票不分红']
                }
            
            # 股息率分析
            if dividend_yield > 4:
                signals.append('✅ 高股息率，超过4%')
                div_score += 3
            elif dividend_yield > 2:
                signals.append('⚪ 适中股息率')
                div_score += 2
            elif dividend_yield > 0:
                signals.append('⚠️ 低股息率')
                div_score += 1
            
            # 派息率分析
            if 0 < payout_ratio < 60:
                signals.append('✅ 派息率健康，可持续')
                div_score += 2
            elif payout_ratio >= 60 and payout_ratio < 80:
                signals.append('⚠️ 派息率偏高')
                div_score += 1
            elif payout_ratio >= 80:
                signals.append('❌ 派息率过高，可持续性存疑')
            
            # 分红历史稳定性
            if len(dividends) >= 5:
                recent_divs = [d['dividend'] for d in dividends[-5:]]
                if all(d > 0 for d in recent_divs):
                    # 检查是否持续增长
                    if all(recent_divs[i] <= recent_divs[i+1] for i in range(len(recent_divs)-1)):
                        signals.append('✅ 连续增长的股息，高度稳定')
                        div_score += 3
                    else:
                        signals.append('⚪ 持续分红，较为稳定')
                        div_score += 2
            
            # 评级
            if div_score >= 7:
                rating = '优秀'
                level = 'excellent'
            elif div_score >= 5:
                rating = '良好'
                level = 'good'
            elif div_score >= 3:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': div_score,
                'metrics': {
                    'dividend_yield': dividend_yield,
                    'payout_ratio': payout_ratio,
                    'dividend_rate': dividend_rate,
                    'dividend_history_years': len(dividends)
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"股息分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_institutional(self, data: Dict) -> Dict[str, Any]:
        """
        机构持仓分析：评估机构投资者行为
        """
        try:
            inst_holders = data.get('institutional_holders', [])
            mutual_holders = data.get('mutualfund_holders', [])
            major_holders = data.get('major_holders', {})
            
            inst_score = 0
            signals = []
            
            if not inst_holders:
                signals.append('⚪ 暂无机构持仓数据')
                return {
                    'rating': '未知',
                    'level': 'unknown',
                    'score': 0,
                    'metrics': {},
                    'signals': signals
                }
            
            # 机构持仓数量分析
            num_institutions = len(inst_holders)
            if num_institutions > 500:
                signals.append('✅ 机构投资者众多，认可度高')
                inst_score += 3
            elif num_institutions > 200:
                signals.append('⚪ 机构投资者较多')
                inst_score += 2
            elif num_institutions > 50:
                signals.append('⚠️ 机构投资者较少')
                inst_score += 1
            
            # 计算机构持股比例
            try:
                shares_held = sum(h.get('Shares', 0) for h in inst_holders if 'Shares' in h)
                if shares_held > 0:
                    signals.append(f'📊 机构持股数量: {shares_held:,.0f}')
            except Exception:
                pass
            
            # 共同基金分析
            if mutual_holders and len(mutual_holders) > 100:
                signals.append('✅ 被大量共同基金持有')
                inst_score += 2
            elif mutual_holders and len(mutual_holders) > 50:
                signals.append('⚪ 有一定共同基金持有')
                inst_score += 1
            
            # 评级
            if inst_score >= 6:
                rating = '优秀'
                level = 'excellent'
            elif inst_score >= 4:
                rating = '良好'
                level = 'good'
            elif inst_score >= 2:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较少'
                level = 'low'
            
            return {
                'rating': rating,
                'level': level,
                'score': inst_score,
                'metrics': {
                    'num_institutions': num_institutions,
                    'num_mutualfunds': len(mutual_holders) if mutual_holders else 0
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"机构持仓分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_insider(self, data: Dict) -> Dict[str, Any]:
        """
        内部交易分析：评估内部人员买卖行为
        """
        try:
            insider_trans = data.get('insider_transactions', [])
            insider_purchases = data.get('insider_purchases', [])
            
            insider_score = 0
            signals = []
            
            if not insider_trans:
                signals.append('⚪ 暂无内部交易数据')
                return {
                    'rating': '未知',
                    'level': 'unknown',
                    'score': 0,
                    'metrics': {},
                    'signals': signals
                }
            
            # 分析最近的内部交易
            recent_buys = 0
            recent_sells = 0
            
            for trans in insider_trans[:20]:  # 分析最近20笔
                trans_type = trans.get('Transaction', '').lower()
                if 'purchase' in trans_type or 'buy' in trans_type:
                    recent_buys += 1
                elif 'sale' in trans_type or 'sell' in trans_type:
                    recent_sells += 1
            
            # 买卖比例分析
            if recent_buys > recent_sells * 2:
                signals.append('✅ 内部人员大量买入，信心强')
                insider_score += 3
            elif recent_buys > recent_sells:
                signals.append('⚪ 内部人员净买入')
                insider_score += 2
            elif recent_sells > recent_buys * 2:
                signals.append('❌ 内部人员大量卖出，需警惕')
            elif recent_sells > recent_buys:
                signals.append('⚠️ 内部人员净卖出')
                insider_score += 1
            else:
                signals.append('⚪ 内部交易平衡')
                insider_score += 1
            
            # 内部购买分析
            if insider_purchases and len(insider_purchases) > 5:
                signals.append('✅ 近期有多笔内部购买')
                insider_score += 2
            
            # 评级
            if insider_score >= 5:
                rating = '积极'
                level = 'positive'
            elif insider_score >= 3:
                rating = '中性'
                level = 'neutral'
            else:
                rating = '消极'
                level = 'negative'
            
            return {
                'rating': rating,
                'level': level,
                'score': insider_score,
                'metrics': {
                    'recent_buys': recent_buys,
                    'recent_sells': recent_sells,
                    'total_transactions': len(insider_trans)
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"内部交易分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_analyst(self, data: Dict) -> Dict[str, Any]:
        """
        分析师意见分析：评估分析师评级和目标价
        """
        try:
            fundamental = data.get('fundamental', {})
            recommendations = data.get('recommendations', [])
            upgrades = data.get('upgrades_downgrades', [])
            
            target_mean = fundamental.get('TargetPrice', 0)
            target_high = fundamental.get('TargetHighPrice', 0)
            target_low = fundamental.get('TargetLowPrice', 0)
            current_price = fundamental.get('Price', 0)
            num_analysts = fundamental.get('NumberOfAnalystOpinions', 0)
            recommendation_key = fundamental.get('RecommendationKey', '')
            
            analyst_score = 0
            signals = []
            
            # 分析师数量分析
            if num_analysts > 20:
                signals.append('✅ 大量分析师覆盖')
                analyst_score += 1
            elif num_analysts > 10:
                signals.append('⚪ 适量分析师覆盖')
            
            # 目标价分析
            if target_mean > 0 and current_price > 0:
                upside_pct = ((target_mean - current_price) / current_price) * 100
                if upside_pct > 20:
                    signals.append(f'🚀 目标价上涨空间大: {upside_pct:.1f}%')
                    analyst_score += 3
                elif upside_pct > 10:
                    signals.append(f'📈 目标价有上涨空间: {upside_pct:.1f}%')
                    analyst_score += 2
                elif upside_pct > 0:
                    signals.append(f'⚪ 目标价略高于当前: {upside_pct:.1f}%')
                    analyst_score += 1
                else:
                    signals.append(f'📉 目标价低于当前: {upside_pct:.1f}%')
            
            # 推荐评级分析
            if recommendation_key:
                if recommendation_key in ['strong_buy', 'buy']:
                    signals.append('✅ 分析师推荐买入')
                    analyst_score += 2
                elif recommendation_key == 'hold':
                    signals.append('⚪ 分析师推荐持有')
                    analyst_score += 1
                elif recommendation_key in ['sell', 'strong_sell']:
                    signals.append('❌ 分析师推荐卖出')
            
            # 近期评级变化
            if upgrades:
                recent_upgrades = [u for u in upgrades[:10] if 'upgrade' in str(u.get('ToGrade', '')).lower()]
                recent_downgrades = [d for d in upgrades[:10] if 'downgrade' in str(d.get('ToGrade', '')).lower()]
                
                if len(recent_upgrades) > len(recent_downgrades):
                    signals.append('✅ 近期评级上调较多')
                    analyst_score += 2
                elif len(recent_downgrades) > len(recent_upgrades):
                    signals.append('⚠️ 近期评级下调较多')
            
            # 评级
            if analyst_score >= 7:
                rating = '强烈看好'
                level = 'strong_buy'
            elif analyst_score >= 5:
                rating = '看好'
                level = 'buy'
            elif analyst_score >= 3:
                rating = '中性'
                level = 'hold'
            else:
                rating = '谨慎'
                level = 'cautious'
            
            return {
                'rating': rating,
                'level': level,
                'score': analyst_score,
                'metrics': {
                    'target_mean': target_mean,
                    'target_high': target_high,
                    'target_low': target_low,
                    'current_price': current_price,
                    'num_analysts': num_analysts,
                    'recommendation': recommendation_key
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"分析师意见分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_earnings(self, data: Dict) -> Dict[str, Any]:
        """
        收益质量分析：评估盈利的稳定性和质量
        """
        try:
            earnings = data.get('earnings', {})
            earnings_history = data.get('earnings_history', [])
            
            earnings_score = 0
            signals = []
            
            if not earnings_history:
                signals.append('⚪ 暂无收益历史数据')
                return {
                    'rating': '未知',
                    'level': 'unknown',
                    'score': 0,
                    'metrics': {},
                    'signals': signals
                }
            
            # 分析实际vs预期
            beat_count = 0
            miss_count = 0
            
            for earning in earnings_history[:8]:  # 分析最近8个季度
                eps_actual = earning.get('epsActual', 0)
                eps_estimate = earning.get('epsEstimate', 0)
                
                if eps_actual and eps_estimate:
                    if eps_actual > eps_estimate:
                        beat_count += 1
                    elif eps_actual < eps_estimate:
                        miss_count += 1
            
            # 超预期比例分析
            if beat_count > 0 or miss_count > 0:
                beat_rate = beat_count / (beat_count + miss_count) * 100
                if beat_rate >= 75:
                    signals.append(f'✅ 经常超预期，超预期率{beat_rate:.0f}%')
                    earnings_score += 3
                elif beat_rate >= 50:
                    signals.append(f'⚪ 超预期表现一般，超预期率{beat_rate:.0f}%')
                    earnings_score += 2
                else:
                    signals.append(f'⚠️ 经常不及预期，超预期率{beat_rate:.0f}%')
                    earnings_score += 1
            
            # 季度收益稳定性
            quarterly_earnings = earnings.get('quarterly', [])
            if quarterly_earnings and len(quarterly_earnings) >= 4:
                recent_earnings = [q.get('Earnings', 0) for q in quarterly_earnings[:4]]
                if all(e > 0 for e in recent_earnings):
                    signals.append('✅ 持续盈利，收益稳定')
                    earnings_score += 2
                    
                    # 检查增长趋势
                    if all(recent_earnings[i] <= recent_earnings[i+1] for i in range(len(recent_earnings)-1)):
                        signals.append('✅ 收益持续增长')
                        earnings_score += 1
            
            # 评级
            if earnings_score >= 5:
                rating = '优秀'
                level = 'excellent'
            elif earnings_score >= 3:
                rating = '良好'
                level = 'good'
            elif earnings_score >= 1:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': earnings_score,
                'metrics': {
                    'beat_count': beat_count,
                    'miss_count': miss_count,
                    'total_reports': len(earnings_history)
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"收益质量分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_esg(self, sustainability: Dict) -> Dict[str, Any]:
        """
        ESG分析：评估环境、社会和治理表现
        """
        try:
            if not sustainability:
                return {
                    'rating': '无数据',
                    'level': 'no_data',
                    'score': 0,
                    'metrics': {},
                    'signals': ['⚪ 暂无ESG数据']
                }
            
            total_esg = sustainability.get('totalEsg', 0)
            environment = sustainability.get('environmentScore', 0)
            social = sustainability.get('socialScore', 0)
            governance = sustainability.get('governanceScore', 0)
            
            signals = []
            
            # ESG总分分析（分数越低越好）
            if total_esg > 0:
                if total_esg < 20:
                    signals.append('✅ ESG评分优秀，可持续性强')
                    rating = '优秀'
                    level = 'excellent'
                elif total_esg < 30:
                    signals.append('⚪ ESG评分良好')
                    rating = '良好'
                    level = 'good'
                elif total_esg < 40:
                    signals.append('⚠️ ESG评分一般')
                    rating = '一般'
                    level = 'fair'
                else:
                    signals.append('❌ ESG评分较差')
                    rating = '较差'
                    level = 'poor'
            else:
                rating = '未评级'
                level = 'unrated'
            
            return {
                'rating': rating,
                'level': level,
                'metrics': {
                    'total_esg': total_esg,
                    'environment': environment,
                    'social': social,
                    'governance': governance
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"ESG分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def assess_risk(self, data: Dict) -> Dict[str, Any]:
        """
        风险评估：综合评估投资风险
        """
        try:
            fundamental = data.get('fundamental', {})
            
            beta = fundamental.get('Beta', 1.0)
            debt_equity = fundamental.get('DebtToEquity', 0)
            current_ratio = fundamental.get('CurrentRatio', 0)
            
            risk_score = 0
            risk_factors = []
            
            # Beta风险
            if beta > 1.5:
                risk_factors.append('⚠️ 高Beta，波动性大')
                risk_score += 2
            elif beta > 1.2:
                risk_factors.append('⚠️ Beta偏高')
                risk_score += 1
            elif beta < 0.8:
                risk_factors.append('✅ 低Beta，相对稳定')
            
            # 债务风险
            if debt_equity > 2:
                risk_factors.append('⚠️ 高杠杆风险')
                risk_score += 3
            elif debt_equity > 1:
                risk_factors.append('⚠️ 杠杆偏高')
                risk_score += 2
            elif debt_equity < 0.5:
                risk_factors.append('✅ 低杠杆，财务稳健')
            
            # 流动性风险
            if 0 < current_ratio < 1:
                risk_factors.append('⚠️ 流动性风险')
                risk_score += 2
            elif current_ratio < 1.5:
                risk_factors.append('⚠️ 流动性偏弱')
                risk_score += 1
            
            # 风险等级
            if risk_score >= 6:
                level = '高风险'
                rating = 'high'
            elif risk_score >= 4:
                level = '中高风险'
                rating = 'medium_high'
            elif risk_score >= 2:
                level = '中等风险'
                rating = 'medium'
            else:
                level = '低风险'
                rating = 'low'
            
            return {
                'level': level,
                'rating': rating,
                'score': risk_score,
                'factors': risk_factors,
                'metrics': {
                    'beta': beta,
                    'debt_to_equity': debt_equity,
                    'current_ratio': current_ratio
                }
            }
            
        except Exception as e:
            logger.error(f"风险评估失败: {e}")
            return {'level': '未知', 'rating': 'unknown', 'factors': []}
    
    def calculate_overall_score(self, results: Dict) -> Dict[str, Any]:
        """
        计算综合评分（0-100分）
        """
        try:
            # 权重分配
            weights = {
                'valuation': 0.20,      # 估值 20%
                'financial_health': 0.15, # 财务健康 15%
                'growth': 0.15,         # 成长性 15%
                'profitability': 0.15,  # 盈利能力 15%
                'analyst': 0.10,        # 分析师意见 10%
                'earnings': 0.10,       # 收益质量 10%
                'institutional': 0.05,  # 机构持仓 5%
                'insider': 0.05,        # 内部交易 5%
                'dividend': 0.05        # 股息 5%
            }
            
            total_score = 0
            max_scores = {
                'valuation': 6,
                'financial_health': 9,
                'growth': 9,
                'profitability': 8,
                'analyst': 8,
                'earnings': 6,
                'institutional': 8,
                'insider': 5,
                'dividend': 8
            }
            
            breakdown = {}
            
            for key, weight in weights.items():
                if key in results and 'score' in results[key]:
                    score = results[key]['score']
                    max_score = max_scores[key]
                    normalized = (score / max_score * 100) if max_score > 0 else 0
                    weighted = normalized * weight
                    total_score += weighted
                    breakdown[key] = {
                        'raw_score': score,
                        'normalized': round(normalized, 2),
                        'weighted': round(weighted, 2)
                    }
            
            # 综合评级
            if total_score >= 80:
                grade = 'A'
                rating = '优秀'
            elif total_score >= 70:
                grade = 'B+'
                rating = '良好'
            elif total_score >= 60:
                grade = 'B'
                rating = '中等偏上'
            elif total_score >= 50:
                grade = 'C+'
                rating = '中等'
            elif total_score >= 40:
                grade = 'C'
                rating = '中等偏下'
            else:
                grade = 'D'
                rating = '较差'
            
            return {
                'total_score': round(total_score, 2),
                'grade': grade,
                'rating': rating,
                'breakdown': breakdown
            }
            
        except Exception as e:
            logger.error(f"计算综合评分失败: {e}")
            return {'total_score': 0, 'grade': 'N/A', 'rating': '未知'}
    
    def generate_recommendation(self, results: Dict) -> Dict[str, Any]:
        """
        生成投资建议
        """
        try:
            overall = results.get('overall_score', {})
            score = overall.get('total_score', 0)
            risk = results.get('risk', {})
            valuation = results.get('valuation', {})
            growth = results.get('growth', {})
            
            # 基于综合评分的建议
            if score >= 75:
                action = '强烈推荐买入'
                action_code = 'strong_buy'
                reason = '综合表现优秀，各项指标表现良好'
            elif score >= 65:
                action = '推荐买入'
                action_code = 'buy'
                reason = '综合表现良好，具有投资价值'
            elif score >= 55:
                action = '谨慎买入'
                action_code = 'cautious_buy'
                reason = '综合表现中等偏上，可适量配置'
            elif score >= 45:
                action = '持有观望'
                action_code = 'hold'
                reason = '综合表现一般，建议持有观望'
            else:
                action = '谨慎持有或减仓'
                action_code = 'cautious_hold'
                reason = '综合表现偏弱，建议谨慎'
            
            # 添加风险提示
            risk_level = risk.get('rating', 'medium')
            if risk_level in ['high', 'medium_high']:
                reason += '，但需注意较高风险'
            
            # 投资要点
            key_points = []
            
            # 估值要点
            if valuation.get('level') == 'excellent':
                key_points.append('估值处于合理偏低水平')
            elif valuation.get('level') == 'expensive':
                key_points.append('当前估值偏高，需谨慎')
            
            # 成长要点
            if growth.get('level') == 'high':
                key_points.append('公司保持高速增长')
            elif growth.get('level') == 'negative':
                key_points.append('增长动力不足')
            
            # 机构持仓要点
            inst_level = results.get('institutional', {}).get('level')
            if inst_level == 'excellent':
                key_points.append('机构投资者高度认可')
            
            return {
                'action': action,
                'action_code': action_code,
                'reason': reason,
                'key_points': key_points,
                'confidence': 'high' if score >= 70 or score <= 40 else 'medium'
            }
            
        except Exception as e:
            logger.error(f"生成投资建议失败: {e}")
            return {
                'action': '数据不足，建议进一步研究',
                'action_code': 'research',
                'reason': '无法给出明确建议'
            }


def create_comprehensive_analysis(symbol: str, all_data: Dict) -> Optional[Dict[str, Any]]:
    """
    创建全面的股票分析报告
    """
    try:
        analyzer = StockAnalyzer(symbol)
        analysis = analyzer.analyze_all(all_data)
        
        if not analysis:
            return None
        
        # 添加基础信息
        fundamental = all_data.get('fundamental', {})
        analysis['basic_info'] = {
            'symbol': symbol,
            'name': fundamental.get('CompanyName', ''),
            'sector': fundamental.get('Sector', ''),
            'industry': fundamental.get('Industry', ''),
            'current_price': fundamental.get('Price', 0),
            'market_cap': fundamental.get('MarketCap', 0),
            'currency': fundamental.get('Currency', 'USD')
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"创建全面分析失败: {symbol}, 错误: {e}")
        return None
