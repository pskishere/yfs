#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析模块 - 技术指标计算、交易信号生成
"""

import numpy as np
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from .yfinance import get_historical_data, sanitize_data

from .indicators import (
    calculate_ma, calculate_rsi, calculate_bollinger, calculate_macd,
    calculate_volume, calculate_price_change, calculate_volatility,
    calculate_support_resistance, calculate_kdj, calculate_atr,
    calculate_williams_r, calculate_obv, analyze_trend_strength,
    calculate_fibonacci_retracement, get_trend,
    calculate_cci, calculate_adx, calculate_sar,
    calculate_supertrend, calculate_stoch_rsi, calculate_volume_profile,
    calculate_ichimoku, calculate_cycle_analysis, analyze_yearly_cycles, analyze_monthly_cycles,
    calculate_vwap, calculate_pivot_points
)

logger = logging.getLogger(__name__)


def _extract_timestamps(hist_data: List[Dict]) -> List[Optional[str]]:
    """
    [内部函数] 从历史数据中提取并格式化时间戳
    """
    timestamps = []
    for bar in hist_data:
        # 优先使用 date，其次使用 time
        date_val = bar.get('date') or bar.get('time', '')
        date_str = str(date_val) if date_val is not None else ''
        
        if not date_str:
            timestamps.append(None)
            continue
            
        try:
            # 1. 处理 yyyymmdd 格式
            if len(date_str) == 8 and date_str.isdigit():
                dt = datetime.strptime(date_str, '%Y%m%d')
                timestamps.append(dt.strftime('%Y-%m-%d'))
            # 2. 处理 yyyymmdd HH:MM:SS 格式
            elif ' ' in date_str and ':' in date_str:
                dt = datetime.strptime(date_str, '%Y%m%d %H:%M:%S')
                timestamps.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
            # 3. 其他格式直接透传（如 ISO 格式）
            else:
                timestamps.append(date_str)
        except Exception:
            timestamps.append(date_str)
            
    return timestamps


def calculate_technical_indicators(symbol: str, duration: str = '1 M', bar_size: str = '1 day', hist_data: List[Dict] = None):
    """
    计算技术指标（基于历史数据）
    返回：移动平均线、RSI、MACD、周期分析等
    
    Args:
        symbol: 股票代码
        duration: 数据范围
        bar_size: K线周期
        hist_data: 已获取的历史数据列表。如果为 None，则会尝试实时获取。
        
    Returns:
        (结果字典, 错误信息字典/None)
    """
    # 1. 确保有历史数据
    if hist_data is None:
        hist_data, error = get_historical_data(symbol, duration, bar_size)
        if error:
            return None, error
    
    if not hist_data or len(hist_data) == 0:
        return None, {"code": "NO_DATA", "message": f"无法获取历史数据: {symbol}"}
    
    # 2. 准备基础数据数组
    closes = np.array([bar['close'] for bar in hist_data])
    highs = np.array([bar['high'] for bar in hist_data])
    lows = np.array([bar['low'] for bar in hist_data])
    volumes = np.array([bar['volume'] for bar in hist_data])
    
    data_len = len(closes)
    if data_len < 20:
        logger.warning(f"数据量较少({data_len})，部分长周期指标可能无法计算: {symbol}")
    
    # 3. 初始化结果
    result = {
        'symbol': symbol,
        'current_price': float(closes[-1]),
        'data_points': data_len,
    }
    
    # 4. 核心指标计算 (OHLC 相关)
    result.update(calculate_ma(closes))
    result.update(calculate_rsi(closes))
    result.update(calculate_bollinger(closes))
    result.update(calculate_macd(closes))
    result.update(calculate_vwap(closes, highs, lows, volumes))
    result.update(calculate_pivot_points(closes, highs, lows))
    result.update(calculate_price_change(closes))
    result.update(calculate_volatility(closes))
    result.update(calculate_support_resistance(closes, highs, lows))
    result.update(analyze_trend_strength(closes, highs, lows))
    result.update(calculate_fibonacci_retracement(highs, lows))

    # 5. 成交量相关指标
    valid_volumes = volumes[volumes > 0]
    result.update(calculate_volume(volumes))
    
    if len(volumes) >= 20:
        obv = calculate_obv(closes, volumes)
        result['obv_current'] = float(obv[-1]) if len(obv) > 0 else 0.0
        result['obv_trend'] = get_trend(obv[-10:]) if len(obv) >= 10 else 'neutral'
    
    # 6. 条件触发指标 (根据数据长度)
    if data_len >= 9:
        result.update(calculate_kdj(closes, highs, lows))
    
    if data_len >= 10:
        result.update(calculate_sar(closes, highs, lows))
        
    if data_len >= 11:
        result.update(calculate_supertrend(closes, highs, lows))

    if data_len >= 14:
        atr = calculate_atr(closes, highs, lows)
        result['atr'] = atr
        result['atr_percent'] = float((atr / closes[-1]) * 100)
        result['williams_r'] = calculate_williams_r(closes, highs, lows)
        result.update(calculate_cci(closes, highs, lows))
    
    if data_len >= 20:
        result.update(calculate_volume_profile(closes, highs, lows, volumes))
    
    if data_len >= 28:
        result.update(calculate_adx(closes, highs, lows))
        result.update(calculate_stoch_rsi(closes))
        
    if data_len >= 52:
        result.update(calculate_ichimoku(closes, highs, lows))

    # 7. 周期分析 (Yearly/Monthly/Cycles)
    if data_len >= 30:
        timestamps = _extract_timestamps(hist_data)
        
        # 基础周期波形分析
        cycle_data = calculate_cycle_analysis(
            closes, highs, lows,
            volumes=volumes if len(valid_volumes) > 0 else None,
            timestamps=timestamps,
            use_adaptive=True,
            use_wavelet=True
        )
        result.update(cycle_data)
        
        # 季节性周期统计
        yearly_result = analyze_yearly_cycles(closes, highs, lows, timestamps)
        monthly_result = analyze_monthly_cycles(closes, highs, lows, timestamps)
        result['yearly_cycles'] = yearly_result.get('yearly_stats', [])
        result['monthly_cycles'] = monthly_result.get('monthly_stats', [])
        
    logger.info(f"技术分析完成: {symbol}, 数据点: {data_len}")
    return sanitize_data(result), None  # 返回结果和错误信息（无错误为None）
