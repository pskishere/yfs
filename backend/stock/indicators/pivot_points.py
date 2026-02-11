# -*- coding: utf-8 -*-

def calculate_pivot_points(closes, highs, lows):
    """
    计算标准枢轴点 (Standard Pivot Points)
    基于前一周期的数据计算
    """
    if len(closes) < 2:
        return {}
    
    # 使用最近一个完整周期的数据 (通常是前一天，这里用最后一条完整数据的前一条)
    # 对于实时分析，通常用昨天的 OHLC
    prev_high = highs[-2]
    prev_low = lows[-2]
    prev_close = closes[-2]
    
    # 枢轴点 (P)
    p = (prev_high + prev_low + prev_close) / 3
    
    # 阻力位
    r1 = (2 * p) - prev_low
    r2 = p + (prev_high - prev_low)
    r3 = prev_high + 2 * (p - prev_low)
    
    # 支撑位
    s1 = (2 * p) - prev_high
    s2 = p - (prev_high - prev_low)
    s3 = prev_low - 2 * (prev_high - p)
    
    return {
        'pivot': float(p),
        'pivot_r1': float(r1),
        'pivot_r2': float(r2),
        'pivot_r3': float(r3),
        'pivot_s1': float(s1),
        'pivot_s2': float(s2),
        'pivot_s3': float(s3)
    }
