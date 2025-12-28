# -*- coding: utf-8 -*-
"""
机构操作分析 - 基于量价关系和技术指标推断机构操作行为

技术原理：
1. 机构操作特征：
   - 大单交易：成交量异常放大
   - 价格行为：建仓时价格缓慢上升，出货时价格快速下跌
   - 资金流向：通过OBV、成交量分析判断资金流入/流出
   - 持仓成本：通过VWAP判断机构平均成本
   - 筹码分布：通过Volume Profile判断机构持仓区域
   - 波动率变化：机构操作可能影响价格波动率
   - 技术指标异常：某些指标组合可能反映机构操作

2. 分析方法：
   - 成交量异常分析：识别异常放量/缩量
   - 量价关系分析：价涨量增（建仓）、价跌量增（出货）、价涨量缩（控盘）
   - 资金流向分析：通过OBV趋势判断资金流向
   - 持仓成本分析：通过VWAP判断机构成本区间
   - 筹码集中度分析：通过Volume Profile判断筹码集中度
   - 价格行为模式：识别建仓/出货/洗盘模式
"""

import numpy as np


def calculate_institutional_activity(closes, highs, lows, volumes, vwap=None, obv_trend=None, vp_poc=None):
    """
    分析机构操作行为
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        volumes: 成交量数组
        vwap: VWAP值（可选）
        obv_trend: OBV趋势（可选）
        vp_poc: Volume Profile POC（可选）
    
    返回:
        dict: 包含机构操作分析结果的字典
    """
    result = {}
    
    if len(closes) < 20:
        return result
    
    closes = np.array(closes, dtype=float)
    highs = np.array(highs, dtype=float)
    lows = np.array(lows, dtype=float)
    volumes = np.array(volumes, dtype=float)
    
    # 过滤无效数据
    valid_mask = ~(np.isnan(closes) | np.isnan(highs) | np.isnan(lows) | np.isnan(volumes))
    if not np.any(valid_mask):
        return result
    
    closes = closes[valid_mask]
    highs = highs[valid_mask]
    lows = lows[valid_mask]
    volumes = volumes[valid_mask]
    
    if len(closes) < 20:
        return result
    
    # 1. 成交量异常分析
    # 计算成交量移动平均
    volume_ma_20 = np.mean(volumes[-20:])
    volume_ma_60 = np.mean(volumes[-60:]) if len(volumes) >= 60 else volume_ma_20
    
    current_volume = volumes[-1]
    volume_ratio_20 = current_volume / volume_ma_20 if volume_ma_20 > 0 else 0
    volume_ratio_60 = current_volume / volume_ma_60 if volume_ma_60 > 0 else 0
    
    # 识别异常放量（可能是机构操作）
    is_volume_spike = bool(volume_ratio_20 > 2.0)  # 成交量是20日均量的2倍以上
    is_volume_surge = bool(volume_ratio_20 > 3.0)  # 成交量是20日均量的3倍以上（强烈信号）
    is_volume_shrink = bool(volume_ratio_20 < 0.5)  # 成交量是20日均量的0.5倍以下（可能控盘）
    
    result['volume_ratio_20'] = float(volume_ratio_20)
    result['volume_ratio_60'] = float(volume_ratio_60)
    result['is_volume_spike'] = is_volume_spike
    result['is_volume_surge'] = is_volume_surge
    result['is_volume_shrink'] = is_volume_shrink
    
    # 2. 量价关系分析
    # 计算价格变化
    price_change_1d = ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) >= 2 else 0
    price_change_5d = ((closes[-1] - closes[-6]) / closes[-6] * 100) if len(closes) >= 6 else 0
    price_change_20d = ((closes[-1] - closes[-21]) / closes[-21] * 100) if len(closes) >= 21 else 0
    
    # 计算成交量变化
    volume_change_1d = ((volumes[-1] - volumes[-2]) / volumes[-2] * 100) if len(volumes) >= 2 else 0
    volume_change_5d = ((volumes[-1] - volumes[-6]) / volumes[-6] * 100) if len(volumes) >= 6 else 0
    
    # 量价关系模式
    # 价涨量增：可能是机构建仓
    price_volume_rising = bool(price_change_5d > 3.0 and volume_change_5d > 20.0)
    # 价跌量增：可能是机构出货
    price_volume_falling = bool(price_change_5d < -3.0 and volume_change_5d > 20.0)
    # 价涨量缩：可能是机构控盘或散户追涨
    price_rising_volume_shrinking = bool(price_change_5d > 3.0 and volume_change_5d < -10.0)
    # 价跌量缩：可能是机构洗盘或散户恐慌
    price_falling_volume_shrinking = bool(price_change_5d < -3.0 and volume_change_5d < -10.0)
    
    result['price_change_5d'] = float(price_change_5d)
    result['volume_change_5d'] = float(volume_change_5d)
    result['price_volume_rising'] = price_volume_rising
    result['price_volume_falling'] = price_volume_falling
    result['price_rising_volume_shrinking'] = price_rising_volume_shrinking
    result['price_falling_volume_shrinking'] = price_falling_volume_shrinking
    
    # 3. 资金流向分析（基于OBV趋势）
    if obv_trend:
        # OBV上升表示资金流入，下降表示资金流出
        if obv_trend == 'up':
            result['fund_flow'] = 'inflow'
            result['fund_flow_desc'] = '资金流入'
        elif obv_trend == 'down':
            result['fund_flow'] = 'outflow'
            result['fund_flow_desc'] = '资金流出'
        else:
            result['fund_flow'] = 'neutral'
            result['fund_flow_desc'] = '资金平衡'
    else:
        # 如果没有OBV趋势，通过价格和成交量估算
        # 计算最近10天的资金流向
        if len(closes) >= 10:
            recent_closes = closes[-10:]
            recent_volumes = volumes[-10:]
            fund_flow_score = 0.0
            for i in range(1, len(recent_closes)):
                if recent_closes[i] > recent_closes[i-1]:
                    fund_flow_score += recent_volumes[i]  # 上涨时成交量计入流入
                elif recent_closes[i] < recent_closes[i-1]:
                    fund_flow_score -= recent_volumes[i]  # 下跌时成交量计入流出
            
            avg_volume = np.mean(recent_volumes)
            if fund_flow_score > avg_volume * 2:
                result['fund_flow'] = 'inflow'
                result['fund_flow_desc'] = '资金流入'
            elif fund_flow_score < -avg_volume * 2:
                result['fund_flow'] = 'outflow'
                result['fund_flow_desc'] = '资金流出'
            else:
                result['fund_flow'] = 'neutral'
                result['fund_flow_desc'] = '资金平衡'
    
    # 4. 持仓成本分析（基于VWAP）
    if vwap:
        current_price = closes[-1]
        vwap_deviation = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0
        
        result['vwap'] = float(vwap)
        result['vwap_deviation'] = float(vwap_deviation)
        
        # 价格低于VWAP：可能被低估，机构可能建仓
        if vwap_deviation < -3.0:
            result['cost_position'] = 'below_cost'
            result['cost_position_desc'] = '价格低于机构成本，可能建仓机会'
        # 价格高于VWAP：机构盈利，可能出货
        elif vwap_deviation > 3.0:
            result['cost_position'] = 'above_cost'
            result['cost_position_desc'] = '价格高于机构成本，可能出货风险'
        else:
            result['cost_position'] = 'near_cost'
            result['cost_position_desc'] = '价格接近机构成本，多空平衡'
    
    # 5. 筹码集中度分析（基于Volume Profile POC）
    if vp_poc:
        current_price = closes[-1]
        poc_deviation = ((current_price - vp_poc) / vp_poc * 100) if vp_poc > 0 else 0
        
        result['vp_poc'] = float(vp_poc)
        result['poc_deviation'] = float(poc_deviation)
        
        # 价格接近POC：筹码集中，机构可能控盘
        if abs(poc_deviation) < 2.0:
            result['chip_concentration'] = 'high'
            result['chip_concentration_desc'] = '筹码高度集中，机构可能控盘'
        # 价格远离POC：筹码分散
        elif abs(poc_deviation) > 5.0:
            result['chip_concentration'] = 'low'
            result['chip_concentration_desc'] = '筹码分散，机构可能在建仓或出货'
        else:
            result['chip_concentration'] = 'medium'
            result['chip_concentration_desc'] = '筹码集中度中等'
    
    # 6. 价格行为模式识别
    # 分析最近20天的价格行为
    if len(closes) >= 20:
        recent_closes = closes[-20:]
        recent_volumes = volumes[-20:]
        
        # 计算价格趋势
        price_trend = np.polyfit(range(len(recent_closes)), recent_closes, 1)[0]
        
        # 计算波动率
        price_returns = np.diff(recent_closes) / recent_closes[:-1]
        volatility = np.std(price_returns) * 100
        
        # 识别价格行为模式
        # 模式1：缓慢上涨 + 放量 = 机构建仓
        if price_trend > 0 and price_change_20d > 5.0 and volume_ratio_20 > 1.5:
            result['price_pattern'] = 'accumulation'
            result['price_pattern_desc'] = '缓慢上涨+放量，可能是机构建仓'
        # 模式2：快速下跌 + 放量 = 机构出货
        elif price_trend < 0 and price_change_20d < -5.0 and volume_ratio_20 > 1.5:
            result['price_pattern'] = 'distribution'
            result['price_pattern_desc'] = '快速下跌+放量，可能是机构出货'
        # 模式3：横盘 + 缩量 = 机构洗盘或控盘
        elif abs(price_change_20d) < 3.0 and volume_ratio_20 < 0.8:
            result['price_pattern'] = 'consolidation'
            result['price_pattern_desc'] = '横盘+缩量，可能是机构洗盘或控盘'
        # 模式4：快速上涨 + 缩量 = 机构控盘拉升
        elif price_trend > 0 and price_change_20d > 10.0 and volume_ratio_20 < 0.8:
            result['price_pattern'] = 'controlled_rise'
            result['price_pattern_desc'] = '快速上涨+缩量，可能是机构控盘拉升'
        else:
            result['price_pattern'] = 'normal'
            result['price_pattern_desc'] = '正常波动'
        
        result['price_trend'] = float(price_trend)
        result['volatility_20d'] = float(volatility)
    
    # 7. 综合机构操作信号
    activity_score = 0.0
    activity_signals = []
    
    # 信号1：异常放量
    if is_volume_surge:
        activity_score += 30
        activity_signals.append('异常放量（强烈信号）')
    elif is_volume_spike:
        activity_score += 20
        activity_signals.append('放量')
    
    # 信号2：量价关系
    if price_volume_rising:
        activity_score += 25
        activity_signals.append('价涨量增（建仓信号）')
    elif price_volume_falling:
        activity_score += 25
        activity_signals.append('价跌量增（出货信号）')
    
    # 信号3：资金流向
    if result.get('fund_flow') == 'inflow':
        activity_score += 15
        activity_signals.append('资金流入')
    elif result.get('fund_flow') == 'outflow':
        activity_score += 15
        activity_signals.append('资金流出')
    
    # 信号4：持仓成本
    if result.get('cost_position') == 'below_cost':
        activity_score += 10
        activity_signals.append('价格低于机构成本')
    elif result.get('cost_position') == 'above_cost':
        activity_score += 10
        activity_signals.append('价格高于机构成本')
    
    # 信号5：价格行为模式
    if result.get('price_pattern') == 'accumulation':
        activity_score += 20
        activity_signals.append('建仓模式')
    elif result.get('price_pattern') == 'distribution':
        activity_score += 20
        activity_signals.append('出货模式')
    
    result['activity_score'] = float(min(100, activity_score))
    result['activity_signals'] = activity_signals
    
    # 判断机构操作强度
    if activity_score >= 60:
        result['activity_level'] = 'high'
        result['activity_level_desc'] = '机构操作迹象明显'
    elif activity_score >= 40:
        result['activity_level'] = 'medium'
        result['activity_level_desc'] = '机构操作迹象中等'
    elif activity_score >= 20:
        result['activity_level'] = 'low'
        result['activity_level_desc'] = '机构操作迹象较弱'
    else:
        result['activity_level'] = 'none'
        result['activity_level_desc'] = '无明显机构操作迹象'
    
    # 8. 操作建议
    if activity_score >= 60:
        if result.get('price_pattern') == 'accumulation' or result.get('fund_flow') == 'inflow':
            result['suggestion'] = '机构可能在建仓，可关注买入机会'
        elif result.get('price_pattern') == 'distribution' or result.get('fund_flow') == 'outflow':
            result['suggestion'] = '机构可能在出货，需注意风险'
        else:
            result['suggestion'] = '机构操作迹象明显，需结合其他指标判断'
    elif activity_score >= 40:
        result['suggestion'] = '机构操作迹象中等，需进一步观察'
    else:
        result['suggestion'] = '无明显机构操作迹象，正常波动'
    
    return result

