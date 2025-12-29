# -*- coding: utf-8 -*-
"""
周期分析 - 重构版本
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import signal
from scipy.fft import fft


@dataclass
class CycleConfig:
    """周期分析配置参数"""
    min_prominence_pct: float = 0.02  # 最小突出度百分比
    min_period_days: int = 10  # 最小周期天数
    max_data_days: int = 756  # 最大数据天数（3年）
    sideways_narrow_threshold: float = 5.0  # 窄幅横盘阈值
    sideways_standard_threshold: float = 15.0  # 标准横盘阈值
    sideways_wide_threshold: float = 25.0  # 宽幅震荡阈值
    min_cycle_strength: float = 0.3  # 最小周期强度
    sideways_price_change_threshold: float = 5.0  # 横盘价格变化阈值
    sideways_amplitude_threshold: float = 10.0  # 横盘振幅阈值


@dataclass
class TurningPoint:
    """转折点数据"""
    index: int
    point_type: str  # 'peak' or 'trough'
    price: float


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
    
    if min_prominence is None:
        avg_price = np.mean(prices)
        min_prominence = avg_price * 0.03
    
    peaks, _ = signal.find_peaks(prices, distance=min_period, prominence=min_prominence)
    troughs, _ = signal.find_peaks(-prices, distance=min_period, prominence=min_prominence)
    
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
        max_lag = min(n // 2, 100)
    
    prices_normalized = prices - np.mean(prices)
    autocorr = []
    lags = []
    
    for lag in range(1, max_lag + 1):
        if lag >= n:
            break
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
    
    valid_mask = (lags >= min_cycle) & (lags <= max_cycle)
    if not np.any(valid_mask):
        return None, 0.0
    
    valid_autocorr = autocorr[valid_mask]
    valid_lags = lags[valid_mask]
    
    max_idx = np.argmax(valid_autocorr)
    dominant_cycle = int(valid_lags[max_idx])
    cycle_strength = float(valid_autocorr[max_idx])
    
    if cycle_strength < 0.3:
        return None, 0.0
    
    return dominant_cycle, cycle_strength


def _convert_turning_points(peaks: List[int], troughs: List[int], prices: np.ndarray) -> List[TurningPoint]:
    """
    将峰谷索引转换为转折点列表
    
    参数:
        peaks: 高点索引列表
        troughs: 低点索引列表
        prices: 价格数组
    
    返回:
        转折点列表，按索引排序
    """
    turning_points = []
    for peak_idx in peaks:
        turning_points.append(TurningPoint(
            index=peak_idx,
            point_type='peak',
            price=float(prices[peak_idx])
        ))
    for trough_idx in troughs:
        turning_points.append(TurningPoint(
            index=trough_idx,
            point_type='trough',
            price=float(prices[trough_idx])
        ))
    turning_points.sort(key=lambda x: x.index)
    return turning_points


def _classify_cycle_type(amplitude: float, duration: int, config: CycleConfig) -> Tuple[str, str]:
    """
    根据振幅和持续时间判断周期类型
    
    参数:
        amplitude: 周期振幅（百分比）
        duration: 持续时间（天数）
        config: 配置参数
    
    返回:
        (cycle_type, cycle_type_desc)
    """
    amplitude_abs = abs(amplitude)
    
    if amplitude_abs < config.sideways_narrow_threshold:
        return 'sideways', '窄幅横盘'
    elif amplitude_abs < config.sideways_standard_threshold:
        if duration > 30:
            return 'sideways', '标准横盘'
        else:
            if amplitude > 0:
                return 'rise', '上涨'
            else:
                return 'decline', '下跌'
    else:
        if amplitude > 0:
            return 'rise', '上涨'
        else:
            return 'decline', '下跌'


def _build_cycle_periods_from_turning_points(turning_points: List[TurningPoint], 
                                             prices: np.ndarray, 
                                             highs: np.ndarray, 
                                             lows: np.ndarray,
                                             timestamps: Optional[List],
                                             config: CycleConfig) -> List[Dict[str, Any]]:
    """
    从转折点构建周期列表
    
    参数:
        turning_points: 转折点列表
        prices: 价格数组
        highs: 最高价数组
        lows: 最低价数组
        timestamps: 时间戳列表
        config: 配置参数
    
    返回:
        周期列表
    """
    cycle_periods = []
    period_index = 1
    
    for i in range(len(turning_points) - 1):
        start_point = turning_points[i]
        end_point = turning_points[i + 1]
        
        start_idx = start_point.index
        end_idx = end_point.index
        
        if end_idx <= start_idx:
            continue
        
        # 上涨周期：从低点到高点
        if start_point.point_type == 'trough' and end_point.point_type == 'peak':
            start_price = float(prices[start_idx])
            period_high_values = highs[start_idx:end_idx + 1] if start_idx < len(highs) else prices[start_idx:end_idx + 1]
            
            max_price_in_period = float(np.max(period_high_values))
            max_idx = start_idx + int(np.argmax(period_high_values))
            amplitude = ((max_price_in_period - start_price) / start_price) * 100 if start_price > 0 else 0
            
            cycle_type, cycle_type_desc = _classify_cycle_type(amplitude, max_idx - start_idx, config)
            
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
            
        # 下跌周期：从高点到低点
        elif start_point.point_type == 'peak' and end_point.point_type == 'trough':
            start_price = float(prices[start_idx])
            period_low_values = lows[start_idx:end_idx + 1] if start_idx < len(lows) else prices[start_idx:end_idx + 1]
            
            min_price_in_period = float(np.min(period_low_values))
            min_idx = start_idx + int(np.argmin(period_low_values))
            amplitude = ((min_price_in_period - start_price) / start_price) * 100 if start_price > 0 else 0
            
            cycle_type, cycle_type_desc = _classify_cycle_type(amplitude, min_idx - start_idx, config)
            
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
    
    return cycle_periods


def _calculate_current_cycle(turning_points: List[TurningPoint],
                            prices: np.ndarray,
                            highs: np.ndarray,
                            lows: np.ndarray,
                            timestamps: Optional[List],
                            period_index: int,
                            config: CycleConfig) -> Optional[Dict[str, Any]]:
    """
    计算当前周期（从最后一个转折点到最新交易日）
    
    参数:
        turning_points: 转折点列表
        prices: 价格数组
        highs: 最高价数组
        lows: 最低价数组
        timestamps: 时间戳列表
        period_index: 周期索引
        config: 配置参数
    
    返回:
        当前周期信息字典，如果无法计算则返回None
    """
    if not turning_points:
        return None
    
    last_point = turning_points[-1]
    last_idx = last_point.index
    current_idx = len(prices) - 1
    
    if last_idx >= current_idx:
        return None
    
    start_idx = last_idx
    start_price = float(prices[start_idx])
    current_price = float(prices[current_idx])
    
    current_period_highs = highs[start_idx:current_idx + 1] if start_idx < len(highs) else prices[start_idx:current_idx + 1]
    current_period_lows = lows[start_idx:current_idx + 1] if start_idx < len(lows) else prices[start_idx:current_idx + 1]
    
    max_price_in_current = float(np.max(current_period_highs))
    min_price_in_current = float(np.min(current_period_lows))
    max_idx_in_current = start_idx + int(np.argmax(current_period_highs))
    min_idx_in_current = start_idx + int(np.argmin(current_period_lows))
    
    amplitude_from_current = ((current_price - start_price) / start_price) * 100 if start_price > 0 else 0
    amplitude_abs = abs(amplitude_from_current)
    
    # 判断周期类型
    if amplitude_abs < config.sideways_narrow_threshold:
        cycle_type = 'sideways'
        cycle_type_desc = '窄幅横盘（进行中）'
    elif amplitude_abs < config.sideways_standard_threshold:
        if (current_idx - start_idx) > 30:
            cycle_type = 'sideways'
            cycle_type_desc = '标准横盘（进行中）'
        else:
            if amplitude_from_current > 0:
                cycle_type = 'rise'
                cycle_type_desc = '上涨（进行中）'
            else:
                cycle_type = 'decline'
                cycle_type_desc = '下跌（进行中）'
    else:
        if amplitude_from_current > 0:
            cycle_type = 'rise'
            cycle_type_desc = '上涨（进行中）'
        else:
            cycle_type = 'decline'
            cycle_type_desc = '下跌（进行中）'
    
    # 根据周期类型设置起始价格和结束价格
    if cycle_type == 'rise':
        actual_start_price = start_price if last_point.point_type == 'trough' else min_price_in_current
        actual_end_price = max_price_in_current
        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
        
        return {
            'period_index': period_index,
            'cycle_type': cycle_type,
            'cycle_type_desc': cycle_type_desc,
            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
            'start_index': int(start_idx),
            'end_index': int(current_idx),
            'duration': int(current_idx - start_idx),
            'low_price': actual_start_price,
            'low_time': timestamps[start_idx if last_point.point_type == 'trough' else min_idx_in_current] if timestamps else None,
            'high_price': actual_end_price,
            'high_time': timestamps[max_idx_in_current] if timestamps and max_idx_in_current < len(timestamps) else None,
            'amplitude': float(amplitude_corrected),
            'is_current': True,
        }
    elif cycle_type == 'decline':
        actual_start_price = start_price if last_point.point_type == 'peak' else max_price_in_current
        actual_end_price = min_price_in_current
        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
        
        return {
            'period_index': period_index,
            'cycle_type': cycle_type,
            'cycle_type_desc': cycle_type_desc,
            'start_time': timestamps[start_idx] if timestamps and start_idx < len(timestamps) else None,
            'end_time': timestamps[current_idx] if timestamps and current_idx < len(timestamps) else None,
            'start_index': int(start_idx),
            'end_index': int(current_idx),
            'duration': int(current_idx - start_idx),
            'high_price': actual_start_price,
            'high_time': timestamps[start_idx if last_point.point_type == 'peak' else max_idx_in_current] if timestamps else None,
            'low_price': actual_end_price,
            'low_time': timestamps[min_idx_in_current] if timestamps and min_idx_in_current < len(timestamps) else None,
            'amplitude': float(amplitude_corrected),
            'is_current': True,
        }
    else:  # sideways
        if amplitude_from_current >= 0:
            actual_start_price = min_price_in_current
            actual_end_price = max_price_in_current
        else:
            actual_start_price = max_price_in_current
            actual_end_price = min_price_in_current
        amplitude_corrected = ((actual_end_price - actual_start_price) / actual_start_price) * 100 if actual_start_price > 0 else 0
        
        return {
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
            'amplitude': float(amplitude_corrected),
            'is_current': True,
        }


def _detect_sideways_market(prices: np.ndarray,
                           highs: np.ndarray,
                           lows: np.ndarray,
                           cycle_periods: List[Dict[str, Any]],
                           config: CycleConfig) -> Dict[str, Any]:
    """
    检测横盘市场
    
    参数:
        prices: 价格数组
        highs: 最高价数组
        lows: 最低价数组
        cycle_periods: 周期列表
        config: 配置参数
    
    返回:
        横盘检测结果字典
    """
    result = {}
    lookback_20 = min(20, len(prices))
    
    if lookback_20 < 20:
        return result
    
    recent_20_prices = prices[-lookback_20:]
    recent_20_highs = highs[-lookback_20:] if len(highs) >= lookback_20 else recent_20_prices
    recent_20_lows = lows[-lookback_20:] if len(lows) >= lookback_20 else recent_20_prices
    
    avg_high_20 = float(np.mean(recent_20_highs))
    avg_low_20 = float(np.mean(recent_20_lows))
    avg_price_20 = float(np.mean(recent_20_prices))
    amplitude_20 = float(((avg_high_20 - avg_low_20) / avg_price_20) * 100 if avg_price_20 > 0 else 0)
    
    # 条件1：20日振幅统计小于阈值
    condition1 = bool(float(amplitude_20) < config.sideways_amplitude_threshold)
    
    # 条件2：均线缠绕
    condition2 = False
    if len(prices) >= 60:
        ma5 = float(np.mean(prices[-5:]))
        ma10 = float(np.mean(prices[-10:]))
        ma20 = float(np.mean(prices[-20:]))
        ma60 = float(np.mean(prices[-60:]))
        
        ma_diff_5_10 = abs(ma5 - ma10) / avg_price_20 * 100 if avg_price_20 > 0 else 0
        ma_diff_10_20 = abs(ma10 - ma20) / avg_price_20 * 100 if avg_price_20 > 0 else 0
        ma_diff_20_60 = abs(ma20 - ma60) / avg_price_20 * 100 if avg_price_20 > 0 else 0
        
        condition2 = bool(ma_diff_5_10 < 2.0 and ma_diff_10_20 < 3.0 and ma_diff_20_60 < 5.0)
    
    # 条件3：价格变化小于阈值
    price_change_20 = float(((recent_20_prices[-1] - recent_20_prices[0]) / recent_20_prices[0]) * 100 if recent_20_prices[0] > 0 else 0)
    condition3 = bool(abs(price_change_20) < config.sideways_price_change_threshold)
    
    # 条件4：价格波动范围适中
    price_range_20 = float((np.max(recent_20_highs) - np.min(recent_20_lows)) / avg_price_20 * 100 if avg_price_20 > 0 else 0)
    condition4 = bool(3.0 <= price_range_20 <= config.sideways_wide_threshold)
    
    # 条件5：周期振幅相近
    cycle_sideways_score = 0.0
    condition5 = False
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
            avg_rise_amp = float(np.mean(rise_amplitudes))
            avg_decline_amp = float(np.mean(decline_amplitudes))
            if avg_rise_amp > 0 and avg_decline_amp > 0:
                amp_diff_ratio = abs(avg_rise_amp - avg_decline_amp) / max(avg_rise_amp, avg_decline_amp)
                if amp_diff_ratio < 0.3:
                    cycle_sideways_score = float(1.0 - amp_diff_ratio)
                    condition5 = bool(cycle_sideways_score > 0.5)
    
    # 计算横盘强度
    conditions_met = int(sum([condition1, condition2, condition3, condition4, condition5]))
    base_strength = float(conditions_met / 5.0)
    sideways_strength = float(min(1.0, base_strength * 0.7 + cycle_sideways_score * 0.3))
    
    # 判断为横盘（确保返回Python原生bool）
    is_sideways = bool(conditions_met >= 3 or (condition1 and condition3))
    sideways_reasons = []
    if is_sideways:
        if condition1:
            sideways_reasons.append(f'20日振幅{float(amplitude_20):.1f}%')
        if condition2:
            sideways_reasons.append('均线缠绕')
        if condition3:
            sideways_reasons.append(f'20日价格变化{abs(price_change_20):.1f}%')
        if condition4:
            sideways_reasons.append(f'波动范围{price_range_20:.1f}%')
        if condition5:
            sideways_reasons.append('周期振幅相近')
    
    result['sideways_market'] = bool(is_sideways)
    result['sideways_strength'] = float(sideways_strength)
    result['sideways_price_range_pct'] = float(price_range_20)
    result['sideways_price_change_pct'] = float(price_change_20)
    result['sideways_amplitude_20'] = float(amplitude_20)
    if is_sideways:
        result['sideways_reasons'] = sideways_reasons
    
    return result


def analyze_cycle_pattern(prices, highs, lows, timestamps=None):
    """
    分析价格周期模式 - 重构版本
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
    config = CycleConfig()
    
    if len(prices) < 30:
        return result
    
    # 限制数据范围到最近3年
    actual_days = len(prices)
    if actual_days > config.max_data_days:
        prices = prices[-config.max_data_days:]
        highs = highs[-config.max_data_days:]
        lows = lows[-config.max_data_days:]
        if timestamps:
            timestamps = timestamps[-config.max_data_days:]
        result['data_range_note'] = f'基于最近3年数据（{config.max_data_days}个交易日）'
    else:
        result['data_range_note'] = f'基于全部可用数据（{actual_days}个交易日，约{actual_days/252:.1f}年）'
    
    # 1. 识别高点和低点
    price_std = np.std(prices)
    avg_price = np.mean(prices)
    min_prominence_abs = max(price_std * 0.08, avg_price * config.min_prominence_pct)
    
    peaks, troughs = find_peaks_and_troughs(prices, min_period=config.min_period_days, min_prominence=min_prominence_abs)
    
    result['filter_params'] = {
        'min_period': config.min_period_days,
        'min_prominence_pct': float((min_prominence_abs / avg_price) * 100),
        'filtered_peaks': len(peaks),
        'filtered_troughs': len(troughs),
    }
    
    # 2. 构建周期列表
    turning_points = _convert_turning_points(peaks, troughs, prices)
    cycle_periods = []
    
    if len(turning_points) >= 2:
        cycle_periods = _build_cycle_periods_from_turning_points(
            turning_points, prices, highs, lows, timestamps, config
        )
        
        # 添加当前周期
        if turning_points:
            current_cycle = _calculate_current_cycle(
                turning_points, prices, highs, lows, timestamps, 
                len(cycle_periods) + 1, config
            )
            if current_cycle:
                cycle_periods.append(current_cycle)
        
        result['cycle_periods'] = cycle_periods
    
    # 3. 计算周期统计
    if len(peaks) >= 2 and len(troughs) >= 2:
        peak_periods = np.diff(peaks)
        trough_periods = np.diff(troughs)
        
        result['peak_count'] = len(peaks)
        result['trough_count'] = len(troughs)
        result['avg_peak_period'] = float(np.mean(peak_periods)) if len(peak_periods) > 0 else None
        result['avg_trough_period'] = float(np.mean(trough_periods)) if len(trough_periods) > 0 else None
        result['std_peak_period'] = float(np.std(peak_periods)) if len(peak_periods) > 1 else None
        result['std_trough_period'] = float(np.std(trough_periods)) if len(trough_periods) > 1 else None
        
        # 完整周期分析
        if len(troughs) >= 2:
            full_cycles = []
            cycle_amplitudes = []
            for i in range(len(troughs) - 1):
                cycle_length = troughs[i + 1] - troughs[i]
                full_cycles.append(cycle_length)
                
                start_idx = troughs[i]
                end_idx = troughs[i + 1]
                if end_idx < len(prices):
                    cycle_high = float(np.max(prices[start_idx:end_idx + 1]))
                    cycle_low = float(np.min(prices[start_idx:end_idx + 1]))
                    amplitude = ((cycle_high - cycle_low) / cycle_low) * 100
                    cycle_amplitudes.append(amplitude)
            
            if full_cycles:
                avg_cycle = float(np.mean(full_cycles))
                std_cycle = float(np.std(full_cycles))
                result['avg_cycle_length'] = avg_cycle
                result['std_cycle_length'] = std_cycle
                result['cycle_consistency'] = float(1.0 - min(std_cycle / avg_cycle if avg_cycle > 0 else 1.0, 1.0))
            
            if cycle_amplitudes:
                result['avg_cycle_amplitude'] = float(np.mean(cycle_amplitudes))
                result['max_cycle_amplitude'] = float(np.max(cycle_amplitudes))
                result['min_cycle_amplitude'] = float(np.min(cycle_amplitudes))
    
    # 4. 自相关分析
    autocorr, lags = calculate_autocorrelation(prices, max_lag=min(100, len(prices) // 2))
    
    if len(autocorr) > 0:
        dominant_cycle, cycle_strength = detect_cycle_length(autocorr, lags, min_cycle=5, max_cycle=100)
        
        if dominant_cycle:
            result['dominant_cycle'] = dominant_cycle
            result['cycle_strength'] = cycle_strength
        
        # 检测多个周期
        valid_mask = (lags >= 5) & (lags <= 100)
        if np.any(valid_mask):
            valid_autocorr = autocorr[valid_mask]
            valid_lags = lags[valid_mask]
            
            from scipy.signal import find_peaks as find_peaks_signal
            peaks_idx, _ = find_peaks_signal(valid_autocorr, height=0.2, distance=5)
            
            if len(peaks_idx) > 0:
                peak_strengths = valid_autocorr[peaks_idx]
                sorted_idx = np.argsort(peak_strengths)[::-1]
                
                short_cycles = [int(valid_lags[peaks_idx[i]]) for i in sorted_idx 
                               if 5 <= valid_lags[peaks_idx[i]] <= 15][:2]
                medium_cycles = [int(valid_lags[peaks_idx[i]]) for i in sorted_idx 
                                if 15 < valid_lags[peaks_idx[i]] <= 30][:2]
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
        
        positive_autocorr = autocorr[autocorr > 0]
        if len(positive_autocorr) > 0:
            result['avg_autocorrelation'] = float(np.mean(positive_autocorr))
            result['max_autocorrelation'] = float(np.max(autocorr))
    
    # 5. FFT频域分析
    if len(prices) >= 50:
        try:
            price_diff = np.diff(prices)
            fft_values = fft(price_diff)
            power_spectrum = np.abs(fft_values) ** 2
            
            n = len(power_spectrum)
            freqs = np.fft.fftfreq(n)
            
            positive_freqs = freqs[1:n//2]
            positive_power = power_spectrum[1:n//2]
            
            if len(positive_power) > 0:
                max_power_idx = np.argmax(positive_power)
                dominant_freq = positive_freqs[max_power_idx]
                
                if dominant_freq > 0:
                    fft_cycle = int(1.0 / dominant_freq)
                    if 5 <= fft_cycle <= 100:
                        result['fft_cycle'] = fft_cycle
                        result['fft_power'] = float(positive_power[max_power_idx] / np.sum(positive_power))
        except Exception:
            pass
    
    # 6. 评估周期性总体强度
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
        
        if overall_strength >= 0.6:
            result['cycle_quality'] = 'strong'
        elif overall_strength >= 0.4:
            result['cycle_quality'] = 'moderate'
        elif overall_strength >= 0.2:
            result['cycle_quality'] = 'weak'
        else:
            result['cycle_quality'] = 'none'
    
    # 7. 当前周期位置分析
    current_period = None
    if cycle_periods:
        last_period = cycle_periods[-1]
        if last_period.get('is_current', False):
            current_period = last_period
    
    if current_period:
        current_cycle_type = current_period.get('cycle_type')
        current_duration = current_period.get('duration', 0)
        
        if current_cycle_type == 'sideways':
            result['cycle_phase'] = 'sideways'
            result['cycle_phase_desc'] = current_period.get('cycle_type_desc', '横盘阶段')
            result['cycle_suggestion'] = '横盘整理中，等待突破'
        elif current_cycle_type == 'rise':
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
            result['cycle_phase'] = 'decline'
            result['cycle_phase_desc'] = '周期下跌阶段（进行中）'
            result['cycle_suggestion'] = '下跌趋势中，等待低点'
            result['days_from_last_peak'] = int(current_duration)
        
        # 计算周期位置
        if 'dominant_cycle' in result or 'avg_cycle_length' in result:
            cycle_len = result.get('dominant_cycle') or result.get('avg_cycle_length')
            if cycle_len:
                if current_cycle_type == 'rise':
                    expected_cycle_length = cycle_len * 0.5
                    cycle_position = current_duration / expected_cycle_length if expected_cycle_length > 0 else 0
                    cycle_position = min(1.0, max(0.0, cycle_position))
                    result['cycle_position'] = float(cycle_position)
                    result['days_to_next_peak'] = max(0, int(expected_cycle_length - current_duration))
                    result['days_to_next_trough'] = max(0, int(cycle_len - current_duration))
                    result['next_turn_type'] = 'peak'
                    result['next_turn_days'] = result['days_to_next_peak']
                elif current_cycle_type == 'decline':
                    expected_cycle_length = cycle_len * 0.5
                    cycle_position = 0.5 + (current_duration / expected_cycle_length) if expected_cycle_length > 0 else 0.5
                    cycle_position = min(1.0, max(0.5, cycle_position))
                    result['cycle_position'] = float(cycle_position)
                    result['days_to_next_trough'] = max(0, int(expected_cycle_length - current_duration))
                    result['days_to_next_peak'] = max(0, int(cycle_len - current_duration))
                    result['next_turn_type'] = 'trough'
                    result['next_turn_days'] = result['days_to_next_trough']
                else:
                    result['cycle_position'] = 0.0
                    result['days_to_next_peak'] = max(0, int(cycle_len * 0.5 - current_duration))
                    result['days_to_next_trough'] = max(0, int(cycle_len - current_duration))
                    result['next_turn_type'] = 'peak'
                    result['next_turn_days'] = result['days_to_next_peak']
                
                result['next_turn_desc'] = f'预计{result["next_turn_days"]}天后到达下一个{"高点" if result["next_turn_type"] == "peak" else "低点"}'
    elif 'dominant_cycle' in result or 'avg_cycle_length' in result:
        cycle_len = result.get('dominant_cycle') or result.get('avg_cycle_length')
        if cycle_len and len(troughs) >= 1:
            last_trough_idx = troughs[-1]
            current_position = len(prices) - 1 - last_trough_idx
            cycle_position = (current_position % int(cycle_len)) / cycle_len
            
            result['cycle_position'] = float(cycle_position)
            result['days_from_last_trough'] = int(current_position)
            result['days_to_next_peak'] = int(cycle_len * 0.5 - current_position) if cycle_position < 0.5 else int(cycle_len * (1.5 - cycle_position))
            result['days_to_next_trough'] = int(cycle_len - current_position)
            
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
            
            if cycle_position < 0.5:
                next_turn_type = 'peak'
                next_turn_days = result['days_to_next_peak']
            else:
                next_turn_type = 'trough'
                next_turn_days = result['days_to_next_trough']
            
            result['next_turn_type'] = next_turn_type
            result['next_turn_days'] = next_turn_days
            result['next_turn_desc'] = f'预计{next_turn_days}天后到达下一个{"高点" if next_turn_type == "peak" else "低点"}'
    
    # 8. 周期稳定性评估
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
    
    # 9. 横盘市场检测
    sideways_result = _detect_sideways_market(prices, highs, lows, cycle_periods, config)
    result.update(sideways_result)
    
    # 10. 综合周期分析总结
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

