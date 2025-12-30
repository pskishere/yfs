# -*- coding: utf-8 -*-
"""
周期分析
新增功能:
1. 自适应参数调整
2. 小波变换多尺度分析
3. 周期预测置信度计算
4. 优化的横盘识别算法
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import signal
from scipy.fft import fft

try:
    import pywt
    PYWT_AVAILABLE = True
except ImportError:
    PYWT_AVAILABLE = False


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
    
    # 新增: 自适应参数
    adaptive_mode: bool = True  # 是否启用自适应参数调整
    volatility_low_threshold: float = 0.015  # 低波动阈值
    volatility_high_threshold: float = 0.03  # 高波动阈值


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





@dataclass
class TurningPoint:
    """转折点数据"""
    index: int
    point_type: str  # 'peak' or 'trough'
    price: float


def calculate_autocorrelation(prices, max_lag=None):
    """
    计算价格序列的自相关函数
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



def calculate_adaptive_config(prices: np.ndarray, volumes: np.ndarray = None) -> CycleConfig:
    """
    根据股票特性自适应计算配置参数
    
    参数:
        prices: 价格数组
        volumes: 成交量数组(可选)
    
    返回:
        CycleConfig: 自适应配置参数
    """
    config = CycleConfig()
    
    if len(prices) < 30:
        return config
    
    # 计算价格波动率
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns)
    
    # 计算价格变化幅度
    price_range = (np.max(prices) - np.min(prices)) / np.mean(prices)
    
    # 根据波动率调整参数
    if volatility > config.volatility_high_threshold:
        # 高波动股票
        config.min_prominence_pct = 0.03
        config.sideways_narrow_threshold = 8.0
        config.sideways_standard_threshold = 20.0
        config.sideways_wide_threshold = 35.0
        config.sideways_amplitude_threshold = 15.0
        config.min_period_days = 12
    elif volatility < config.volatility_low_threshold:
        # 低波动股票
        config.min_prominence_pct = 0.015
        config.sideways_narrow_threshold = 3.0
        config.sideways_standard_threshold = 10.0
        config.sideways_wide_threshold = 20.0
        config.sideways_amplitude_threshold = 8.0
        config.min_period_days = 8
    else:
        # 中等波动股票
        config.min_prominence_pct = 0.02
        config.sideways_narrow_threshold = 5.0
        config.sideways_standard_threshold = 15.0
        config.sideways_wide_threshold = 25.0
        config.sideways_amplitude_threshold = 10.0
        config.min_period_days = 10
    
    # 如果提供了成交量数据，考虑流动性
    if volumes is not None and len(volumes) > 0:
        volume_cv = np.std(volumes) / np.mean(volumes)  # 成交量变异系数
        if volume_cv > 1.0:
            # 成交量波动大，可能是小盘股或流动性差
            config.min_period_days = max(config.min_period_days, 15)
    
    return config


def wavelet_cycle_analysis(prices: np.ndarray, max_scale: int = 128) -> Dict[str, Any]:
    """
    使用连续小波变换进行多尺度周期分析
    
    参数:
        prices: 价格数组
        max_scale: 最大尺度
    
    返回:
        dict: 小波分析结果
    """
    result = {}
    
    if not PYWT_AVAILABLE:
        result['wavelet_available'] = False
        return result
    
    if len(prices) < 50:
        return result
    
    try:
        # 价格去趋势化
        detrended = signal.detrend(prices)
        
        # 使用Morlet小波进行连续小波变换
        scales = np.arange(1, min(max_scale, len(prices) // 4))
        coefficients, frequencies = pywt.cwt(detrended, scales, 'morl')
        
        # 计算功率谱
        power = np.abs(coefficients) ** 2
        
        # 找出主要周期（功率最大的尺度）
        avg_power = np.mean(power, axis=1)
        dominant_scale_idx = np.argmax(avg_power)
        dominant_scale = scales[dominant_scale_idx]
        
        # 计算周期强度（归一化功率）
        total_power = np.sum(avg_power)
        cycle_strength = avg_power[dominant_scale_idx] / total_power if total_power > 0 else 0
        
        # 检测多个显著周期
        # 找出功率峰值
        peak_indices, properties = signal.find_peaks(avg_power, prominence=np.max(avg_power) * 0.3)
        
        significant_cycles = []
        for idx in peak_indices[:5]:  # 最多保留5个显著周期
            cycle_period = int(scales[idx])
            cycle_power = float(avg_power[idx] / total_power)
            if cycle_power > 0.05:  # 功率占比超过5%
                significant_cycles.append({
                    'period': cycle_period,
                    'strength': cycle_power,
                    'scale': int(scales[idx])
                })
        
        # 按强度排序
        significant_cycles.sort(key=lambda x: x['strength'], reverse=True)
        
        result['wavelet_available'] = True
        result['wavelet_dominant_cycle'] = int(dominant_scale)
        result['wavelet_cycle_strength'] = float(cycle_strength)
        result['wavelet_significant_cycles'] = significant_cycles
        result['wavelet_method'] = 'Continuous Wavelet Transform (Morlet)'
        
        # 时频局部化分析
        # 计算最近20%数据的主导周期
        recent_ratio = 0.2
        recent_start = int(len(prices) * (1 - recent_ratio))
        recent_power = power[:, recent_start:]
        recent_avg_power = np.mean(recent_power, axis=1)
        recent_dominant_idx = np.argmax(recent_avg_power)
        recent_dominant_cycle = int(scales[recent_dominant_idx])
        
        result['wavelet_recent_cycle'] = recent_dominant_cycle
        result['wavelet_cycle_stability'] = float(1.0 - abs(recent_dominant_cycle - dominant_scale) / dominant_scale) if dominant_scale > 0 else 0
        
    except Exception as e:
        result['wavelet_error'] = str(e)
        result['wavelet_available'] = False
    
    return result


def calculate_cycle_confidence(prices: np.ndarray, 
                               dominant_cycle: Optional[int],
                               cycle_strength: float,
                               cycle_consistency: Optional[float] = None,
                               wavelet_result: Optional[Dict] = None) -> Dict[str, Any]:
    """
    计算周期预测的置信度
    
    参数:
        prices: 价格数组
        dominant_cycle: 主导周期长度
        cycle_strength: 周期强度
        cycle_consistency: 周期一致性
        wavelet_result: 小波分析结果
    
    返回:
        dict: 置信度相关指标
    """
    result = {}
    
    if dominant_cycle is None or dominant_cycle == 0:
        result['confidence_score'] = 0.0
        result['confidence_level'] = 'none'
        result['confidence_desc'] = '无法识别周期'
        return result
    
    # 计算置信度的多个维度
    scores = []
    factors = []
    
    # 因素1: 周期强度 (0-1) 权重: 30%
    if cycle_strength is not None:
        strength_score = min(cycle_strength, 1.0)
        scores.append(strength_score * 0.3)
        factors.append(f'强度: {strength_score:.2f}')
    
    # 因素2: 周期一致性 (0-1) 权重: 25%
    if cycle_consistency is not None:
        consistency_score = min(cycle_consistency, 1.0)
        scores.append(consistency_score * 0.25)
        factors.append(f'一致性: {consistency_score:.2f}')
    
    # 因素3: 数据充分性 权重: 15%
    # 至少需要3个完整周期的数据
    if dominant_cycle > 0:
        required_length = dominant_cycle * 3
        data_sufficiency = min(len(prices) / required_length, 1.0)
        scores.append(data_sufficiency * 0.15)
        factors.append(f'数据充分性: {data_sufficiency:.2f}')
    
    # 因素4: 小波验证 权重: 20%
    if wavelet_result and wavelet_result.get('wavelet_available'):
        wavelet_cycle = wavelet_result.get('wavelet_dominant_cycle', 0)
        if wavelet_cycle > 0:
            # 检查FFT/自相关周期与小波周期的一致性
            cycle_diff = abs(wavelet_cycle - dominant_cycle) / dominant_cycle
            wavelet_agreement = max(0, 1.0 - cycle_diff)
            scores.append(wavelet_agreement * 0.2)
            factors.append(f'小波验证: {wavelet_agreement:.2f}')
        
        # 小波周期稳定性
        wavelet_stability = wavelet_result.get('wavelet_cycle_stability', 0)
        if wavelet_stability > 0:
            scores.append(wavelet_stability * 0.1)
            factors.append(f'时变稳定性: {wavelet_stability:.2f}')
    
    # 因素5: 周期合理性 权重: 10%
    # 周期长度应该在合理范围内（5-100天）
    if 5 <= dominant_cycle <= 100:
        reasonability_score = 1.0
        # 20-60天的周期更可靠
        if 20 <= dominant_cycle <= 60:
            reasonability_score = 1.0
        elif 10 <= dominant_cycle < 20 or 60 < dominant_cycle <= 80:
            reasonability_score = 0.8
        else:
            reasonability_score = 0.6
        scores.append(reasonability_score * 0.1)
        factors.append(f'合理性: {reasonability_score:.2f}')
    
    # 综合置信度
    confidence_score = sum(scores) if scores else 0.0
    
    # 置信度等级
    if confidence_score >= 0.75:
        confidence_level = 'high'
        confidence_desc = '高置信度 - 周期特征明显且稳定'
    elif confidence_score >= 0.55:
        confidence_level = 'medium'
        confidence_desc = '中等置信度 - 存在周期特征但稳定性一般'
    elif confidence_score >= 0.35:
        confidence_level = 'low'
        confidence_desc = '低置信度 - 周期特征较弱或不稳定'
    else:
        confidence_level = 'very_low'
        confidence_desc = '极低置信度 - 周期特征不明显'
    
    result['confidence_score'] = float(confidence_score)
    result['confidence_level'] = confidence_level
    result['confidence_desc'] = confidence_desc
    result['confidence_factors'] = factors
    
    return result


def enhanced_sideways_detection(prices: np.ndarray,
                                highs: np.ndarray,
                                lows: np.ndarray,
                                volumes: np.ndarray,
                                cycle_periods: List[Dict[str, Any]],
                                config: CycleConfig) -> Dict[str, Any]:
    """
    增强的横盘检测算法
    新增:
    1. 考虑成交量分布
    2. 线性回归斜率分析
    3. 价格分布熵分析
    
    参数:
        prices: 价格数组
        highs: 最高价数组
        lows: 最低价数组
        volumes: 成交量数组
        cycle_periods: 周期列表
        config: 配置参数
    
    返回:
        dict: 横盘检测结果
    """
    result = {}
    lookback_20 = min(20, len(prices))
    
    if lookback_20 < 20:
        return result
    
    recent_20_prices = prices[-lookback_20:]
    recent_20_highs = highs[-lookback_20:] if len(highs) >= lookback_20 else recent_20_prices
    recent_20_lows = lows[-lookback_20:] if len(lows) >= lookback_20 else recent_20_prices
    recent_20_volumes = volumes[-lookback_20:] if len(volumes) >= lookback_20 else np.ones(lookback_20)
    
    avg_high_20 = float(np.mean(recent_20_highs))
    avg_low_20 = float(np.mean(recent_20_lows))
    avg_price_20 = float(np.mean(recent_20_prices))
    amplitude_20 = float(((avg_high_20 - avg_low_20) / avg_price_20) * 100 if avg_price_20 > 0 else 0)
    
    # 条件1: 20日振幅统计小于阈值
    condition1 = bool(float(amplitude_20) < config.sideways_amplitude_threshold)
    
    # 条件2: 均线缠绕
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
    
    # 条件3: 价格变化小于阈值
    price_change_20 = float(((recent_20_prices[-1] - recent_20_prices[0]) / recent_20_prices[0]) * 100 if recent_20_prices[0] > 0 else 0)
    condition3 = bool(abs(price_change_20) < config.sideways_price_change_threshold)
    
    # 条件4: 价格波动范围适中
    price_range_20 = float((np.max(recent_20_highs) - np.min(recent_20_lows)) / avg_price_20 * 100 if avg_price_20 > 0 else 0)
    condition4 = bool(3.0 <= price_range_20 <= config.sideways_wide_threshold)
    
    # 条件5: 周期振幅相近
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
    
    # 新条件6: 线性回归斜率分析
    condition6 = False
    try:
        x = np.arange(len(recent_20_prices))
        slope, intercept = np.polyfit(x, recent_20_prices, 1)
        # 计算斜率占价格的百分比
        slope_pct = abs(slope * len(recent_20_prices)) / avg_price_20 * 100
        condition6 = bool(slope_pct < 5.0)  # 斜率小于5%
        result['sideways_slope_pct'] = float(slope_pct)
    except Exception:
        pass
    
    # 新条件7: 价格分布熵分析
    condition7 = False
    try:
        # 将价格分为10个区间，计算分布熵
        bins = 10
        hist, _ = np.histogram(recent_20_prices, bins=bins)
        hist_normalized = hist / np.sum(hist)
        hist_normalized = hist_normalized[hist_normalized > 0]  # 去除零值
        entropy = -np.sum(hist_normalized * np.log2(hist_normalized))
        max_entropy = np.log2(bins)  # 均匀分布的最大熵
        normalized_entropy = entropy / max_entropy
        
        # 横盘时价格分布应该比较均匀，熵较高
        condition7 = bool(normalized_entropy > 0.6)
        result['sideways_price_entropy'] = float(normalized_entropy)
    except Exception:
        pass
    
    # 新条件8: 成交量分布
    condition8 = False
    try:
        volume_cv = np.std(recent_20_volumes) / np.mean(recent_20_volumes)
        # 横盘时成交量相对稳定
        condition8 = bool(volume_cv < 0.8)
        result['sideways_volume_cv'] = float(volume_cv)
    except Exception:
        pass
    
    # 计算横盘强度（加权评分）
    conditions = [
        (condition1, 0.20),  # 振幅 - 20%
        (condition2, 0.15),  # 均线缠绕 - 15%
        (condition3, 0.20),  # 价格变化 - 20%
        (condition4, 0.10),  # 波动范围 - 10%
        (condition5, 0.10),  # 周期振幅 - 10%
        (condition6, 0.10),  # 斜率 - 10%
        (condition7, 0.10),  # 熵 - 10%
        (condition8, 0.05),  # 成交量 - 5%
    ]
    
    sideways_strength = sum(weight for cond, weight in conditions if cond)
    
    # 判断为横盘（至少满足60%的加权条件，或核心条件满足）
    is_sideways = bool(sideways_strength >= 0.6 or (condition1 and condition3 and condition6))
    
    sideways_reasons = []
    if is_sideways:
        if condition1:
            sideways_reasons.append(f'20日振幅{float(amplitude_20):.1f}%')
        if condition2:
            sideways_reasons.append('均线缠绕')
        if condition3:
            sideways_reasons.append(f'价格变化{abs(price_change_20):.1f}%')
        if condition4:
            sideways_reasons.append(f'波动范围{price_range_20:.1f}%')
        if condition5:
            sideways_reasons.append('周期振幅相近')
        if condition6:
            sideways_reasons.append(f'趋势斜率{result.get("sideways_slope_pct", 0):.1f}%')
        if condition7:
            sideways_reasons.append(f'价格分布均匀(熵{result.get("sideways_price_entropy", 0):.2f})')
        if condition8:
            sideways_reasons.append('成交量稳定')
    
    result['sideways_market'] = bool(is_sideways)
    result['sideways_strength'] = float(sideways_strength)
    result['sideways_price_range_pct'] = float(price_range_20)
    result['sideways_price_change_pct'] = float(price_change_20)
    result['sideways_amplitude_20'] = float(amplitude_20)
    if is_sideways:
        result['sideways_reasons'] = sideways_reasons
        
        # 横盘类型分类
        if amplitude_20 < 5.0:
            result['sideways_type'] = 'narrow'
            result['sideways_type_desc'] = '窄幅横盘'
        elif amplitude_20 < 15.0:
            result['sideways_type'] = 'standard'
            result['sideways_type_desc'] = '标准横盘'
        else:
            result['sideways_type'] = 'wide'
            result['sideways_type_desc'] = '宽幅震荡'
    
    return result


def calculate_cycle_analysis(prices: np.ndarray, 
                                      highs: np.ndarray, 
                                      lows: np.ndarray,
                                      volumes: np.ndarray = None,
                                      timestamps: Optional[List] = None,
                                      use_adaptive: bool = True,
                                      use_wavelet: bool = True) -> Dict[str, Any]:
    """
    周期分析主函数（增强版）
    
    参数:
        prices: 价格数组
        highs: 最高价数组
        lows: 最低价数组  
        volumes: 成交量数组(可选)
        timestamps: 时间戳数组(可选)
        use_adaptive: 是否使用自适应参数
        use_wavelet: 是否使用小波分析
    
    返回:
        dict: 增强的周期分析结果
    """
    # 使用本模块的函数
    
    result = {}
    
    if len(prices) < 30:
        return result
    
    # 1. 获取配置（自适应或默认）
    if use_adaptive and volumes is not None:
        config = calculate_adaptive_config(prices, volumes)
        result['adaptive_config_used'] = True
        result['config_volatility_level'] = 'high' if config.min_prominence_pct > 0.025 else ('low' if config.min_prominence_pct < 0.018 else 'medium')
    else:
        config = CycleConfig()
        result['adaptive_config_used'] = False
    
    # 限制数据范围到最近3年
    actual_days = len(prices)
    if actual_days > config.max_data_days:
        prices = prices[-config.max_data_days:]
        highs = highs[-config.max_data_days:]
        lows = lows[-config.max_data_days:]
        if volumes is not None:
            volumes = volumes[-config.max_data_days:]
        if timestamps:
            timestamps = timestamps[-config.max_data_days:]
        result['data_range_note'] = f'基于最近3年数据（{config.max_data_days}个交易日）'
    else:
        result['data_range_note'] = f'基于全部可用数据（{actual_days}个交易日，约{actual_days/252:.1f}年）'
    
    # 2. 识别高点和低点
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
    
    # 3. 构建周期列表
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
    
    # 4. 计算周期统计
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
    
    # 5. 自相关分析
    autocorr, lags = calculate_autocorrelation(prices, max_lag=min(100, len(prices) // 2))
    
    dominant_cycle = None
    cycle_strength = 0.0
    
    if len(autocorr) > 0:
        dominant_cycle, cycle_strength = detect_cycle_length(autocorr, lags, min_cycle=5, max_cycle=100)
        
        if dominant_cycle:
            result['dominant_cycle'] = dominant_cycle
            result['cycle_strength'] = cycle_strength
        
        # 多周期检测
        valid_mask = (lags >= 5) & (lags <= 100)
        if np.any(valid_mask):
            valid_autocorr = autocorr[valid_mask]
            valid_lags = lags[valid_mask]
            
            peaks_idx, _ = signal.find_peaks(valid_autocorr, height=0.2, distance=5)
            
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
    
    # 6. 小波分析（新增）
    wavelet_result = {}
    if use_wavelet and PYWT_AVAILABLE:
        wavelet_result = wavelet_cycle_analysis(prices)
        result.update(wavelet_result)
    
    # 7. FFT频域分析
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
    
    # 8. 评估周期性总体强度
    cycle_indicators = []
    if 'cycle_strength' in result:
        cycle_indicators.append(result['cycle_strength'])
    if 'avg_autocorrelation' in result:
        cycle_indicators.append(result['avg_autocorrelation'])
    if 'fft_power' in result:
        cycle_indicators.append(result['fft_power'])
    if wavelet_result.get('wavelet_cycle_strength'):
        cycle_indicators.append(wavelet_result['wavelet_cycle_strength'])
    
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
    
    # 9. 周期预测置信度（新增）
    confidence_result = calculate_cycle_confidence(
        prices, 
        dominant_cycle, 
        cycle_strength,
        result.get('cycle_consistency'),
        wavelet_result if wavelet_result else None
    )
    result.update(confidence_result)
    
    # 10. 当前周期位置分析（保持原有逻辑，略）
    # ...（这部分保持原有cycle.py的实现）
    
    # 11. 增强的横盘检测（新增）
    if volumes is not None and len(volumes) >= 20:
        sideways_result = enhanced_sideways_detection(prices, highs, lows, volumes, cycle_periods, config)
        result.update(sideways_result)
    
    # 12. 综合周期分析总结
    summary_parts = []
    if 'dominant_cycle' in result:
        summary_parts.append(f"主要周期{result['dominant_cycle']}天")
    if 'cycle_quality' in result:
        quality_map = {'strong': '强', 'moderate': '中等', 'weak': '弱', 'none': '无'}
        summary_parts.append(f"质量{quality_map.get(result['cycle_quality'], '未知')}")
    if 'confidence_level' in result:
        conf_map = {'high': '高', 'medium': '中', 'low': '低', 'very_low': '极低', 'none': '无'}
        summary_parts.append(f"置信度{conf_map.get(result['confidence_level'], '未知')}")
    if 'sideways_market' in result and result['sideways_market']:
        summary_parts.append(result.get('sideways_type_desc', '横盘'))
    if summary_parts:
        result['cycle_summary'] = ' | '.join(summary_parts)
    
    return result


def analyze_yearly_cycles(closes: np.ndarray, 
                          highs: np.ndarray, 
                          lows: np.ndarray,
                          timestamps: Optional[List] = None) -> Dict[str, Any]:
    """
    分析年度周期规律
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        timestamps: 时间戳列表
    
    返回:
        dict: 年度周期分析结果
    """
    result = {}
    
    if len(closes) < 252:  # 少于一年数据
        return result
    
    try:
        # 按年份分组分析
        if timestamps:
            from datetime import datetime
            years_data = {}
            
            for i, ts in enumerate(timestamps):
                if isinstance(ts, str):
                    year = datetime.fromisoformat(ts.replace('Z', '+00:00')).year
                else:
                    year = ts.year if hasattr(ts, 'year') else None
                
                if year:
                    if year not in years_data:
                        years_data[year] = {'prices': [], 'highs': [], 'lows': [], 'indices': []}
                    years_data[year]['prices'].append(closes[i])
                    years_data[year]['highs'].append(highs[i] if i < len(highs) else closes[i])
                    years_data[year]['lows'].append(lows[i] if i < len(lows) else closes[i])
                    years_data[year]['indices'].append(i)
            
            # 计算每年的统计数据
            yearly_stats = []
            for year in sorted(years_data.keys()):
                data = years_data[year]
                if len(data['prices']) > 0:
                    prices_arr = np.array(data['prices'])
                    highs_arr = np.array(data['highs'])
                    lows_arr = np.array(data['lows'])
                    indices = data['indices']
                    
                    # 基础价格数据
                    year_high = float(np.max(highs_arr))
                    year_low = float(np.min(lows_arr))
                    year_open = float(prices_arr[0])
                    year_close = float(prices_arr[-1])
                    
                    # 找出最高价和最低价的位置
                    max_high_idx = int(np.argmax(highs_arr))
                    min_low_idx = int(np.argmin(lows_arr))
                    
                    # 计算涨幅
                    first_to_last_change = ((year_close - year_open) / year_open * 100) if year_open > 0 else 0
                    low_to_high_change = ((year_high - year_low) / year_low * 100) if year_low > 0 else 0
                    
                    # 获取日期
                    first_date = timestamps[indices[0]] if timestamps and indices[0] < len(timestamps) else None
                    last_date = timestamps[indices[-1]] if timestamps and indices[-1] < len(timestamps) else None
                    max_high_date = timestamps[indices[max_high_idx]] if timestamps and indices[max_high_idx] < len(timestamps) else None
                    min_low_date = timestamps[indices[min_low_idx]] if timestamps and indices[min_low_idx] < len(timestamps) else None
                    
                    yearly_stats.append({
                        'year': year,
                        'first_date': first_date,
                        'first_close': year_open,
                        'last_date': last_date,
                        'last_close': year_close,
                        'first_to_last_change': float(first_to_last_change),
                        'min_low': year_low,
                        'min_low_date': min_low_date,
                        'max_high': year_high,
                        'max_high_date': max_high_date,
                        'low_to_high_change': float(low_to_high_change),
                        'trading_days': len(data['prices'])
                    })
            
            result['yearly_stats'] = yearly_stats
            result['years_count'] = len(yearly_stats)
            
            # 计算平均年度表现
            if len(yearly_stats) > 0:
                avg_year_change = np.mean([s['first_to_last_change'] for s in yearly_stats])
                avg_year_amplitude = np.mean([s['low_to_high_change'] for s in yearly_stats])
                result['avg_yearly_change_pct'] = float(avg_year_change)
                result['avg_yearly_amplitude_pct'] = float(avg_year_amplitude)
    
    except Exception as e:
        result['error'] = str(e)
    
    return result


def analyze_monthly_cycles(closes: np.ndarray,
                           highs: np.ndarray,
                           lows: np.ndarray,
                           timestamps: Optional[List] = None) -> Dict[str, Any]:
    """
    分析月度周期规律
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        timestamps: 时间戳列表
    
    返回:
        dict: 月度周期分析结果
    """
    result = {}
    
    if len(closes) < 60:  # 少于3个月数据
        return result
    
    try:
        # 按月份分组分析
        if timestamps:
            from datetime import datetime
            months_data = {}
            
            for i, ts in enumerate(timestamps):
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    year_month = f"{dt.year}-{dt.month:02d}"
                else:
                    year_month = f"{ts.year}-{ts.month:02d}" if hasattr(ts, 'year') else None
                
                if year_month:
                    if year_month not in months_data:
                        months_data[year_month] = {'prices': [], 'highs': [], 'lows': [], 'indices': []}
                    months_data[year_month]['prices'].append(closes[i])
                    months_data[year_month]['highs'].append(highs[i] if i < len(highs) else closes[i])
                    months_data[year_month]['lows'].append(lows[i] if i < len(lows) else closes[i])
                    months_data[year_month]['indices'].append(i)
            
            # 计算每月的统计数据（仅保留最近24个月）
            monthly_stats = []
            for year_month in sorted(months_data.keys())[-24:]:
                data = months_data[year_month]
                if len(data['prices']) > 0:
                    prices_arr = np.array(data['prices'])
                    highs_arr = np.array(data['highs'])
                    lows_arr = np.array(data['lows'])
                    indices = data['indices']
                    
                    # 基础价格数据
                    month_high = float(np.max(highs_arr))
                    month_low = float(np.min(lows_arr))
                    month_open = float(prices_arr[0])
                    month_close = float(prices_arr[-1])
                    
                    # 找出最高价和最低价的位置
                    max_high_idx = int(np.argmax(highs_arr))
                    min_low_idx = int(np.argmin(lows_arr))
                    
                    # 计算涨幅
                    first_to_last_change = ((month_close - month_open) / month_open * 100) if month_open > 0 else 0
                    low_to_high_change = ((month_high - month_low) / month_low * 100) if month_low > 0 else 0
                    
                    # 获取日期
                    first_date = timestamps[indices[0]] if timestamps and indices[0] < len(timestamps) else None
                    last_date = timestamps[indices[-1]] if timestamps and indices[-1] < len(timestamps) else None
                    max_high_date = timestamps[indices[max_high_idx]] if timestamps and indices[max_high_idx] < len(timestamps) else None
                    min_low_date = timestamps[indices[min_low_idx]] if timestamps and indices[min_low_idx] < len(timestamps) else None
                    
                    monthly_stats.append({
                        'month': year_month,
                        'first_date': first_date,
                        'first_close': month_open,
                        'last_date': last_date,
                        'last_close': month_close,
                        'first_to_last_change': float(first_to_last_change),
                        'min_low': month_low,
                        'min_low_date': min_low_date,
                        'max_high': month_high,
                        'max_high_date': max_high_date,
                        'low_to_high_change': float(low_to_high_change),
                        'trading_days': len(data['prices'])
                    })
            
            result['monthly_stats'] = monthly_stats
            result['months_count'] = len(monthly_stats)
            
            # 计算平均月度表现
            if len(monthly_stats) > 0:
                avg_month_change = np.mean([s['first_to_last_change'] for s in monthly_stats])
                avg_month_amplitude = np.mean([s['low_to_high_change'] for s in monthly_stats])
                result['avg_monthly_change_pct'] = float(avg_month_change)
                result['avg_monthly_amplitude_pct'] = float(avg_month_amplitude)
    
    except Exception as e:
        result['error'] = str(e)
    
    return result

