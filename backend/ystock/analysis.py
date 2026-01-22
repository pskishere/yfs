#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析模块 - 技术指标计算、交易信号生成
"""

import numpy as np
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

logger = logging.getLogger(__name__)


def calculate_technical_indicators(symbol: str, duration: str = '1 M', bar_size: str = '1 day', hist_data: List[Dict] = None):
    """
    计算技术指标（基于历史数据）
    返回：移动平均线、RSI、MACD等
    如果证券不存在，返回(None, error_info)
    """
    if hist_data is None:
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

    logger.info(f"calculate_technical_indicators called for {symbol}. Data points: {len(closes)}")

    if len(closes) >= 30:
        # 获取时间戳信息用于周期分析
        # 从hist_data中获取date字段，如果没有则从formatted_candles中获取time字段
        timestamps = []
        if hist_data:
            for bar in hist_data:
                # 确保获取到日期字符串
                date_val = bar.get('date') or bar.get('time', '')
                date_str = str(date_val) if date_val is not None else ''
                
                if date_str:
                    try:
                        # 尝试转换日期格式
                        if len(date_str) == 8 and date_str.isdigit():
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
        
        logger.info(f"Cycle analysis prep: closes={len(closes)}, timestamps={len(timestamps)}")
        if timestamps and len(timestamps) > 0:
            logger.info(f"First timestamp: {timestamps[0]}, Last timestamp: {timestamps[-1]}")
        
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
