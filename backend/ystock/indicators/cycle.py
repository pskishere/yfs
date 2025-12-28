# -*- coding: utf-8 -*-
"""
周期分析 - 检测价格数据的周期性模式
"""

import numpy as np
from scipy import signal
from scipy.fft import fft


def find_peaks_and_troughs(prices, min_period=5, min_prominence=None):
    """
    识别价格的高点和低点，过滤小波动
    
    参数:
        prices: 价格数组
        min_period: 最小周期长度（用于过滤噪声）
        min_prominence: 最小突出度（价格变化的百分比阈值，用于过滤小波动）
    
    返回:
        peaks: 高点索引列表
        troughs: 低点索引列表
    """
    if len(prices) < min_period * 2:
        return [], []
    
    # 如果没有指定最小突出度，根据价格范围自动计算
    if min_prominence is None:
        price_range = np.max(prices) - np.min(prices)
        avg_price = np.mean(prices)
        # 最小突出度为平均价格的3%（过滤小于3%的波动）
        min_prominence = avg_price * 0.03
    
    # 使用scipy的find_peaks函数，添加prominence参数过滤小波动
    peaks, peak_properties = signal.find_peaks(
        prices, 
        distance=min_period,
        prominence=min_prominence  # 只识别突出度大于阈值的峰值
    )
    troughs, trough_properties = signal.find_peaks(
        -prices, 
        distance=min_period,
        prominence=min_prominence  # 只识别突出度大于阈值的谷值
    )
    
    return peaks.tolist(), troughs.tolist()


def calculate_autocorrelation(prices, max_lag=None):
    """
    计算价格序列的自相关函数
    
    参数:
        prices: 价格数组
        max_lag: 最大滞后周期（默认使用数据长度的一半）
    
    返回:
        autocorr: 自相关值数组
        lags: 滞后周期数组
    """
    n = len(prices)
    if n < 20:
        return np.array([]), np.array([])
    
    if max_lag is None:
        max_lag = min(n // 2, 100)  # 限制最大滞后周期
    
    # 标准化价格（去均值）
    prices_normalized = prices - np.mean(prices)
    
    autocorr = []
    lags = []
    
    for lag in range(1, max_lag + 1):
        if lag >= n:
            break
        
        # 计算自相关
        corr = np.corrcoef(prices_normalized[:-lag], prices_normalized[lag:])[0, 1]
        if not np.isnan(corr):
            autocorr.append(corr)
            lags.append(lag)
    
    return np.array(autocorr), np.array(lags)


def detect_cycle_length(autocorr, lags, min_cycle=5, max_cycle=100):
    """
    从自相关函数中检测主要周期长度
    
    参数:
        autocorr: 自相关值数组
        lags: 滞后周期数组
        min_cycle: 最小周期长度
        max_cycle: 最大周期长度
    
    返回:
        dominant_cycle: 主要周期长度（如果检测到）
        cycle_strength: 周期强度（0-1）
    """
    if len(autocorr) == 0 or len(lags) == 0:
        return None, 0.0
    
    # 过滤有效范围
    valid_mask = (lags >= min_cycle) & (lags <= max_cycle)
    if not np.any(valid_mask):
        return None, 0.0
    
    valid_autocorr = autocorr[valid_mask]
    valid_lags = lags[valid_mask]
    
    # 找到自相关值最大的周期
    max_idx = np.argmax(valid_autocorr)
    dominant_cycle = int(valid_lags[max_idx])
    cycle_strength = float(valid_autocorr[max_idx])
    
    # 如果周期强度太低，认为没有明显周期
    if cycle_strength < 0.3:
        return None, 0.0
    
    return dominant_cycle, cycle_strength


def analyze_cycle_pattern(prices, highs, lows, timestamps=None):
    """
    分析价格周期模式 - 增强版，提供更详细的分析
    只使用最近3年的数据进行周期分析
    
    参数:
        prices: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        timestamps: 时间戳数组（可选）
    
    返回:
        dict: 包含周期分析结果的字典
    """
    result = {}
    
    if len(prices) < 30:
        return result
    
    # 使用最近3年的数据（约756个交易日，每年约252个交易日）
    # 如果数据不足3年，使用全部可用数据
    max_days = 756  # 3年 * 252个交易日
    actual_days = len(prices)
    if actual_days > max_days:
        # 如果数据超过3年，只使用最近3年
        prices = prices[-max_days:]
        highs = highs[-max_days:]
        lows = lows[-max_days:]
        if timestamps:
            timestamps = timestamps[-max_days:]
        result['data_range_note'] = f'基于最近3年数据（{max_days}个交易日）'
    else:
        # 如果数据不足3年，使用全部数据
        result['data_range_note'] = f'基于全部可用数据（{actual_days}个交易日，约{actual_days/252:.1f}年）'
    
    # 1. 识别高点和低点（过滤小波动，只关注大波动）
    # 计算价格的平均波动幅度，用于设置最小突出度
    price_changes = np.abs(np.diff(prices))
    avg_change = np.mean(price_changes)
    price_std = np.std(prices)
    avg_price = np.mean(prices)
    
    # 最小突出度：使用价格标准差的8%或平均价格的2%，取较大值
    # 这样可以过滤掉小的日常波动，只关注显著的价格变化（至少2-8%的波动）
    min_prominence_abs = max(price_std * 0.08, avg_price * 0.02)
    
    # 使用更大的min_period（10天）来过滤短期波动
    # 使用prominence来过滤幅度小的波动（至少2-8%的价格变化）
    peaks, troughs = find_peaks_and_troughs(prices, min_period=10, min_prominence=min_prominence_abs)
    
    # 记录过滤参数，用于说明
    result['filter_params'] = {
        'min_period': 10,
        'min_prominence_pct': float((min_prominence_abs / avg_price) * 100),
        'filtered_peaks': len(peaks),
        'filtered_troughs': len(troughs),
    }
    
    # 按周期分组，生成时间段和该时间段内的高低点
    # 周期定义：包括上涨周期（低点到高点）和下跌周期（高点到低点）
    cycle_periods = []
    
    # 合并所有高点和低点，按时间顺序排列
    all_turning_points = []
    for peak_idx in peaks:
        all_turning_points.append({'index': peak_idx, 'type': 'peak', 'price': float(prices[peak_idx])})
    for trough_idx in troughs:
        all_turning_points.append({'index': trough_idx, 'type': 'trough', 'price': float(prices[trough_idx])})
    
    # 按索引排序
    all_turning_points.sort(key=lambda x: x['index'])
    
    if len(all_turning_points) >= 2:
        period_index = 1
        for i in range(len(all_turning_points) - 1):
            start_point = all_turning_points[i]
            end_point = all_turning_points[i + 1]
            
            start_idx = start_point['index']
            end_idx = end_point['index']
            
            if end_idx <= start_idx:
                continue
            
            # 判断周期类型
            if start_point['type'] == 'trough' and end_point['type'] == 'peak':
                # 上涨周期：从低点到高点
                start_price = float(prices[start_idx])
                end_price = float(prices[end_idx])
                
                # 周期内的价格范围
                period_prices = prices[start_idx:end_idx + 1]
                period_high_values = highs[start_idx:end_idx + 1] if start_idx < len(highs) else period_prices
                
                # 找到周期内的最高价
                max_price_in_period = float(np.max(period_high_values))
                max_idx = start_idx + int(np.argmax(period_high_values))
                
                # 计算振幅
                amplitude = ((max_price_in_period - start_price) / start_price) * 100 if start_price > 0 else 0
                
                # 根据振幅判断周期类型
                # 窄幅横盘：5%以内；标准横盘：5%-15%；宽幅震荡：15%-25%
                amplitude_abs = abs(amplitude)
                if amplitude_abs < 5.0:
                    cycle_type = 'sideways'
                    cycle_type_desc = '窄幅横盘'
                elif amplitude_abs < 15.0:
                    # 5%-15%可能是标准横盘，但如果是上涨周期，保持为上涨
                    # 这里可以根据周期持续时间进一步判断
                    if (max_idx - start_idx) > 30:  # 持续时间超过30天，可能是横盘
                        cycle_type = 'sideways'
                        cycle_type_desc = '标准横盘'
                    else:
                        cycle_type = 'rise'
                        cycle_type_desc = '上涨'
                else:
                    cycle_type = 'rise'
                    cycle_type_desc = '上涨'
                
                period_info = {
                    'period_index': period_index,
                    'cycle_type': cycle_type,
                    'cycle_type_desc': cycle_type_desc,
                    'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                    'end_time': timestamps[max_idx] if timestamps and max_idx < len(timestamps) else None,
                    'start_index': int(start_idx),
                    'end_index': int(max_idx),
                    'duration': int(max_idx - start_idx),
                    'low_price': start_price,
                    'low_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                    'high_price': max_price_in_period,
                    'high_time': timestamps[max_idx] if timestamps and max_idx < len(timestamps) else None,
                    'amplitude': float(amplitude),
                }
                cycle_periods.append(period_info)
                period_index += 1
                
            elif start_point['type'] == 'peak' and end_point['type'] == 'trough':
                # 下跌周期：从高点到低点
                start_price = float(prices[start_idx])
                end_price = float(prices[end_idx])
                
                # 周期内的价格范围
                period_prices = prices[start_idx:end_idx + 1]
                period_low_values = lows[start_idx:end_idx + 1] if start_idx < len(lows) else period_prices
                
                # 找到周期内的最低价
                min_price_in_period = float(np.min(period_low_values))
                min_idx = start_idx + int(np.argmin(period_low_values))
                
                # 计算振幅（下跌周期振幅为负数）
                amplitude = ((min_price_in_period - start_price) / start_price) * 100 if start_price > 0 else 0
                amplitude_abs = abs(amplitude)  # 用于判断周期类型的绝对值
                
                # 根据振幅判断周期类型
                # 窄幅横盘：5%以内；标准横盘：5%-15%；宽幅震荡：15%-25%
                if amplitude_abs < 5.0:
                    cycle_type = 'sideways'
                    cycle_type_desc = '窄幅横盘'
                elif amplitude_abs < 15.0:
                    # 5%-15%可能是标准横盘，但如果是下跌周期，保持为下跌
                    # 这里可以根据周期持续时间进一步判断
                    if (min_idx - start_idx) > 30:  # 持续时间超过30天，可能是横盘
                        cycle_type = 'sideways'
                        cycle_type_desc = '标准横盘'
                        # 横盘时振幅保持正负方向（不取绝对值）
                    else:
                        cycle_type = 'decline'
                        cycle_type_desc = '下跌'
                else:
                    cycle_type = 'decline'
                    cycle_type_desc = '下跌'
                
                period_info = {
                    'period_index': period_index,
                    'cycle_type': cycle_type,
                    'cycle_type_desc': cycle_type_desc,
                    'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                    'end_time': timestamps[min_idx] if timestamps and min_idx < len(timestamps) else None,
                    'start_index': int(start_idx),
                    'end_index': int(min_idx),
                    'duration': int(min_idx - start_idx),
                    'high_price': start_price,
                    'high_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                    'low_price': min_price_in_period,
                    'low_time': timestamps[min_idx] if timestamps and min_idx < len(timestamps) else None,
                    'amplitude': float(amplitude),
                }
                cycle_periods.append(period_info)
                period_index += 1
        
        # 添加当前周期（从最后一个转折点到最新交易日）
        if len(all_turning_points) >= 1:
            last_point = all_turning_points[-1]
            last_idx = last_point['index']
            current_idx = len(prices) - 1  # 最新交易日的索引
            
            # 如果最后一个转折点不是最新交易日，添加当前周期
            if last_idx < current_idx:
                start_idx = last_idx
                start_price = float(prices[start_idx])
                current_price = float(prices[current_idx])
                
                # 当前周期内的价格范围
                current_period_prices = prices[start_idx:current_idx + 1]
                current_period_highs = highs[start_idx:current_idx + 1] if start_idx < len(highs) else current_period_prices
                current_period_lows = lows[start_idx:current_idx + 1] if start_idx < len(lows) else current_period_prices
                
                # 找到当前周期内的最高价和最低价
                max_price_in_current = float(np.max(current_period_highs))
                min_price_in_current = float(np.min(current_period_lows))
                max_idx_in_current = start_idx + int(np.argmax(current_period_highs))
                min_idx_in_current = start_idx + int(np.argmin(current_period_lows))
                
                # 判断当前周期的类型
                if last_point['type'] == 'trough':
                    # 从低点开始，可能是上涨或横盘，但需要根据实际价格变化判断
                    # 计算基于最新价格的振幅
                    amplitude_from_current = ((current_price - start_price) / start_price) * 100 if start_price > 0 else 0
                    amplitude_abs = abs(amplitude_from_current)
                    
                    # 根据实际价格变化判断周期类型
                    if amplitude_abs < 5.0:
                        cycle_type = 'sideways'
                        cycle_type_desc = '窄幅横盘（进行中）'
                    elif amplitude_abs < 15.0:
                        if (current_idx - start_idx) > 30:
                            cycle_type = 'sideways'
                            cycle_type_desc = '标准横盘（进行中）'
                        else:
                            # 根据实际价格变化方向判断
                            if amplitude_from_current > 0:
                                cycle_type = 'rise'
                                cycle_type_desc = '上涨（进行中）'
                            else:
                                cycle_type = 'decline'
                                cycle_type_desc = '下跌（进行中）'
                    else:
                        # 根据实际价格变化方向判断
                        if amplitude_from_current > 0:
                            cycle_type = 'rise'
                            cycle_type_desc = '上涨（进行中）'
                        else:
                            cycle_type = 'decline'
                            cycle_type_desc = '下跌（进行中）'
                    
                    # 根据周期类型设置起始价格和结束价格，并计算正确的振幅
                    if cycle_type == 'rise':
                        # 上涨周期：起始价格是低点，结束价格是高点
                        actual_start_price = start_price  # 从低点开始，起始价格就是低点
                        actual_end_price = max_price_in_current  # 结束价格是周期内的最高价
                        # 振幅 = (结束价格 - 起始价格) / 起始价格 * 100
                        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
                        current_period_info = {
                            'period_index': period_index,
                            'cycle_type': cycle_type,
                            'cycle_type_desc': cycle_type_desc,
                            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
                            'start_index': int(start_idx),
                            'end_index': int(current_idx),
                            'duration': int(current_idx - start_idx),
                            'low_price': actual_start_price,  # 起始价格是低点
                            'low_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'high_price': actual_end_price,  # 结束价格是周期内的最高价
                            'high_time': timestamps[max_idx_in_current] if timestamps and max_idx_in_current < len(timestamps) else None,
                            'amplitude': float(amplitude_corrected),  # 使用正确的振幅计算
                            'is_current': True,  # 标记为当前周期
                        }
                    elif cycle_type == 'decline':
                        # 下跌周期：起始价格是高点，结束价格是低点
                        actual_start_price = max_price_in_current  # 起始价格是周期内的最高价
                        actual_end_price = min_price_in_current  # 结束价格是周期内的最低价
                        # 振幅 = (结束价格 - 起始价格) / 起始价格 * 100（应该是负数）
                        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
                        current_period_info = {
                            'period_index': period_index,
                            'cycle_type': cycle_type,
                            'cycle_type_desc': cycle_type_desc,
                            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
                            'start_index': int(start_idx),
                            'end_index': int(current_idx),
                            'duration': int(current_idx - start_idx),
                            'high_price': actual_start_price,  # 起始价格是周期内的最高价
                            'high_time': timestamps[max_idx_in_current] if timestamps and max_idx_in_current < len(timestamps) else None,
                            'low_price': actual_end_price,  # 结束价格是周期内的最低价
                            'low_time': timestamps[min_idx_in_current] if timestamps and min_idx_in_current < len(timestamps) else None,
                            'amplitude': float(amplitude_corrected),  # 使用正确的振幅计算
                            'is_current': True,  # 标记为当前周期
                        }
                    else:
                        # 横盘周期：根据振幅方向判断起始价格和结束价格
                        # 振幅方向由 amplitude_from_current 决定
                        if amplitude_from_current >= 0:
                            # 振幅为正：从低点到高点
                            actual_start_price = min_price_in_current
                            actual_end_price = max_price_in_current
                        else:
                            # 振幅为负：从高点到低点
                            actual_start_price = max_price_in_current
                            actual_end_price = min_price_in_current
                        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
                        current_period_info = {
                            'period_index': period_index,
                            'cycle_type': cycle_type,
                            'cycle_type_desc': cycle_type_desc,
                            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
                            'start_index': int(start_idx),
                            'end_index': int(current_idx),
                            'duration': int(current_idx - start_idx),
                            'high_price': max_price_in_current,
                            'high_time': timestamps[max_idx_in_current] if timestamps and max_idx_in_current < len(timestamps) else None,
                            'low_price': min_price_in_current,
                            'low_time': timestamps[min_idx_in_current] if timestamps and min_idx_in_current < len(timestamps) else None,
                            'amplitude': float(amplitude_corrected),  # 使用正确的振幅计算
                            'is_current': True,  # 标记为当前周期
                        }
                else:  # last_point['type'] == 'peak'
                    # 从高点开始，可能是下跌或横盘，但需要根据实际价格变化判断
                    # 计算基于最新价格的振幅
                    amplitude_from_current = ((current_price - start_price) / start_price) * 100 if start_price > 0 else 0
                    amplitude_abs = abs(amplitude_from_current)
                    
                    # 根据实际价格变化判断周期类型
                    if amplitude_abs < 5.0:
                        cycle_type = 'sideways'
                        cycle_type_desc = '窄幅横盘（进行中）'
                    elif amplitude_abs < 15.0:
                        if (current_idx - start_idx) > 30:
                            cycle_type = 'sideways'
                            cycle_type_desc = '标准横盘（进行中）'
                        else:
                            # 根据实际价格变化方向判断
                            if amplitude_from_current > 0:
                                cycle_type = 'rise'
                                cycle_type_desc = '上涨（进行中）'
                            else:
                                cycle_type = 'decline'
                                cycle_type_desc = '下跌（进行中）'
                    else:
                        # 根据实际价格变化方向判断
                        if amplitude_from_current > 0:
                            cycle_type = 'rise'
                            cycle_type_desc = '上涨（进行中）'
                        else:
                            cycle_type = 'decline'
                            cycle_type_desc = '下跌（进行中）'
                    
                    # 根据周期类型设置起始价格和结束价格，并计算正确的振幅
                    if cycle_type == 'rise':
                        # 上涨周期：起始价格是低点，结束价格是高点
                        actual_start_price = min_price_in_current  # 起始价格是周期内的最低价
                        actual_end_price = max_price_in_current  # 结束价格是周期内的最高价
                        # 振幅 = (结束价格 - 起始价格) / 起始价格 * 100
                        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
                        current_period_info = {
                            'period_index': period_index,
                            'cycle_type': cycle_type,
                            'cycle_type_desc': cycle_type_desc,
                            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
                            'start_index': int(start_idx),
                            'end_index': int(current_idx),
                            'duration': int(current_idx - start_idx),
                            'low_price': actual_start_price,  # 起始价格是周期内的最低价
                            'low_time': timestamps[min_idx_in_current] if timestamps and min_idx_in_current < len(timestamps) else None,
                            'high_price': actual_end_price,  # 结束价格是周期内的最高价
                            'high_time': timestamps[max_idx_in_current] if timestamps and max_idx_in_current < len(timestamps) else None,
                            'amplitude': float(amplitude_corrected),  # 使用正确的振幅计算
                            'is_current': True,  # 标记为当前周期
                        }
                    elif cycle_type == 'decline':
                        # 下跌周期：起始价格是高点，结束价格是低点
                        actual_start_price = start_price  # 从高点开始，起始价格就是高点
                        actual_end_price = min_price_in_current  # 结束价格是周期内的最低价
                        # 振幅 = (结束价格 - 起始价格) / 起始价格 * 100（应该是负数）
                        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
                        current_period_info = {
                            'period_index': period_index,
                            'cycle_type': cycle_type,
                            'cycle_type_desc': cycle_type_desc,
                            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
                            'start_index': int(start_idx),
                            'end_index': int(current_idx),
                            'duration': int(current_idx - start_idx),
                            'high_price': actual_start_price,  # 起始价格是高点
                            'high_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'low_price': actual_end_price,  # 结束价格是周期内的最低价
                            'low_time': timestamps[min_idx_in_current] if timestamps and min_idx_in_current < len(timestamps) else None,
                            'amplitude': float(amplitude_corrected),  # 使用正确的振幅计算
                            'is_current': True,  # 标记为当前周期
                        }
                    else:
                        # 横盘周期：根据振幅方向判断起始价格和结束价格
                        # 振幅方向由 amplitude_from_current 决定
                        if amplitude_from_current >= 0:
                            # 振幅为正：从低点到高点
                            actual_start_price = min_price_in_current
                            actual_end_price = max_price_in_current
                        else:
                            # 振幅为负：从高点到低点
                            actual_start_price = max_price_in_current
                            actual_end_price = min_price_in_current
                        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
                        current_period_info = {
                            'period_index': period_index,
                            'cycle_type': cycle_type,
                            'cycle_type_desc': cycle_type_desc,
                            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
                            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
                            'start_index': int(start_idx),
                            'end_index': int(current_idx),
                            'duration': int(current_idx - start_idx),
                            'high_price': max_price_in_current,
                            'high_time': timestamps[max_idx_in_current] if timestamps and max_idx_in_current < len(timestamps) else None,
                            'low_price': min_price_in_current,
                            'low_time': timestamps[min_idx_in_current] if timestamps and min_idx_in_current < len(timestamps) else None,
                            'amplitude': float(amplitude_corrected),  # 使用正确的振幅计算
                            'is_current': True,  # 标记为当前周期
                        }
                
                cycle_periods.append(current_period_info)
        
        # 保留所有检测到的周期（按时间从旧到新排列）
        result['cycle_periods'] = cycle_periods
    
    if len(peaks) >= 2 and len(troughs) >= 2:
        # 计算高点之间的周期
        peak_periods = np.diff(peaks)
        avg_peak_period = float(np.mean(peak_periods)) if len(peak_periods) > 0 else None
        std_peak_period = float(np.std(peak_periods)) if len(peak_periods) > 1 else None
        
        # 计算低点之间的周期
        trough_periods = np.diff(troughs)
        avg_trough_period = float(np.mean(trough_periods)) if len(trough_periods) > 0 else None
        std_trough_period = float(np.std(trough_periods)) if len(trough_periods) > 1 else None
        
        # 计算完整周期（从低点到低点）
        full_cycles = []
        if len(troughs) >= 2:
            for i in range(len(troughs) - 1):
                cycle_length = troughs[i + 1] - troughs[i]
                full_cycles.append(cycle_length)
        
        result['peak_count'] = len(peaks)
        result['trough_count'] = len(troughs)
        result['avg_peak_period'] = avg_peak_period
        result['avg_trough_period'] = avg_trough_period
        result['std_peak_period'] = std_peak_period
        result['std_trough_period'] = std_trough_period
        
        # 周期一致性（标准差越小，一致性越高）
        if full_cycles:
            avg_cycle = float(np.mean(full_cycles))
            std_cycle = float(np.std(full_cycles))
            result['avg_cycle_length'] = avg_cycle
            result['std_cycle_length'] = std_cycle
            result['cycle_consistency'] = float(1.0 - min(std_cycle / avg_cycle if avg_cycle > 0 else 1.0, 1.0))  # 一致性：0-1
            
            # 周期振幅分析
            cycle_amplitudes = []
            for i in range(len(troughs) - 1):
                start_idx = troughs[i]
                end_idx = troughs[i + 1]
                if end_idx < len(prices):
                    cycle_high = float(np.max(prices[start_idx:end_idx + 1]))
                    cycle_low = float(np.min(prices[start_idx:end_idx + 1]))
                    amplitude = ((cycle_high - cycle_low) / cycle_low) * 100
                    cycle_amplitudes.append(amplitude)
            
            if cycle_amplitudes:
                result['avg_cycle_amplitude'] = float(np.mean(cycle_amplitudes))
                result['max_cycle_amplitude'] = float(np.max(cycle_amplitudes))
                result['min_cycle_amplitude'] = float(np.min(cycle_amplitudes))
        
        # 计算完整周期（从低点到低点或从高点到高点）- 向后兼容
        if avg_peak_period and avg_trough_period:
            avg_cycle = (avg_peak_period + avg_trough_period) / 2
            if 'avg_cycle_length' not in result:
                result['avg_cycle_length'] = float(avg_cycle)
    
    # 2. 自相关分析 - 检测多个周期
    autocorr, lags = calculate_autocorrelation(prices, max_lag=min(100, len(prices) // 2))
    
    if len(autocorr) > 0:
        # 检测主要周期
        dominant_cycle, cycle_strength = detect_cycle_length(autocorr, lags, min_cycle=5, max_cycle=100)
        
        if dominant_cycle:
            result['dominant_cycle'] = dominant_cycle
            result['cycle_strength'] = cycle_strength
        
        # 检测多个周期（短、中、长）
        valid_mask = (lags >= 5) & (lags <= 100)
        if np.any(valid_mask):
            valid_autocorr = autocorr[valid_mask]
            valid_lags = lags[valid_mask]
            
            # 找到所有局部最大值（周期候选）
            from scipy.signal import find_peaks as find_peaks_signal
            peaks_idx, properties = find_peaks_signal(valid_autocorr, height=0.2, distance=5)
            
            if len(peaks_idx) > 0:
                # 按强度排序
                peak_strengths = valid_autocorr[peaks_idx]
                sorted_idx = np.argsort(peak_strengths)[::-1]  # 降序
                
                # 短周期（5-15天）
                short_cycles = [int(valid_lags[peaks_idx[i]]) for i in sorted_idx 
                               if 5 <= valid_lags[peaks_idx[i]] <= 15][:2]
                # 中周期（15-30天）
                medium_cycles = [int(valid_lags[peaks_idx[i]]) for i in sorted_idx 
                                if 15 < valid_lags[peaks_idx[i]] <= 30][:2]
                # 长周期（30-100天）
                long_cycles = [int(valid_lags[peaks_idx[i]]) for i in sorted_idx 
                              if 30 < valid_lags[peaks_idx[i]] <= 100][:2]
                
                if short_cycles:
                    result['short_cycles'] = short_cycles
                    result['short_cycle_strength'] = float(max([valid_autocorr[valid_lags == c][0] for c in short_cycles if len(valid_autocorr[valid_lags == c]) > 0]))
                if medium_cycles:
                    result['medium_cycles'] = medium_cycles
                    result['medium_cycle_strength'] = float(max([valid_autocorr[valid_lags == c][0] for c in medium_cycles if len(valid_autocorr[valid_lags == c]) > 0]))
                if long_cycles:
                    result['long_cycles'] = long_cycles
                    result['long_cycle_strength'] = float(max([valid_autocorr[valid_lags == c][0] for c in long_cycles if len(valid_autocorr[valid_lags == c]) > 0]))
        
        # 计算平均自相关强度（用于评估整体周期性）
        positive_autocorr = autocorr[autocorr > 0]
        if len(positive_autocorr) > 0:
            result['avg_autocorrelation'] = float(np.mean(positive_autocorr))
            result['max_autocorrelation'] = float(np.max(autocorr))
    
    # 3. 使用FFT进行频域分析（检测周期性）
    if len(prices) >= 50:
        try:
            # 去趋势（使用一阶差分）
            price_diff = np.diff(prices)
            
            # FFT分析
            fft_values = fft(price_diff)
            power_spectrum = np.abs(fft_values) ** 2
            
            # 找到主要频率（排除DC分量）
            n = len(power_spectrum)
            freqs = np.fft.fftfreq(n)
            
            # 只考虑正频率部分
            positive_freqs = freqs[1:n//2]
            positive_power = power_spectrum[1:n//2]
            
            if len(positive_power) > 0:
                # 找到功率最大的频率
                max_power_idx = np.argmax(positive_power)
                dominant_freq = positive_freqs[max_power_idx]
                
                # 转换为周期长度
                if dominant_freq > 0:
                    fft_cycle = int(1.0 / dominant_freq)
                    if 5 <= fft_cycle <= 100:
                        result['fft_cycle'] = fft_cycle
                        result['fft_power'] = float(positive_power[max_power_idx] / np.sum(positive_power))
        except Exception:
            # FFT分析失败时忽略
            pass
    
    # 4. 评估周期性的总体强度
    cycle_indicators = []
    if 'cycle_strength' in result:
        cycle_indicators.append(result['cycle_strength'])
    if 'avg_autocorrelation' in result:
        cycle_indicators.append(result['avg_autocorrelation'])
    if 'fft_power' in result:
        cycle_indicators.append(result['fft_power'])
    
    if cycle_indicators:
        overall_strength = float(np.mean(cycle_indicators))
        result['overall_cycle_strength'] = overall_strength
        
        # 判断周期性强度等级
        if overall_strength >= 0.6:
            result['cycle_quality'] = 'strong'
        elif overall_strength >= 0.4:
            result['cycle_quality'] = 'moderate'
        elif overall_strength >= 0.2:
            result['cycle_quality'] = 'weak'
        else:
            result['cycle_quality'] = 'none'
    
    # 5. 当前周期位置分析和预测（基于当前进行中的周期）
    # 优先使用当前周期（从最后一个转折点到最新交易日）来判断阶段
    current_period = None
    if len(cycle_periods) > 0:
        last_period = cycle_periods[-1]
        if last_period.get('is_current', False):
            current_period = last_period
    
    if current_period:
        # 如果有当前周期，使用当前周期的信息判断阶段
        current_cycle_type = current_period.get('cycle_type')
        current_amplitude = current_period.get('amplitude', 0)
        current_duration = current_period.get('duration', 0)
        
        if current_cycle_type == 'sideways':
            # 当前是横盘，阶段信息会在横盘判断中设置
            result['cycle_phase'] = 'sideways'
            result['cycle_phase_desc'] = current_period.get('cycle_type_desc', '横盘阶段')
            result['cycle_suggestion'] = '横盘整理中，等待突破'
        elif current_cycle_type == 'rise':
            # 当前是上涨周期，根据持续时间和振幅判断阶段
            if current_duration <= 5:
                result['cycle_phase'] = 'early_rise'
                result['cycle_phase_desc'] = '周期早期上涨阶段（进行中）'
                result['cycle_suggestion'] = '适合买入，预期还有上涨空间'
            elif current_duration <= 15:
                result['cycle_phase'] = 'mid_rise'
                result['cycle_phase_desc'] = '周期中期上涨阶段（进行中）'
                result['cycle_suggestion'] = '上涨趋势中，注意接近高点'
            else:
                result['cycle_phase'] = 'late_rise'
                result['cycle_phase_desc'] = '周期后期上涨阶段（进行中）'
                result['cycle_suggestion'] = '接近周期高点，注意风险'
            
            result['days_from_last_trough'] = int(current_duration)
        elif current_cycle_type == 'decline':
            # 当前是下跌周期
            result['cycle_phase'] = 'decline'
            result['cycle_phase_desc'] = '周期下跌阶段（进行中）'
            result['cycle_suggestion'] = '下跌趋势中，等待低点'
            result['days_from_last_peak'] = int(current_duration)
        
        # 计算周期位置（如果有周期长度）
        if 'dominant_cycle' in result or 'avg_cycle_length' in result:
            cycle_len = result.get('dominant_cycle') or result.get('avg_cycle_length')
            if cycle_len:
                if current_cycle_type == 'rise':
                    # 上涨周期：周期位置 = 当前天数 / 预期周期长度
                    expected_cycle_length = cycle_len * 0.5  # 上涨周期通常是完整周期的一半
                    cycle_position = current_duration / expected_cycle_length if expected_cycle_length > 0 else 0
                    cycle_position = min(1.0, max(0.0, cycle_position))
                    result['cycle_position'] = float(cycle_position)
                    result['days_to_next_peak'] = max(0, int(expected_cycle_length - current_duration))
                    result['days_to_next_trough'] = max(0, int(cycle_len - current_duration))
                    result['next_turn_type'] = 'peak'
                    result['next_turn_days'] = result['days_to_next_peak']
                elif current_cycle_type == 'decline':
                    # 下跌周期：周期位置 = 0.5 + (当前天数 / 预期周期长度)
                    expected_cycle_length = cycle_len * 0.5
                    cycle_position = 0.5 + (current_duration / expected_cycle_length) if expected_cycle_length > 0 else 0.5
                    cycle_position = min(1.0, max(0.5, cycle_position))
                    result['cycle_position'] = float(cycle_position)
                    result['days_to_next_trough'] = max(0, int(expected_cycle_length - current_duration))
                    result['days_to_next_peak'] = max(0, int(cycle_len - current_duration))
                    result['next_turn_type'] = 'trough'
                    result['next_turn_days'] = result['days_to_next_trough']
                else:
                    # 横盘周期
                    result['cycle_position'] = 0.0
                    result['days_to_next_peak'] = max(0, int(cycle_len * 0.5 - current_duration))
                    result['days_to_next_trough'] = max(0, int(cycle_len - current_duration))
                    result['next_turn_type'] = 'peak'
                    result['next_turn_days'] = result['days_to_next_peak']
                
                result['next_turn_desc'] = f'预计{result["next_turn_days"]}天后到达下一个{"高点" if result["next_turn_type"] == "peak" else "低点"}'
    elif 'dominant_cycle' in result or 'avg_cycle_length' in result:
        # 如果没有当前周期，使用传统方法判断（基于最近转折点）
        cycle_len = result.get('dominant_cycle') or result.get('avg_cycle_length')
        if cycle_len and len(troughs) >= 1:
            # 计算距离最近低点的周期位置
            last_trough_idx = troughs[-1]
            current_position = len(prices) - 1 - last_trough_idx
            cycle_position = (current_position % int(cycle_len)) / cycle_len
            
            result['cycle_position'] = float(cycle_position)
            result['days_from_last_trough'] = int(current_position)
            result['days_to_next_peak'] = int(cycle_len * 0.5 - current_position) if cycle_position < 0.5 else int(cycle_len * (1.5 - cycle_position))
            result['days_to_next_trough'] = int(cycle_len - current_position)
            
            # 判断当前处于周期的哪个阶段（更详细的描述）
            if cycle_position < 0.25:
                result['cycle_phase'] = 'early_rise'
                result['cycle_phase_desc'] = '周期早期上涨阶段'
                result['cycle_suggestion'] = '适合买入，预期还有上涨空间'
            elif cycle_position < 0.5:
                result['cycle_phase'] = 'mid_rise'
                result['cycle_phase_desc'] = '周期中期上涨阶段'
                result['cycle_suggestion'] = '上涨趋势中，注意接近高点'
            elif cycle_position < 0.75:
                result['cycle_phase'] = 'late_rise'
                result['cycle_phase_desc'] = '周期后期上涨阶段'
                result['cycle_suggestion'] = '接近周期高点，注意风险'
            else:
                result['cycle_phase'] = 'decline'
                result['cycle_phase_desc'] = '周期下跌阶段'
                result['cycle_suggestion'] = '下跌趋势中，等待低点'
            
            # 预测下一个转折点
            if cycle_position < 0.5:
                # 下一个是高点
                next_turn_type = 'peak'
                next_turn_days = result['days_to_next_peak']
            else:
                # 下一个是低点
                next_turn_type = 'trough'
                next_turn_days = result['days_to_next_trough']
            
            result['next_turn_type'] = next_turn_type
            result['next_turn_days'] = next_turn_days
            result['next_turn_desc'] = f'预计{next_turn_days}天后到达下一个{"高点" if next_turn_type == "peak" else "低点"}'
    
    # 6. 周期稳定性评估
    if 'cycle_consistency' in result:
        consistency = result['cycle_consistency']
        if consistency >= 0.7:
            result['cycle_stability'] = 'high'
            result['cycle_stability_desc'] = '周期非常稳定，规律性强'
        elif consistency >= 0.5:
            result['cycle_stability'] = 'medium'
            result['cycle_stability_desc'] = '周期较为稳定'
        elif consistency >= 0.3:
            result['cycle_stability'] = 'low'
            result['cycle_stability_desc'] = '周期不够稳定，规律性较弱'
        else:
            result['cycle_stability'] = 'very_low'
            result['cycle_stability_desc'] = '周期不稳定，无明显规律'
    
    # 6.5. 整体横盘判断（结合多个技术指标）
    # 使用ADX、均线缠绕、20日振幅统计等指标综合判断
    is_sideways = False
    sideways_strength = 0.0
    sideways_reasons = []
    
    # 计算最近20个交易日的振幅统计
    lookback_20 = min(20, len(prices))
    if lookback_20 >= 20:
        recent_20_prices = prices[-lookback_20:]
        recent_20_highs = highs[-lookback_20:] if len(highs) >= lookback_20 else recent_20_prices
        recent_20_lows = lows[-lookback_20:] if len(lows) >= lookback_20 else recent_20_prices
        
        # 20日平均最高价与最低价之差
        avg_high_20 = np.mean(recent_20_highs)
        avg_low_20 = np.mean(recent_20_lows)
        avg_price_20 = np.mean(recent_20_prices)
        amplitude_20 = ((avg_high_20 - avg_low_20) / avg_price_20) * 100 if avg_price_20 > 0 else 0
        
        # 条件1：20日振幅统计小于10%（标准横盘特征）
        condition1 = amplitude_20 < 10.0
        
        # 条件2：计算均线缠绕（如果均线相互缠绕，可能是横盘）
        # 简化版：计算短期和长期均线的差异
        if len(prices) >= 60:
            ma5 = np.mean(prices[-5:])
            ma10 = np.mean(prices[-10:])
            ma20 = np.mean(prices[-20:])
            ma60 = np.mean(prices[-60:]) if len(prices) >= 60 else ma20
            
            # 均线缠绕：各均线之间的差异小于5%
            ma_diff_5_10 = abs(ma5 - ma10) / avg_price_20 * 100 if avg_price_20 > 0 else 0
            ma_diff_10_20 = abs(ma10 - ma20) / avg_price_20 * 100 if avg_price_20 > 0 else 0
            ma_diff_20_60 = abs(ma20 - ma60) / avg_price_20 * 100 if avg_price_20 > 0 else 0
            
            condition2 = ma_diff_5_10 < 2.0 and ma_diff_10_20 < 3.0 and ma_diff_20_60 < 5.0
        else:
            condition2 = False
        
        # 条件3：计算ADX（如果可用，ADX < 25表示无趋势）
        # 这里简化计算ADX，或者从外部传入
        # 暂时使用价格变化率作为趋势强度的替代
        price_change_20 = ((recent_20_prices[-1] - recent_20_prices[0]) / recent_20_prices[0]) * 100 if recent_20_prices[0] > 0 else 0
        condition3 = abs(price_change_20) < 5.0  # 20日价格变化小于5%
        
        # 条件4：价格波动范围适中（3%-25%）
        price_range_20 = (np.max(recent_20_highs) - np.min(recent_20_lows)) / avg_price_20 * 100 if avg_price_20 > 0 else 0
        condition4 = 3.0 <= price_range_20 <= 25.0
        
        # 条件5：结合周期特征（如果上涨和下跌周期振幅相近）
        cycle_sideways_score = 0.0
        if len(cycle_periods) >= 4:
            rise_amplitudes = []
            decline_amplitudes = []
            for p in cycle_periods:
                if p.get('cycle_type') == 'rise':
                    start_price = p.get('low_price', 0)
                    end_price = p.get('high_price', 0)
                    if start_price > 0:
                        amp = ((end_price - start_price) / start_price) * 100
                        rise_amplitudes.append(amp)
                elif p.get('cycle_type') == 'decline':
                    start_price = p.get('high_price', 0)
                    end_price = p.get('low_price', 0)
                    if start_price > 0:
                        amp = abs(((end_price - start_price) / start_price) * 100)
                        decline_amplitudes.append(amp)
            
            if len(rise_amplitudes) > 0 and len(decline_amplitudes) > 0:
                avg_rise_amp = np.mean(rise_amplitudes)
                avg_decline_amp = np.mean(decline_amplitudes)
                if avg_rise_amp > 0 and avg_decline_amp > 0:
                    amp_diff_ratio = abs(avg_rise_amp - avg_decline_amp) / max(avg_rise_amp, avg_decline_amp)
                    if amp_diff_ratio < 0.3:
                        cycle_sideways_score = 1.0 - amp_diff_ratio
                        condition5 = cycle_sideways_score > 0.5
                    else:
                        condition5 = False
                else:
                    condition5 = False
            else:
                condition5 = False
        else:
            condition5 = False
        
        # 计算横盘强度
        conditions_met = sum([condition1, condition2, condition3, condition4, condition5])
        base_strength = conditions_met / 5.0
        sideways_strength = min(1.0, base_strength * 0.7 + cycle_sideways_score * 0.3)
        
        # 判断为横盘：至少满足3个条件，或者满足条件1+条件3（20日振幅小且价格变化小）
        if conditions_met >= 3 or (condition1 and condition3):
            is_sideways = True
            if condition1:
                sideways_reasons.append(f'20日振幅{amplitude_20:.1f}%')
            if condition2:
                sideways_reasons.append('均线缠绕')
            if condition3:
                sideways_reasons.append(f'20日价格变化{abs(price_change_20):.1f}%')
            if condition4:
                sideways_reasons.append(f'波动范围{price_range_20:.1f}%')
            if condition5:
                sideways_reasons.append('周期振幅相近')
        
        result['sideways_market'] = is_sideways
        result['sideways_strength'] = float(sideways_strength)
        result['sideways_price_range_pct'] = float(price_range_20)
        result['sideways_price_change_pct'] = float(price_change_20)
        result['sideways_amplitude_20'] = float(amplitude_20)
        if is_sideways:
            result['sideways_reasons'] = sideways_reasons
    
    # 7. 综合周期分析总结
    summary_parts = []
    if 'dominant_cycle' in result:
        summary_parts.append(f"主要周期{result['dominant_cycle']}天")
    if 'cycle_quality' in result:
        quality_map = {'strong': '强', 'moderate': '中等', 'weak': '弱', 'none': '无'}
        summary_parts.append(f"质量{quality_map.get(result['cycle_quality'], '未知')}")
    if 'sideways_market' in result and result['sideways_market']:
        summary_parts.append('横盘')
    if 'cycle_phase_desc' in result:
        summary_parts.append(result['cycle_phase_desc'])
    if summary_parts:
        result['cycle_summary'] = ' | '.join(summary_parts)
    
    return result


def calculate_cycle_analysis(closes, highs, lows, timestamps=None):
    """
    计算周期分析指标
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        timestamps: 时间戳数组（可选）
    
    返回:
        dict: 包含周期分析结果的字典
    """
    if len(closes) < 30:
        return {}
    
    return analyze_cycle_pattern(closes, highs, lows, timestamps)

