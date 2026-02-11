# -*- coding: utf-8 -*-
import numpy as np

def calculate_vwap(closes, highs, lows, volumes):
    """
    计算成交量加权平均价 (VWAP)
    公式: VWAP = sum(Typical Price * Volume) / sum(Volume)
    Typical Price = (High + Low + Close) / 3
    """
    if len(closes) == 0 or len(volumes) == 0:
        return {}
    
    typical_prices = (highs + lows + closes) / 3
    
    # 简单的全量 VWAP (通常 VWAP 是按天重置的，但对于日线数据，我们计算一个累积的或者滑动窗口的)
    # 这里我们返回当前点的 VWAP 值
    vwap = np.sum(typical_prices * volumes) / np.sum(volumes)
    
    # 计算最近 20 日的 VWAP 作为参考
    vwap_20 = 0
    if len(closes) >= 20:
        vwap_20 = np.sum(typical_prices[-20:] * volumes[-20:]) / np.sum(volumes[-20:])
    
    signal = 'at'
    if closes[-1] > vwap * 1.01:
        signal = 'above'
    elif closes[-1] < vwap * 0.99:
        signal = 'below'
        
    return {
        'vwap': float(vwap),
        'vwap_20': float(vwap_20) if vwap_20 > 0 else float(vwap),
        'vwap_signal': signal,
        'vwap_deviation': float((closes[-1] - vwap) / vwap * 100)
    }
