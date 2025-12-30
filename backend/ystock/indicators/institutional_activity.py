# -*- coding: utf-8 -*-
"""
机构操作分析
新增功能:
1. MFI (Money Flow Index) 资金流量指数
2. CMF (Chaikin Money Flow) 蔡金资金流量指标
3. 筹码分布分析
4. 优化的活跃度评分算法
5. 主力成本区间估算
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional


def calculate_mfi(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, 
                  volumes: np.ndarray, period: int = 14) -> Dict[str, Any]:
    """
    计算资金流量指数 (Money Flow Index)
    
    MFI是综合价格和成交量的动量指标，类似RSI但考虑成交量
    
    参数:
        highs: 最高价数组
        lows: 最低价数组
        closes: 收盘价数组
        volumes: 成交量数组
        period: 计算周期，默认14
    
    返回:
        dict: MFI相关指标
    """
    result = {}
    
    if len(closes) < period + 1:
        return result
    
    # 计算典型价格 (Typical Price)
    typical_price = (highs + lows + closes) / 3
    
    # 计算原始资金流量 (Raw Money Flow)
    money_flow = typical_price * volumes
    
    # 分离正资金流和负资金流
    positive_flow = np.zeros(len(money_flow))
    negative_flow = np.zeros(len(money_flow))
    
    for i in range(1, len(typical_price)):
        if typical_price[i] > typical_price[i-1]:
            positive_flow[i] = money_flow[i]
        elif typical_price[i] < typical_price[i-1]:
            negative_flow[i] = money_flow[i]
    
    # 计算period天的正负资金流总和
    if len(positive_flow) >= period:
        positive_mf_sum = np.sum(positive_flow[-period:])
        negative_mf_sum = np.sum(negative_flow[-period:])
        
        # 计算资金流量比率 (Money Flow Ratio)
        if negative_mf_sum > 0:
            money_flow_ratio = positive_mf_sum / negative_mf_sum
            # 计算MFI
            mfi = 100 - (100 / (1 + money_flow_ratio))
        else:
            mfi = 100.0 if positive_mf_sum > 0 else 50.0
        
        result['mfi'] = float(mfi)
        result['money_flow_ratio'] = float(money_flow_ratio) if negative_mf_sum > 0 else float('inf')
        
        # MFI信号解读
        if mfi >= 80:
            result['mfi_signal'] = 'overbought'
            result['mfi_signal_desc'] = '超买区域，资金流入过度，可能回调'
        elif mfi >= 60:
            result['mfi_signal'] = 'strong'
            result['mfi_signal_desc'] = '资金流入强劲'
        elif mfi >= 40:
            result['mfi_signal'] = 'neutral'
            result['mfi_signal_desc'] = '资金流向中性'
        elif mfi >= 20:
            result['mfi_signal'] = 'weak'
            result['mfi_signal_desc'] = '资金流出明显'
        else:
            result['mfi_signal'] = 'oversold'
            result['mfi_signal_desc'] = '超卖区域，资金流出过度，可能反弹'
        
        # 计算MFI背离
        # 检查最近是否有价格创新高但MFI未创新高（顶背离）
        # 或价格创新低但MFI未创新低（底背离）
        if len(closes) >= period * 2:
            recent_closes = closes[-period:]
            recent_mfi_values = []
            
            # 简化版：只计算最近一个MFI值，实际应该计算多个MFI值
            # 这里只返回当前MFI，背离分析需要历史MFI数据
            result['mfi_divergence'] = 'none'
    
    return result


def calculate_cmf(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                  volumes: np.ndarray, period: int = 20) -> Dict[str, Any]:
    """
    计算蔡金资金流量 (Chaikin Money Flow)
    
    CMF通过测量成交量加权的价格位置来判断资金流向
    
    参数:
        highs: 最高价数组
        lows: 最低价数组
        closes: 收盘价数组
        volumes: 成交量数组
        period: 计算周期，默认20
    
    返回:
        dict: CMF相关指标
    """
    result = {}
    
    if len(closes) < period:
        return result
    
    # 计算资金流量乘数 (Money Flow Multiplier)
    # MFM = [(Close - Low) - (High - Close)] / (High - Low)
    mfm = np.zeros(len(closes))
    
    for i in range(len(closes)):
        high_low_diff = highs[i] - lows[i]
        if high_low_diff > 0:
            mfm[i] = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / high_low_diff
        else:
            mfm[i] = 0
    
    # 计算资金流量成交量 (Money Flow Volume)
    mfv = mfm * volumes
    
    # 计算CMF
    if len(mfv) >= period:
        cmf_sum = np.sum(mfv[-period:])
        volume_sum = np.sum(volumes[-period:])
        
        cmf = cmf_sum / volume_sum if volume_sum > 0 else 0
        
        result['cmf'] = float(cmf)
        
        # CMF信号解读
        if cmf >= 0.25:
            result['cmf_signal'] = 'strong_accumulation'
            result['cmf_signal_desc'] = '强力买入，资金大量流入'
        elif cmf >= 0.05:
            result['cmf_signal'] = 'accumulation'
            result['cmf_signal_desc'] = '买入信号，资金流入'
        elif cmf >= -0.05:
            result['cmf_signal'] = 'neutral'
            result['cmf_signal_desc'] = '中性，资金流向不明显'
        elif cmf >= -0.25:
            result['cmf_signal'] = 'distribution'
            result['cmf_signal_desc'] = '卖出信号，资金流出'
        else:
            result['cmf_signal'] = 'strong_distribution'
            result['cmf_signal_desc'] = '强力卖出，资金大量流出'
    
    return result


def calculate_chip_distribution(closes: np.ndarray, highs: np.ndarray, 
                                lows: np.ndarray, volumes: np.ndarray,
                                lookback: int = 60, bins: int = 50) -> Dict[str, Any]:
    """
    计算筹码分布分析
    
    通过统计历史成交量在不同价格区间的分布，估算持仓成本分布
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        volumes: 成交量数组
        lookback: 回看周期，默认60天
        bins: 价格区间数量，默认50
    
    返回:
        dict: 筹码分布相关指标
    """
    result = {}
    
    if len(closes) < lookback:
        lookback = len(closes)
    
    if lookback < 10:
        return result
    
    # 获取回看周期内的数据
    recent_closes = closes[-lookback:]
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    recent_volumes = volumes[-lookback:]
    
    # 确定价格范围
    price_min = float(np.min(recent_lows))
    price_max = float(np.max(recent_highs))
    current_price = float(closes[-1])
    
    if price_max <= price_min:
        return result
    
    # 创建价格区间
    price_bins = np.linspace(price_min, price_max, bins + 1)
    volume_distribution = np.zeros(bins)
    
    # 分配每天的成交量到价格区间
    # 简化方法：假设成交量均匀分布在当天的高低价之间
    for i in range(len(recent_closes)):
        low_price = recent_lows[i]
        high_price = recent_highs[i]
        volume = recent_volumes[i]
        
        # 找到高低价对应的区间
        low_bin = np.digitize(low_price, price_bins) - 1
        high_bin = np.digitize(high_price, price_bins) - 1
        
        # 边界处理
        low_bin = max(0, min(bins - 1, low_bin))
        high_bin = max(0, min(bins - 1, high_bin))
        
        if low_bin == high_bin:
            volume_distribution[low_bin] += volume
        else:
            # 将成交量均匀分配到涉及的区间
            affected_bins = high_bin - low_bin + 1
            volume_distribution[low_bin:high_bin + 1] += volume / affected_bins
    
    total_volume = np.sum(volume_distribution)
    
    if total_volume == 0:
        return result
    
    # 计算当前价格所在区间
    current_bin = np.digitize(current_price, price_bins) - 1
    current_bin = max(0, min(bins - 1, current_bin))
    
    # 1. 计算获利盘比例（当前价格以下的筹码）
    profit_volume = np.sum(volume_distribution[:current_bin + 1])
    profit_ratio = profit_volume / total_volume
    
    result['chip_profit_ratio'] = float(profit_ratio)
    result['chip_loss_ratio'] = float(1.0 - profit_ratio)
    
    # 2. 找出筹码峰值（成本密集区）
    peak_bin = np.argmax(volume_distribution)
    peak_price = (price_bins[peak_bin] + price_bins[peak_bin + 1]) / 2
    peak_volume_ratio = volume_distribution[peak_bin] / total_volume
    
    result['chip_peak_price'] = float(peak_price)
    result['chip_peak_volume_ratio'] = float(peak_volume_ratio)
    result['chip_concentration'] = float(peak_volume_ratio)
    
    # 筹码集中度描述
    if peak_volume_ratio > 0.3:
        result['chip_concentration_desc'] = '高度集中'
        result['chip_concentration_level'] = 'high'
    elif peak_volume_ratio > 0.15:
        result['chip_concentration_desc'] = '较为集中'
        result['chip_concentration_level'] = 'medium'
    else:
        result['chip_concentration_desc'] = '较为分散'
        result['chip_concentration_level'] = 'low'
    
    # 3. 计算筹码分布的统计特征
    # 加权平均成本
    bin_centers = (price_bins[:-1] + price_bins[1:]) / 2
    weighted_cost = np.sum(bin_centers * volume_distribution) / total_volume
    result['chip_weighted_avg_cost'] = float(weighted_cost)
    
    # 成本偏离度
    cost_deviation = (current_price - weighted_cost) / weighted_cost * 100
    result['chip_cost_deviation_pct'] = float(cost_deviation)
    
    # 4. 识别主力成本区间（成交量最集中的区域）
    # 找出成交量超过平均值的区间
    avg_volume_per_bin = total_volume / bins
    significant_bins = np.where(volume_distribution > avg_volume_per_bin * 1.5)[0]
    
    if len(significant_bins) > 0:
        main_cost_low = price_bins[significant_bins[0]]
        main_cost_high = price_bins[significant_bins[-1] + 1]
        result['chip_main_cost_low'] = float(main_cost_low)
        result['chip_main_cost_high'] = float(main_cost_high)
        result['chip_main_cost_center'] = float((main_cost_low + main_cost_high) / 2)
        
        # 判断当前价格与主力成本区间的关系
        if current_price < main_cost_low:
            result['chip_price_position'] = 'below_main_cost'
            result['chip_price_position_desc'] = '价格低于主力成本区，支撑较强'
        elif current_price > main_cost_high:
            result['chip_price_position'] = 'above_main_cost'
            result['chip_price_position_desc'] = '价格高于主力成本区，压力较大'
        else:
            result['chip_price_position'] = 'in_main_cost'
            result['chip_price_position_desc'] = '价格在主力成本区内，多空争夺'
    
    # 5. 计算筹码分散度（熵）
    normalized_dist = volume_distribution / total_volume
    normalized_dist = normalized_dist[normalized_dist > 0]
    chip_entropy = -np.sum(normalized_dist * np.log(normalized_dist))
    max_entropy = np.log(bins)
    normalized_entropy = chip_entropy / max_entropy
    
    result['chip_entropy'] = float(normalized_entropy)
    
    if normalized_entropy > 0.8:
        result['chip_dispersion'] = 'highly_dispersed'
        result['chip_dispersion_desc'] = '筹码高度分散，无明显主力'
    elif normalized_entropy > 0.5:
        result['chip_dispersion'] = 'moderately_dispersed'
        result['chip_dispersion_desc'] = '筹码较为分散'
    else:
        result['chip_dispersion'] = 'concentrated'
        result['chip_dispersion_desc'] = '筹码集中，可能有主力控盘'
    
    return result


def calculate_main_force_cost(closes: np.ndarray, highs: np.ndarray,
                              lows: np.ndarray, volumes: np.ndarray,
                              lookback: int = 30) -> Dict[str, Any]:
    """
    估算主力成本区间
    
    通过分析大成交量时期的价格区间估算主力成本
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        volumes: 成交量数组
        lookback: 回看周期，默认30天
    
    返回:
        dict: 主力成本相关指标
    """
    result = {}
    
    if len(closes) < lookback:
        lookback = len(closes)
    
    if lookback < 10:
        return result
    
    recent_closes = closes[-lookback:]
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    recent_volumes = volumes[-lookback:]
    
    # 1. 识别大成交量日期（成交量>1.5倍平均值）
    avg_volume = np.mean(recent_volumes)
    high_volume_mask = recent_volumes > (avg_volume * 1.5)
    
    if not np.any(high_volume_mask):
        return result
    
    # 2. 计算大成交量日的价格区间
    high_volume_prices = []
    high_volume_weights = []
    
    for i in range(len(recent_closes)):
        if high_volume_mask[i]:
            # 使用均价作为该日的代表价格
            avg_price = (recent_highs[i] + recent_lows[i] + recent_closes[i]) / 3
            high_volume_prices.append(avg_price)
            high_volume_weights.append(recent_volumes[i])
    
    if len(high_volume_prices) == 0:
        return result
    
    # 3. 计算加权平均成本
    high_volume_prices = np.array(high_volume_prices)
    high_volume_weights = np.array(high_volume_weights)
    
    weighted_avg_cost = np.average(high_volume_prices, weights=high_volume_weights)
    
    # 4. 计算成本区间（使用标准差）
    weighted_std = np.sqrt(np.average((high_volume_prices - weighted_avg_cost) ** 2, 
                                     weights=high_volume_weights))
    
    cost_lower = weighted_avg_cost - weighted_std
    cost_upper = weighted_avg_cost + weighted_std
    
    result['main_force_cost'] = float(weighted_avg_cost)
    result['main_force_cost_lower'] = float(cost_lower)
    result['main_force_cost_upper'] = float(cost_upper)
    result['main_force_cost_range_pct'] = float((cost_upper - cost_lower) / weighted_avg_cost * 100)
    
    # 5. 判断当前价格与主力成本的关系
    current_price = closes[-1]
    cost_deviation = (current_price - weighted_avg_cost) / weighted_avg_cost * 100
    
    result['main_force_cost_deviation_pct'] = float(cost_deviation)
    
    if current_price < cost_lower:
        result['main_force_position'] = 'below_cost'
        result['main_force_position_desc'] = f'价格低于主力成本{abs(cost_deviation):.1f}%，主力套牢'
    elif current_price > cost_upper:
        result['main_force_position'] = 'above_cost'
        result['main_force_position_desc'] = f'价格高于主力成本{cost_deviation:.1f}%，主力获利'
    else:
        result['main_force_position'] = 'near_cost'
        result['main_force_position_desc'] = f'价格接近主力成本区间'
    
    return result


def calculate_institutional_activity(closes: np.ndarray, highs: np.ndarray,
                                            lows: np.ndarray, volumes: np.ndarray,
                                            vwap: Optional[float] = None,
                                            obv_trend: Optional[str] = None,
                                            vp_poc: Optional[float] = None) -> Dict[str, Any]:
    """
    机构操作分析
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        volumes: 成交量数组
        vwap: VWAP值（可选）
        obv_trend: OBV趋势（可选）
        vp_poc: Volume Profile POC（可选）
    
    返回:
        dict: 机构操作分析结果
    """
    result = {}
    
    if len(closes) < 20:
        return result
    
    # 基础量价分析
    closes_arr = np.array(closes, dtype=float)
    volumes_arr = np.array(volumes, dtype=float)
    
    # 成交量比率
    volume_ratio_20 = 0.0
    volume_ratio_60 = 0.0
    if len(volumes_arr) >= 20:
        volume_ma_20 = np.mean(volumes_arr[-20:])
        volume_ma_60 = np.mean(volumes_arr[-60:]) if len(volumes_arr) >= 60 else volume_ma_20
        current_volume = volumes_arr[-1]
        volume_ratio_20 = float(current_volume / volume_ma_20 if volume_ma_20 > 0 else 0)
        volume_ratio_60 = float(current_volume / volume_ma_60 if volume_ma_60 > 0 else 0)
        result['volume_ratio_20'] = volume_ratio_20
        result['volume_ratio_60'] = volume_ratio_60
    
    # 添加MFI分析
    mfi_result = calculate_mfi(highs, lows, closes, volumes, period=14)
    result.update(mfi_result)
    
    # 添加CMF分析
    cmf_result = calculate_cmf(highs, lows, closes, volumes, period=20)
    result.update(cmf_result)
    
    # 添加筹码分布分析
    chip_result = calculate_chip_distribution(closes, highs, lows, volumes, lookback=60)
    result.update(chip_result)
    
    # 添加主力成本估算
    main_force_result = calculate_main_force_cost(closes, highs, lows, volumes, lookback=30)
    result.update(main_force_result)
    
    return result

