#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
评分系统模块 - 基于技术指标的多维度加权评分算法
"""

import numpy as np
from typing import Dict, Tuple, Optional


class ScoringSystem:
    """
    多维度加权评分系统
    
    评分体系：
    - 各维度内部评分：0 到 100（百分制）
    - 最终综合评分：0 到 100（百分制）
    - 评分等级：
      * 70-100分：强烈买入/买入/轻度买入
      * 46-69分：中性观望
      * 0-45分：轻度卖出/卖出/强烈卖出
    """
    
    # 各维度权重配置
    WEIGHTS = {
        'trend': 0.25,        # 趋势方向权重
        'momentum': 0.20,     # 动量指标权重
        'volume': 0.15,       # 成交量分析权重
        'volatility': 0.10,   # 波动性权重
        'support_resistance': 0.15,  # 支撑压力权重
        'advanced': 0.15      # 高级指标权重
    }
    
    def __init__(self):
        """初始化评分系统"""
        pass
    
    def _get_adaptive_weights(self, indicators: Dict) -> Dict[str, float]:
        """
        根据股票特征动态调整权重（优化版）
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            调整后的权重字典
        """
        weights = self.WEIGHTS.copy()
        
        volatility = indicators.get('volatility_20', 2.0)
        trend_strength = indicators.get('trend_strength', 0)
        adx = indicators.get('adx', 0)
        volume_ratio = indicators.get('volume_ratio', 1.0)
        price_change = indicators.get('price_change_pct', 0)
        
        # 1. 高波动股票：增加风险管理权重，但不过度降低趋势权重
        if volatility > 4.0:
            weights['volatility'] *= 1.4  # 从1.5降低
            weights['trend'] *= 0.85      # 从0.8提高
            weights['momentum'] *= 0.95   # 从0.9提高
        # 2. 低波动股票：增加动量权重（寻找突破机会）
        elif volatility < 1.5:
            weights['momentum'] *= 1.25   # 从1.3降低，避免过度依赖
            weights['volatility'] *= 0.75  # 从0.7提高
        
        # 3. 强趋势股票：增加趋势和动量权重
        if trend_strength > 70 or adx > 40:
            weights['trend'] *= 1.25       # 从1.3降低
            weights['momentum'] *= 1.15    # 从1.2降低
            weights['support_resistance'] *= 0.85  # 从0.8提高
        # 4. 弱趋势/震荡股票：增加支撑压力位和动量权重（捕捉反弹）
        elif trend_strength < 30 or adx < 20:
            weights['support_resistance'] *= 1.3  # 从1.4降低
            weights['momentum'] *= 1.2     # 新增：震荡市更关注超买超卖
            weights['trend'] *= 0.75       # 从0.7提高
        # 5. 中等趋势（30-70）：均衡权重
        else:
            weights['trend'] *= 1.1
            weights['momentum'] *= 1.1
        
        # 6. 成交量异常：增加成交量权重
        if volume_ratio > 2.0:
            weights['volume'] *= 1.4       # 从1.5降低
        elif volume_ratio < 0.5:
            weights['volume'] *= 0.7       # 从0.6提高
        
        # 7. 反弹信号：价跌量缩后价涨
        if price_change > 0 and volume_ratio < 0.8:
            prev_change = indicators.get('prev_price_change_pct', 0)
            if prev_change < 0:
                weights['momentum'] *= 1.2
                weights['support_resistance'] *= 1.2
        
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def calculate_score(self, indicators: Dict, apply_risk_adjustment: bool = True, use_adaptive_weights: bool = True) -> Tuple[int, Dict]:
        """
        计算综合评分
        
        Args:
            indicators: 技术指标字典
            apply_risk_adjustment: 是否应用风险调整因子（默认True）
            use_adaptive_weights: 是否使用自适应权重（默认True）
            
        Returns:
            (综合评分, 详细评分字典)
            评分范围: 0 到 100（百分制）
        """
        if not indicators:
            return 50, {}
        
        if use_adaptive_weights:
            weights = self._get_adaptive_weights(indicators)
        else:
            weights = self.WEIGHTS
        
        # 各维度评分
        trend_score = self._score_trend(indicators)
        momentum_score = self._score_momentum(indicators)
        volume_score = self._score_volume(indicators)
        volatility_score = self._score_volatility(indicators)
        support_resistance_score = self._score_support_resistance(indicators)
        advanced_score = self._score_advanced(indicators)
        
        def to_weighted_score(score_0_100):
            """将0-100评分转换为-100到100用于加权计算"""
            return (score_0_100 - 50) * 2
        
        base_score = (
            to_weighted_score(trend_score) * weights['trend'] +
            to_weighted_score(momentum_score) * weights['momentum'] +
            to_weighted_score(volume_score) * weights['volume'] +
            to_weighted_score(volatility_score) * weights['volatility'] +
            to_weighted_score(support_resistance_score) * weights['support_resistance'] +
            to_weighted_score(advanced_score) * weights['advanced']
        )
        
        risk_adjustment_factor = 1.0
        risk_level = indicators.get('risk_level', 'medium')
        
        if apply_risk_adjustment:
            risk_adjustment_map = {
                'very_low': 1.12,   # 低风险加成12%
                'low': 1.06,        # 低风险加成6%
                'medium': 1.0,      # 中等风险不调整
                'high': 0.90,       # 高风险惩罚10%
                'very_high': 0.80   # 极高风险惩罚20%
            }
            risk_adjustment_factor = risk_adjustment_map.get(risk_level, 1.0)
        
        adjusted_score = base_score * risk_adjustment_factor
        
        total_score = int(round((adjusted_score + 100) / 2))
        total_score = max(0, min(100, total_score))
        
        score_details = {
            'total': total_score,
            'base_score': round(base_score, 1),
            'adjusted_score': round(adjusted_score, 1),
            'risk_adjustment_factor': round(risk_adjustment_factor, 3),
            'risk_level': risk_level,
            'adaptive_weights_used': use_adaptive_weights,
            'dimensions': {
                'trend': round(trend_score, 1),
                'momentum': round(momentum_score, 1),
                'volume': round(volume_score, 1),
                'volatility': round(volatility_score, 1),
                'support_resistance': round(support_resistance_score, 1),
                'advanced': round(advanced_score, 1)
            },
            'weights': {k: round(v, 3) for k, v in weights.items()},
            'base_weights': self.WEIGHTS
        }
        
        return total_score, score_details
    
    def _score_trend(self, indicators: Dict) -> float:
        """
        趋势方向评分 (0 到 100)
        
        考虑因素:
        - MA均线排列
        - ADX趋势强度
        - SuperTrend
        - Ichimoku云层
        """
        score = 50.0  # 基准分50（中性）
        
        ma_score = 0.0
        if all(k in indicators for k in ['ma5', 'ma20', 'ma50']):
            ma5 = indicators['ma5']
            ma20 = indicators['ma20']
            ma50 = indicators['ma50']
            current_price = indicators.get('current_price', 0)
            
            if current_price > 0:
                if current_price > ma5 > ma20 > ma50:
                    ma_score = 30
                elif current_price < ma5 < ma20 < ma50:
                    ma_score = -30
                elif current_price > ma5 and ma5 > ma20:
                    ma_score = 20
                elif current_price > ma20 and ma20 > ma50:
                    ma_score = 18
                elif current_price > ma5 and ma5 < ma20:
                    ma_score = 12
                elif ma5 < current_price < ma20 or ma20 < current_price < ma5:
                    ma_score = 5
                elif ma5 < ma20 and current_price < ma5:
                    ma_score = -15
                elif current_price < ma20 < ma50:
                    ma_score = -20
        
        score += ma_score * 0.3
        
        adx_score = 0.0
        if 'adx' in indicators:
            adx = indicators['adx']
            adx_signal = indicators.get('adx_signal', 'weak_trend')
            plus_di = indicators.get('plus_di', 0)
            minus_di = indicators.get('minus_di', 0)
            
            if adx_signal == 'strong_trend':
                if plus_di > minus_di:
                    intensity = min(adx / 50.0, 1.0)
                    adx_score = 30 * intensity
                else:
                    intensity = min(adx / 50.0, 1.0)
                    adx_score = -30 * intensity
            elif adx_signal == 'trend':
                if plus_di > minus_di:
                    adx_score = 15
                else:
                    adx_score = -15
        
        score += adx_score * 0.3
        
        supertrend_score = 0.0
        if 'supertrend' in indicators and 'supertrend_direction' in indicators:
            st_dir = indicators['supertrend_direction']
            current_price = indicators.get('current_price', 0)
            st_price = indicators.get('supertrend', 0)
            
            if current_price > 0 and st_price > 0:
                if st_dir == 'up' and current_price > st_price:
                    supertrend_score = 20
                elif st_dir == 'down' and current_price < st_price:
                    supertrend_score = -20
        
        score += supertrend_score * 0.2
        
        ichimoku_score = 0.0
        if all(k in indicators for k in ['ichimoku_cloud_top', 'ichimoku_cloud_bottom', 'ichimoku_status']):
            current_price = indicators.get('current_price', 0)
            cloud_top = indicators.get('ichimoku_cloud_top', 0)
            cloud_bottom = indicators.get('ichimoku_cloud_bottom', 0)
            status = indicators.get('ichimoku_status', 'unknown')
            
            if current_price > 0 and cloud_top > 0 and cloud_bottom > 0:
                if status == 'bullish':
                    ichimoku_score = 20
                elif status == 'bearish':
                    ichimoku_score = -20
                elif current_price > cloud_top:
                    ichimoku_score = 10
                elif current_price < cloud_bottom:
                    ichimoku_score = -10
        
        score += ichimoku_score * 0.2
        
        return max(0, min(100, score))
    
    def _score_momentum(self, indicators: Dict) -> float:
        """
        动量指标评分 (0 到 100)
        
        考虑因素:
        - RSI
        - MACD
        - KDJ
        - CCI
        - StochRSI
        """
        score = 50.0
        
        rsi_score = 0.0
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            if rsi < 30:
                rsi_score = 25 * (30 - rsi) / 30
            elif 30 <= rsi < 45:
                rsi_score = 20
            elif 45 <= rsi < 60:
                if trend_direction == 'up':
                    rsi_score = 18
                else:
                    rsi_score = 10
            elif 60 <= rsi <= 70:
                if trend_direction == 'up':
                    rsi_score = 8
                else:
                    rsi_score = -5
            elif rsi > 70:
                rsi_score = -25 * (rsi - 70) / 30
        
        score += rsi_score * 0.25
        
        macd_score = 0.0
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            histogram = indicators.get('macd_histogram', 0)
            
            if macd > signal:
                macd_score = 25 * min(abs(histogram) * 10, 1.0)
            else:
                macd_score = -25 * min(abs(histogram) * 10, 1.0)
        
        score += macd_score * 0.25
        
        kdj_score = 0.0
        if all(k in indicators for k in ['kdj_k', 'kdj_d', 'kdj_j']):
            k = indicators['kdj_k']
            d = indicators['kdj_d']
            j = indicators['kdj_j']
            
            if j < 20:
                kdj_score = 20 * (20 - j) / 20
            elif j > 80:
                kdj_score = -20 * (j - 80) / 20
            elif k > d:
                kdj_score = 10
            elif k < d:
                kdj_score = -10
        
        score += kdj_score * 0.2
        
        cci_score = 0.0
        if 'cci' in indicators:
            cci = indicators['cci']
            if cci < -100:
                cci_score = 15 * min((abs(cci) - 100) / 100, 1.0)
            elif cci > 100:
                cci_score = -15 * min((cci - 100) / 100, 1.0)
        
        score += cci_score * 0.15
        
        stoch_rsi_score = 0.0
        if 'stoch_rsi_k' in indicators and 'stoch_rsi_d' in indicators:
            k = indicators['stoch_rsi_k']
            d = indicators['stoch_rsi_d']
            status = indicators.get('stoch_rsi_status', 'neutral')
            
            if status == 'oversold':
                if k > d:
                    stoch_rsi_score = 15
                else:
                    stoch_rsi_score = 8
            elif status == 'overbought':
                if k < d:
                    stoch_rsi_score = -15
                else:
                    stoch_rsi_score = -8
        
        score += stoch_rsi_score * 0.15
        
        return max(0, min(100, score))
    
    def _score_volume(self, indicators: Dict) -> float:
        """
        成交量分析评分 (0 到 100)
        
        考虑因素:
        - 价量配合
        - OBV趋势
        - Volume Profile
        - 成交量比率
        """
        score = 50.0
        
        price_volume_score = 0.0
        if 'price_volume_confirmation' in indicators:
            confirmation = indicators['price_volume_confirmation']
            price_change = indicators.get('price_change_pct', 0)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            
            if confirmation == 'bullish':
                if volume_ratio > 2.0:
                    price_volume_score = 40
                elif volume_ratio > 1.5:
                    price_volume_score = 35
                else:
                    price_volume_score = 25
            elif confirmation == 'bearish':
                if volume_ratio > 2.0 and price_change < -5:
                    price_volume_score = -30
                else:
                    price_volume_score = -40
            elif confirmation == 'divergence':
                if price_change > 0:
                    price_volume_score = -15
                else:
                    price_volume_score = 10
            else:
                if volume_ratio > 1.5:
                    price_volume_score = 10
                elif volume_ratio < 0.6:
                    price_volume_score = -10
        
        score += price_volume_score * 0.4
        
        obv_score = 0.0
        if 'obv_trend' in indicators:
            obv_trend = indicators['obv_trend']
            price_change = indicators.get('price_change_pct', 0)
            
            if obv_trend == 'up' and price_change > 0:
                obv_score = 30
            elif obv_trend == 'down' and price_change < 0:
                obv_score = -30
            elif obv_trend == 'up':
                obv_score = 15
            elif obv_trend == 'down':
                obv_score = -15
        
        score += obv_score * 0.3
        
        vp_score = 0.0
        if 'vp_status' in indicators:
            vp_status = indicators['vp_status']
            if vp_status == 'above_va':
                vp_score = 20
            elif vp_status == 'below_va':
                vp_score = -20
        
        score += vp_score * 0.2
        
        volume_ratio_score = 0.0
        if 'volume_ratio' in indicators:
            ratio = indicators['volume_ratio']
            price_change = indicators.get('price_change_pct', 0)
            
            if ratio > 1.5 and price_change > 0:
                volume_ratio_score = 10
            elif ratio > 1.5 and price_change < 0:
                volume_ratio_score = -10
        
        score += volume_ratio_score * 0.1
        
        return max(0, min(100, score))
    
    def _score_volatility(self, indicators: Dict) -> float:
        """
        波动性评分 (0 到 100)
        
        考虑因素:
        - 波动率水平
        - 布林带位置
        - ATR
        """
        score = 50.0
        
        bb_score = 0.0
        if all(k in indicators for k in ['bb_upper', 'bb_lower', 'bb_middle', 'current_price']):
            price = indicators['current_price']
            upper = indicators['bb_upper']
            lower = indicators['bb_lower']
            middle = indicators['bb_middle']
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            if upper > lower > 0:
                band_width = upper - lower
                position = (price - lower) / band_width if band_width > 0 else 0.5
                
                if position <= 0.1:
                    bb_score = 50 * (0.1 - position) / 0.1
                elif 0.1 < position <= 0.25:
                    bb_score = 35
                elif 0.25 < position <= 0.4:
                    bb_score = 25
                elif 0.4 < position <= 0.6:
                    if trend_direction == 'up':
                        bb_score = 15
                    elif price > middle:
                        bb_score = 10
                    else:
                        bb_score = 5
                elif 0.6 < position <= 0.75:
                    if trend_direction == 'up':
                        bb_score = 8
                    else:
                        bb_score = 0
                elif 0.75 < position <= 0.9:
                    bb_score = -10
                elif position > 0.9:
                    bb_score = -50 * (position - 0.9) / 0.1
        
        score += bb_score * 0.5
        
        volatility_score = 0.0
        if 'volatility_20' in indicators:
            vol = indicators['volatility_20']
            if 2.0 <= vol <= 3.0:
                volatility_score = 30
            elif 1.5 <= vol < 2.0 or 3.0 < vol <= 4.0:
                volatility_score = 15
            elif vol < 1.0:
                volatility_score = -20
            elif vol > 5.0:
                volatility_score = -40
            elif vol > 4.0:
                volatility_score = -25
        
        score += volatility_score * 0.3
        
        atr_score = 0.0
        if 'atr_percent' in indicators:
            atr_pct = indicators['atr_percent']
            if atr_pct < 1.5:
                atr_score = 20
            elif atr_pct > 5.0:
                atr_score = -30
        
        score += atr_score * 0.2
        
        return max(0, min(100, score))
    
    def _score_support_resistance(self, indicators: Dict) -> float:
        """
        支撑压力位评分 (0 到 100)
        
        考虑因素:
        - 距离支撑/压力位的距离
        - 突破关键位
        - SAR位置
        """
        score = 50.0
        current_price = indicators.get('current_price', 0)
        
        if current_price <= 0:
            return 50.0
        
        support_score = 0.0
        if 'support_20d_low' in indicators:
            support = indicators['support_20d_low']
            dist_pct = ((current_price - support) / current_price) * 100
            
            if dist_pct < -5:
                support_score = -40
            elif -5 <= dist_pct < -2:
                support_score = -25
            elif -2 <= dist_pct < 0:
                support_score = 20
            elif 0 <= dist_pct < 3:
                support_score = 40
            elif 3 <= dist_pct < 8:
                support_score = 25
            elif 8 <= dist_pct < 15:
                support_score = 10
            else:
                support_score = 0
        
        score += support_score * 0.4
        
        resistance_score = 0.0
        if 'resistance_20d_high' in indicators:
            resistance = indicators['resistance_20d_high']
            dist_pct = ((resistance - current_price) / current_price) * 100
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            if dist_pct < -3:
                resistance_score = 30
            elif -3 <= dist_pct < 0:
                resistance_score = 20
            elif 0 <= dist_pct < 2:
                if trend_direction == 'up':
                    resistance_score = -5
                else:
                    resistance_score = -20
            elif 2 <= dist_pct < 5:
                resistance_score = -10
            elif 5 <= dist_pct < 10:
                resistance_score = 10
            elif 10 <= dist_pct < 20:
                resistance_score = 20
            else:
                resistance_score = 15
        
        score += resistance_score * 0.3
        
        sar_score = 0.0
        if 'sar' in indicators and 'sar_signal' in indicators:
            sar = indicators['sar']
            sar_signal = indicators.get('sar_signal', 'hold')
            sar_trend = indicators.get('sar_trend', 'neutral')
            
            if sar > 0:
                if sar_signal == 'buy':
                    if sar_trend == 'up':
                        sar_score = 25
                    else:
                        sar_score = 30
                elif sar_signal == 'sell':
                    if sar_trend == 'down':
                        sar_score = -25
                    else:
                        sar_score = -30
        
        score += sar_score * 0.3
        
        return max(0, min(100, score))
    
    def _score_advanced(self, indicators: Dict) -> float:
        """
        高级指标评分 (0 到 100)
        
        考虑因素:
        - ML预测
        - 连续涨跌天数
        - 趋势强度
        - 威廉指标
        """
        score = 50.0
        
        ml_score = 0.0
        if 'ml_trend' in indicators:
            ml_trend = indicators['ml_trend']
            ml_confidence = indicators.get('ml_confidence', 0)
            ml_prediction = indicators.get('ml_prediction', 0)
            
            if ml_confidence > 70:
                if ml_trend == 'up':
                    ml_score = 20 * (ml_confidence / 100)
                elif ml_trend == 'down':
                    ml_score = -20 * (ml_confidence / 100)
            elif ml_confidence > 50:
                if ml_trend == 'up':
                    ml_score = 10 * (ml_confidence / 100)
                elif ml_trend == 'down':
                    ml_score = -10 * (ml_confidence / 100)
        
        score += ml_score * 0.2
        
        trend_strength_score = 0.0
        if 'trend_strength' in indicators and 'trend_direction' in indicators:
            strength = indicators['trend_strength']
            direction = indicators['trend_direction']
            
            if strength > 50:
                if direction == 'up':
                    trend_strength_score = 35 * (strength / 100)
                elif direction == 'down':
                    trend_strength_score = -35 * (strength / 100)
        
        score += trend_strength_score * 0.35
        
        consecutive_score = 0.0
        up_days = indicators.get('consecutive_up_days', 0)
        down_days = indicators.get('consecutive_down_days', 0)
        price_change = indicators.get('price_change_pct', 0)
        
        if down_days >= 7:
            consecutive_score = 25
        elif down_days >= 5:
            consecutive_score = 20
        elif down_days >= 3:
            consecutive_score = 12
        elif down_days == 0 and price_change > 0:
            prev_down = indicators.get('prev_consecutive_down_days', 0)
            if prev_down >= 3:
                consecutive_score = 18
        elif up_days >= 7:
            consecutive_score = -20
        elif up_days >= 5:
            consecutive_score = -10
        elif up_days >= 1 and up_days <= 4:
            if price_change > 0 and price_change < 5:
                consecutive_score = 8
            elif price_change >= 5:
                consecutive_score = 5
        
        score += consecutive_score * 0.25
        
        wr_score = 0.0
        if 'williams_r' in indicators:
            wr = indicators['williams_r']
            if wr < -80:
                wr_score = 10 * (abs(wr) - 80) / 20
            elif wr > -20:
                wr_score = -10 * (20 - abs(wr)) / 20
        
        score += wr_score * 0.1
        
        return max(0, min(100, score))
    
    def get_recommendation(self, score: int) -> Tuple[str, str]:
        """
        根据评分获取建议（百分制，0-100分）
        
        Args:
            score: 综合评分 (0 到 100)
            
        Returns:
            (建议文字, 操作标识)
        """
        if score >= 70:
            return '🟢 强烈买入', 'strong_buy'
        elif score >= 60:
            return '🟢 买入', 'buy'
        elif score >= 54:
            return '🟢 轻度买入', 'buy_light'
        elif score >= 46:
            return '⚪ 中性观望', 'hold'
        elif score >= 40:
            return '🔴 轻度卖出', 'sell_light'
        elif score >= 30:
            return '🔴 卖出', 'sell'
        else:
            return '🔴 强烈卖出', 'strong_sell'


# 全局评分系统实例
_scoring_system = ScoringSystem()


def calculate_comprehensive_score(indicators: Dict) -> Tuple[int, Dict]:
    """
    计算综合评分的便捷函数
    
    Args:
        indicators: 技术指标字典
        
    Returns:
        (综合评分, 详细评分字典)
    """
    return _scoring_system.calculate_score(indicators)


def get_recommendation(score: int) -> Tuple[str, str]:
    """
    获取建议的便捷函数
    
    Args:
        score: 综合评分
        
    Returns:
        (建议文字, 操作标识)
    """
    return _scoring_system.get_recommendation(score)

