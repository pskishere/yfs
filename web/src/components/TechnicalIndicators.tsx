/**
 * 技术指标组件
 */
import React from 'react';
import { Collapse, Descriptions, Space, Tag } from 'antd';
import { BarChartOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import { formatValue, getRSIStatus } from '../utils/formatters';

interface TechnicalIndicatorsProps {
  analysisResult: AnalysisResult;
  currencySymbol: string;
  createIndicatorLabel: (label: string, indicatorKey: string) => React.ReactNode;
}

/**
 * 技术指标组件
 */
export const TechnicalIndicators: React.FC<TechnicalIndicatorsProps> = ({
  analysisResult,
  currencySymbol,
  createIndicatorLabel,
}) => {
  const formatCurrency = (value?: number, decimals: number = 2) =>
    `${currencySymbol}${formatValue(value ?? 0, decimals)}`;

  const indicators = analysisResult.indicators;

  const renderIndicatorItems = () => {
    const items = [];

    // RSI
    if (indicators.rsi !== undefined) {
      items.push({
        label: createIndicatorLabel('RSI(14)', 'rsi'),
        children: (
          <Space>
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              {formatValue(indicators.rsi, 1)}
            </span>
            <Tag color={getRSIStatus(indicators.rsi).color}>
              {getRSIStatus(indicators.rsi).text}
            </Tag>
          </Space>
        ),
      });
    }

    // MACD
    if (indicators.macd !== undefined) {
      items.push({
        label: createIndicatorLabel('MACD', 'macd'),
        children: (
          <Space>
            <span>{formatValue(indicators.macd, 3)}</span>
            {indicators.macd !== undefined && indicators.macd_signal !== undefined && indicators.macd > indicators.macd_signal ? (
              <Tag color="success">金叉</Tag>
            ) : (
              <Tag color="error">死叉</Tag>
            )}
          </Space>
        ),
      });
    }

    if (indicators.macd_signal !== undefined) {
      items.push({
        label: createIndicatorLabel('MACD信号线', 'macd'),
        children: formatValue(indicators.macd_signal, 3),
      });
    }

    if (indicators.macd_histogram !== undefined) {
      items.push({
        label: createIndicatorLabel('MACD柱状图', 'macd'),
        children: formatValue(indicators.macd_histogram, 3),
      });
    }

    // 布林带
    if (indicators.bb_upper) {
      items.push({
        label: createIndicatorLabel('布林带上轨', 'bb'),
        children: formatCurrency(indicators.bb_upper),
      });
    }

    if (indicators.bb_middle) {
      items.push({
        label: createIndicatorLabel('布林带中轨', 'bb'),
        children: formatCurrency(indicators.bb_middle),
      });
    }

    if (indicators.bb_lower) {
      items.push({
        label: createIndicatorLabel('布林带下轨', 'bb'),
        children: formatCurrency(indicators.bb_lower),
      });
    }

    // 成交量比率
    if (indicators.volume_ratio !== undefined) {
      items.push({
        label: createIndicatorLabel('成交量比率', 'volume_ratio'),
        children: (
          <Space>
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              {formatValue(indicators.volume_ratio, 2)}x
            </span>
            {indicators.volume_ratio > 1.5 ? (
              <Tag color="orange">放量</Tag>
            ) : indicators.volume_ratio < 0.7 ? (
              <Tag color="default">缩量</Tag>
            ) : (
              <Tag color="success">正常</Tag>
            )}
          </Space>
        ),
      });
    }

    // 波动率
    if (indicators.volatility_20 !== undefined) {
      items.push({
        label: createIndicatorLabel('波动率', 'volatility'),
        children: (
          <Space>
            <span>{formatValue(indicators.volatility_20)}%</span>
            {indicators.volatility_20 > 5 ? (
              <Tag color="error">极高</Tag>
            ) : indicators.volatility_20 > 3 ? (
              <Tag color="warning">高</Tag>
            ) : indicators.volatility_20 > 2 ? (
              <Tag color="default">中</Tag>
            ) : (
              <Tag color="success">低</Tag>
            )}
          </Space>
        ),
      });
    }

    // ATR
    if (indicators.atr !== undefined) {
      items.push({
        label: createIndicatorLabel('ATR', 'atr'),
        children: `${formatCurrency(indicators.atr)} (${formatValue(indicators.atr_percent, 1)}%)`,
      });
    }

    // KDJ
    if (indicators.kdj_k !== undefined) {
      items.push({
        label: createIndicatorLabel('KDJ', 'kdj'),
        children: (
          <Space orientation="vertical" size="small" style={{ width: '100%' }}>
            <div>
              K={formatValue(indicators.kdj_k, 1)} D={formatValue(indicators.kdj_d, 1)} J={formatValue(indicators.kdj_j, 1)}
            </div>
            <Space>
              {indicators.kdj_j !== undefined && indicators.kdj_j < 20 ? (
                <Tag color="success">超卖</Tag>
              ) : indicators.kdj_j !== undefined && indicators.kdj_j > 80 ? (
                <Tag color="error">超买</Tag>
              ) : (
                <Tag color="default">中性</Tag>
              )}
              {indicators.kdj_k !== undefined && indicators.kdj_d !== undefined && indicators.kdj_k > indicators.kdj_d ? (
                <Tag color="success">多头</Tag>
              ) : (
                <Tag color="error">空头</Tag>
              )}
            </Space>
          </Space>
        ),
      });
    }

    // 威廉%R
    if (indicators.williams_r !== undefined) {
      items.push({
        label: createIndicatorLabel('威廉%R', 'williams_r'),
        children: (
          <Space>
            <span>{formatValue(indicators.williams_r, 1)}</span>
            <Tag
              color={
                indicators.williams_r < -80 ? 'success' :
                  indicators.williams_r > -20 ? 'error' : 'default'
              }
            >
              {indicators.williams_r < -80 ? '超卖' :
                indicators.williams_r > -20 ? '超买' : '中性'}
            </Tag>
          </Space>
        ),
      });
    }

    // CCI
    if (indicators.cci !== undefined) {
      items.push({
        label: createIndicatorLabel('CCI', 'cci'),
        children: (
          <Space>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{formatValue(indicators.cci, 1)}</span>
            <Tag
              color={
                indicators.cci_signal === 'overbought' ? 'error' :
                  indicators.cci_signal === 'oversold' ? 'success' : 'default'
              }
            >
              {indicators.cci_signal === 'overbought' ? '超买(>100)' :
                indicators.cci_signal === 'oversold' ? '超卖(<-100)' : '中性'}
            </Tag>
          </Space>
        ),
      });
    }

    // ADX
    if (indicators.adx !== undefined) {
      items.push({
        label: createIndicatorLabel('ADX', 'adx'),
        children: (
          <Space orientation="vertical" size="small" style={{ width: '100%' }}>
            <div>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{formatValue(indicators.adx, 1)}</span>
              <Tag
                color={
                  indicators.adx > 40 ? 'success' :
                    indicators.adx > 25 ? 'default' : 'warning'
                }
                style={{ marginLeft: 8 }}
              >
                {indicators.adx > 40 ? '强趋势' :
                  indicators.adx > 25 ? '中趋势' :
                    indicators.adx > 20 ? '弱趋势' : '无趋势'}
              </Tag>
            </div>
            {indicators.plus_di !== undefined && indicators.minus_di !== undefined && (
              <div>
                <span>+DI={formatValue(indicators.plus_di, 1)} -DI={formatValue(indicators.minus_di, 1)}</span>
                <Tag color={indicators.plus_di > indicators.minus_di ? 'success' : 'error'} style={{ marginLeft: 8 }}>
                  {indicators.plus_di > indicators.minus_di ? '多头' : '空头'}
                </Tag>
              </div>
            )}
          </Space>
        ),
      });
    }

    // SAR
    if (indicators.sar !== undefined) {
      items.push({
        label: createIndicatorLabel('SAR', 'sar'),
        children: (
          <Space>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{formatCurrency(indicators.sar)}</span>
            <Tag
              color={
                indicators.sar_signal === 'bullish' ? 'success' :
                  indicators.sar_signal === 'bearish' ? 'error' : 'default'
              }
            >
              {indicators.sar_signal === 'bullish' ? '看涨' :
                indicators.sar_signal === 'bearish' ? '看跌' : '中性'}
            </Tag>
            {indicators.sar_distance_pct !== undefined && (
              <span style={{ fontSize: 14 }}>
                (距离{Math.abs(indicators.sar_distance_pct).toFixed(1)}%)
              </span>
            )}
          </Space>
        ),
      });
    }

    // Ichimoku Cloud
    if (indicators.ichimoku_tenkan_sen !== undefined) {
      items.push({
        label: createIndicatorLabel('一目均衡表', 'ichimoku'),
        children: (
          <Space orientation="vertical" size="small" style={{ width: '100%' }}>
            <Space>
              <Tag
                color={
                  indicators.ichimoku_status === 'above_cloud' ? 'success' :
                    indicators.ichimoku_status === 'below_cloud' ? 'error' : 'default'
                }
              >
                {indicators.ichimoku_status === 'above_cloud' ? '云上(看涨)' :
                  indicators.ichimoku_status === 'below_cloud' ? '云下(看跌)' : '云中(盘整)'}
              </Tag>
              {indicators.ichimoku_tk_cross === 'bullish' && <Tag color="success">金叉</Tag>}
              {indicators.ichimoku_tk_cross === 'bearish' && <Tag color="error">死叉</Tag>}
            </Space>
            <div style={{ fontSize: 12 }}>
              转折: {formatCurrency(indicators.ichimoku_tenkan_sen)} 基准: {formatCurrency(indicators.ichimoku_kijun_sen)}
            </div>
            <div style={{ fontSize: 12 }}>
              云层: {formatCurrency(indicators.ichimoku_cloud_bottom ?? Math.min(indicators.ichimoku_senkou_span_a || 0, indicators.ichimoku_senkou_span_b || 0))} - {formatCurrency(indicators.ichimoku_cloud_top ?? Math.max(indicators.ichimoku_senkou_span_a || 0, indicators.ichimoku_senkou_span_b || 0))}
            </div>
          </Space>
        ),
      });
    }

    // SuperTrend
    if (indicators.supertrend !== undefined) {
      items.push({
        label: createIndicatorLabel('SuperTrend', 'supertrend'),
        children: (
          <Space>
            <span style={{ fontSize: 16, fontWeight: 600 }}>{formatCurrency(indicators.supertrend)}</span>
            <Tag color={indicators.supertrend_direction === 'up' ? 'success' : 'error'}>
              {indicators.supertrend_direction === 'up' ? '看涨支撑' : '看跌阻力'}
            </Tag>
          </Space>
        ),
      });
    }

    // StochRSI
    if (indicators.stoch_rsi_k !== undefined) {
      items.push({
        label: createIndicatorLabel('StochRSI', 'stoch_rsi'),
        children: (
          <Space>
            <span>K: {formatValue(indicators.stoch_rsi_k, 1)}</span>
            <span>D: {formatValue(indicators.stoch_rsi_d, 1)}</span>
            <Tag
              color={
                indicators.stoch_rsi_status === 'oversold' ? 'success' :
                  indicators.stoch_rsi_status === 'overbought' ? 'error' : 'default'
              }
            >
              {indicators.stoch_rsi_status === 'oversold' ? '超卖' :
                indicators.stoch_rsi_status === 'overbought' ? '超买' : '中性'}
            </Tag>
          </Space>
        ),
      });
    }

    // Volume Profile
    if (indicators.vp_poc !== undefined) {
      items.push({
        label: createIndicatorLabel('筹码分布', 'volume_profile'),
        children: (
          <Space orientation="vertical" size="small">
            <Space>
              <span>POC: {formatCurrency(indicators.vp_poc)}</span>
              <Tag
                color={
                  indicators.vp_status === 'above_va' ? 'success' :
                    indicators.vp_status === 'below_va' ? 'error' : 'default'
                }
              >
                {indicators.vp_status === 'above_va' ? '上方失衡(看涨)' :
                  indicators.vp_status === 'below_va' ? '下方失衡(看跌)' : '价值区平衡'}
              </Tag>
            </Space>
            <span style={{ fontSize: 12 }}>
              价值区: {formatCurrency(indicators.vp_val)} - {formatCurrency(indicators.vp_vah)}
            </span>
          </Space>
        ),
      });
    }

    // OBV
    if (indicators.obv_trend) {
      items.push({
        label: createIndicatorLabel('OBV趋势', 'obv'),
        children: indicators.obv_trend === 'up' ? (
          (indicators.price_change_pct ?? 0) > 0 ? (
            <Tag color="success">量价齐升</Tag>
          ) : (
            <Tag color="warning">量价背离(可能见底)</Tag>
          )
        ) : indicators.obv_trend === 'down' ? (
          (indicators.price_change_pct ?? 0) < 0 ? (
            <Tag color="error">量价齐跌</Tag>
          ) : (
            <Tag color="warning">量价背离(可能见顶)</Tag>
          )
        ) : (
          <Tag color="default">平稳</Tag>
        ),
      });
    }

    // 趋势强度
    if (indicators.trend_strength !== undefined) {
      const getTrendTag = (direction: string | undefined) => {
        if (direction === 'up') return <Tag color="success"><RiseOutlined /> 上涨</Tag>;
        if (direction === 'down') return <Tag color="error"><FallOutlined /> 下跌</Tag>;
        return <Tag color="default">盘整</Tag>;
      };

      items.push({
        label: createIndicatorLabel('趋势强度', 'trend_strength'),
        children: (
          <Space>
            {getTrendTag(indicators.trend_direction)}
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              {formatValue(indicators.trend_strength, 0)}%
            </span>
            {indicators.trend_strength > 50 ? (
              <Tag color="success">强</Tag>
            ) : indicators.trend_strength > 25 ? (
              <Tag color="default">中</Tag>
            ) : (
              <Tag color="warning">弱</Tag>
            )}
          </Space>
        ),
      });
    }

    // 连续涨跌
    if ((indicators.consecutive_up_days ?? 0) > 0 || (indicators.consecutive_down_days ?? 0) > 0) {
      items.push({
        label: '连续涨跌',
        children: (
          <Space>
            {(indicators.consecutive_up_days ?? 0) > 0 ? (
              <>
                <RiseOutlined style={{ color: '#3f8600' }} />
                <span>连续{indicators.consecutive_up_days}天上涨</span>
                {(indicators.consecutive_up_days ?? 0) >= 5 && (
                  <Tag color="warning">注意</Tag>
                )}
              </>
            ) : (
              <>
                <FallOutlined style={{ color: '#cf1322' }} />
                <span>连续{indicators.consecutive_down_days}天下跌</span>
                {(indicators.consecutive_down_days ?? 0) >= 5 && (
                  <Tag color="success">关注</Tag>
                )}
              </>
            )}
          </Space>
        ),
      });
    }

    return items;
  };

  return (
    <div id="section-indicators">
      <Collapse
        ghost
        defaultActiveKey={[]}
        items={[{
          key: 'indicators',
          label: (
            <span>
              <BarChartOutlined style={{ marginRight: 8 }} />
              技术指标
            </span>
          ),
          children: (
            <Descriptions
              bordered
              column={{ xxl: 4, xl: 3, lg: 3, md: 2, sm: 1, xs: 1 }}
              size="small"
              layout="vertical"
              items={renderIndicatorItems()}
            />
          ),
        }]}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
