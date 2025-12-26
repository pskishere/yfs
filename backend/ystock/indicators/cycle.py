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


def detect_cycle_length(autocorr, lags, min_cycle=10, max_cycle=100):
    """
    从自相关函数中检测主要周期长度
    改进版：排除短期噪声，寻找更显著的周期
    
    参数:
        autocorr: 自相关值数组
        lags: 滞后周期数组
        min_cycle: 最小周期长度（提高以避免短期噪声）
        max_cycle: 最大周期长度
    
    返回:
        dominant_cycle: 主要周期长度（如果检测到）
        cycle_strength: 周期强度（0-1）
    """
    if len(autocorr) == 0 or len(lags) == 0:
        return None, 0.0
    
    # 过滤有效范围（排除太短的周期，避免噪声）
    valid_mask = (lags >= min_cycle) & (lags <= max_cycle)
    if not np.any(valid_mask):
        return None, 0.0
    
    valid_autocorr = autocorr[valid_mask]
    valid_lags = lags[valid_mask]
    
    # 使用find_peaks找到所有局部最大值，而不是简单地找全局最大值
    # 这样可以避免短期噪声干扰
    from scipy.signal import find_peaks as find_peaks_signal
    
    # 寻找所有峰值，要求最小高度和最小距离
    peaks_idx, properties = find_peaks_signal(
        valid_autocorr, 
        height=0.2,  # 最小自相关值
        distance=max(5, min_cycle // 3)  # 峰值之间的最小距离
    )
    
    if len(peaks_idx) == 0:
        # 如果没有找到峰值，回退到全局最大值
        max_idx = np.argmax(valid_autocorr)
        dominant_cycle = int(valid_lags[max_idx])
        cycle_strength = float(valid_autocorr[max_idx])
    else:
        # 从所有峰值中选择强度最高的
        peak_strengths = valid_autocorr[peaks_idx]
        max_peak_idx = np.argmax(peak_strengths)
        best_peak_idx = peaks_idx[max_peak_idx]
        dominant_cycle = int(valid_lags[best_peak_idx])
        cycle_strength = float(valid_autocorr[best_peak_idx])
    
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
                cycle_type = 'rise'
                cycle_type_desc = '上涨'
                start_price = float(prices[start_idx])
                end_price = float(prices[end_idx])
                
                # 周期内的价格范围
                period_prices = prices[start_idx:end_idx + 1]
                period_high_values = highs[start_idx:end_idx + 1] if start_idx < len(highs) else period_prices
                
                # 找到周期内的最高价
                max_price_in_period = float(np.max(period_high_values))
                max_idx = start_idx + int(np.argmax(period_high_values))
                
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
                }
                cycle_periods.append(period_info)
                period_index += 1
                
            elif start_point['type'] == 'peak' and end_point['type'] == 'trough':
                # 下跌周期：从高点到低点
                cycle_type = 'decline'
                cycle_type_desc = '下跌'
                start_price = float(prices[start_idx])
                end_price = float(prices[end_idx])
                
                # 周期内的价格范围
                period_prices = prices[start_idx:end_idx + 1]
                period_low_values = lows[start_idx:end_idx + 1] if start_idx < len(lows) else period_prices
                
                # 找到周期内的最低价
                min_price_in_period = float(np.min(period_low_values))
                min_idx = start_idx + int(np.argmin(period_low_values))
                
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
                }
                cycle_periods.append(period_info)
                period_index += 1
        
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
        # 检测主要周期（提高最小周期以避免短期噪声）
        dominant_cycle, cycle_strength = detect_cycle_length(autocorr, lags, min_cycle=10, max_cycle=100)
        
        # 优先使用实际检测到的平均周期长度作为主要周期
        # 因为实际的高低点周期比自相关分析更准确和直观
        if 'avg_cycle_length' in result and result['avg_cycle_length']:
            # 使用实际检测到的周期
            result['dominant_cycle'] = int(result['avg_cycle_length'])
            # 如果自相关也检测到周期且强度较高，使用自相关的强度
            # 否则使用基于周期一致性的强度
            if dominant_cycle and cycle_strength > 0.4:
                result['cycle_strength'] = cycle_strength
            elif 'cycle_consistency' in result:
                result['cycle_strength'] = result['cycle_consistency']
            else:
                result['cycle_strength'] = 0.5  # 默认中等强度
        elif dominant_cycle:
            # 没有实际周期数据，使用自相关检测的结果
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
    
    # 5. 当前周期位置分析和预测
    if 'dominant_cycle' in result or 'avg_cycle_length' in result:
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
    
    # 7. 综合周期分析总结
    summary_parts = []
    if 'dominant_cycle' in result:
        summary_parts.append(f"主要周期{result['dominant_cycle']}天")
    if 'cycle_quality' in result:
        quality_map = {'strong': '强', 'moderate': '中等', 'weak': '弱', 'none': '无'}
        summary_parts.append(f"质量{quality_map.get(result['cycle_quality'], '未知')}")
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

