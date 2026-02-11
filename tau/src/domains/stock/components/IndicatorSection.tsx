import React from 'react';
import { Card, Row, Col, Statistic, Descriptions, Tag, Typography, Space, Empty } from 'antd';
import { Indicators } from '../../../types';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface IndicatorSectionProps {
  indicators: Indicators;
}

const IndicatorSection: React.FC<IndicatorSectionProps> = ({ indicators }) => {
  if (!indicators) return <Empty description="暂无指标数据" />;

  const getTrendColor = (trend?: string) => {
    if (trend === 'up' || trend === 'strong_up' || trend === 'above') return '#3f8600';
    if (trend === 'down' || trend === 'strong_down' || trend === 'below') return '#cf1322';
    return '#8c8c8c';
  };

  const getTrendIcon = (trend?: string) => {
    if (trend === 'up' || trend === 'strong_up' || trend === 'above') return <ArrowUpOutlined />;
    if (trend === 'down' || trend === 'strong_down' || trend === 'below') return <ArrowDownOutlined />;
    return null;
  };

  return (
    <div style={{ padding: '16px' }}>
      <Title level={4}>技术指标分析</Title>
      
      <Row gutter={[16, 16]}>
        {/* 核心趋势 */}
        <Col span={24}>
          <Card size="small" title="核心趋势分析">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="当前价格"
                  value={indicators.current_price}
                  precision={2}
                  prefix="$"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="趋势方向"
                  value={indicators.trend_direction?.toUpperCase()}
                  valueStyle={{ color: getTrendColor(indicators.trend_direction) }}
                  prefix={getTrendIcon(indicators.trend_direction)}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="趋势强度"
                  value={indicators.trend_strength}
                  suffix="/ 100"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="20日涨跌"
                  value={indicators.price_change_pct}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: (indicators.price_change_pct || 0) >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 动量指标 */}
        <Col span={12}>
          <Card size="small" title="动量指标 (Momentum)">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="RSI (14)">
                <Space>
                  <Text strong>{indicators.rsi?.toFixed(2)}</Text>
                  {indicators.rsi && indicators.rsi > 70 && <Tag color="error">超买</Tag>}
                  {indicators.rsi && indicators.rsi < 30 && <Tag color="success">超卖</Tag>}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="MACD">
                <Text style={{ color: getTrendColor(indicators.macd_histogram && indicators.macd_histogram > 0 ? 'up' : 'down') }}>
                  {indicators.macd?.toFixed(2)} / {indicators.macd_signal?.toFixed(2)} (柱状图: {indicators.macd_histogram?.toFixed(2)})
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="KDJ">
                K: {indicators.kdj_k?.toFixed(2)} D: {indicators.kdj_d?.toFixed(2)} J: {indicators.kdj_j?.toFixed(2)}
              </Descriptions.Item>
              <Descriptions.Item label="Williams %R">
                {indicators.williams_r?.toFixed(2)}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* 波动率与支撑压力 */}
        <Col span={12}>
          <Card size="small" title="波动率与支撑压力">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="布林带 (BB)">
                <Text type="secondary">上: {indicators.bb_upper?.toFixed(2)} 中: {indicators.bb_middle?.toFixed(2)} 下: {indicators.bb_lower?.toFixed(2)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="ATR (14)">
                {indicators.atr?.toFixed(2)} ({indicators.atr_percent?.toFixed(2)}%)
              </Descriptions.Item>
              <Descriptions.Item label="支撑位 (20日)">
                <Text type="success">{indicators.support_20d_low?.toFixed(2)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="阻力位 (20日)">
                <Text type="danger">{indicators.resistance_20d_high?.toFixed(2)}</Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* 现代/高级指标 */}
        <Col span={12}>
          <Card size="small" title="现代趋势指标">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="VWAP">
                <Space>
                  {indicators.vwap?.toFixed(2)}
                  <Tag color={getTrendColor(indicators.vwap_signal)}>{indicators.vwap_signal}</Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="ADX (趋势强度)">
                <Space>
                  {indicators.adx?.toFixed(2)}
                  <Tag color={getTrendColor(indicators.adx_signal)}>{indicators.adx_signal}</Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Parabolic SAR">
                <Space>
                  {indicators.sar?.toFixed(2)}
                  <Tag color={indicators.sar_signal === 'buy' ? 'success' : 'error'}>{indicators.sar_signal?.toUpperCase()}</Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="SuperTrend">
                <Space>
                  {indicators.supertrend?.toFixed(2)}
                  <Tag color={indicators.supertrend_direction === 'up' ? 'success' : 'error'}>{indicators.supertrend_direction?.toUpperCase()}</Tag>
                </Space>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* 一目均衡表 */}
        <Col span={12}>
          <Card size="small" title="一目均衡表 (Ichimoku)">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="状态">
                <Tag color={getTrendColor(indicators.ichimoku_status)}>{indicators.ichimoku_status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="TK Cross">
                <Text strong>{indicators.ichimoku_tk_cross}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="云层 (Cloud)">
                顶: {indicators.ichimoku_cloud_top?.toFixed(2)} 底: {indicators.ichimoku_cloud_bottom?.toFixed(2)}
              </Descriptions.Item>
              <Descriptions.Item label="成交量比率">
                {indicators.volume_ratio?.toFixed(2)}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* 枢轴点 (Pivot Points) */}
        <Col span={24}>
          <Card size="small" title="枢轴点 (Standard Pivot Points)">
            <Row gutter={16}>
              <Col span={3}><Statistic title="S3" value={indicators.pivot_s3} precision={2} valueStyle={{ color: '#cf1322' }} /></Col>
              <Col span={3}><Statistic title="S2" value={indicators.pivot_s2} precision={2} valueStyle={{ color: '#cf1322' }} /></Col>
              <Col span={3}><Statistic title="S1" value={indicators.pivot_s1} precision={2} valueStyle={{ color: '#cf1322' }} /></Col>
              <Col span={6}><Statistic title="枢轴点 (P)" value={indicators.pivot} precision={2} /></Col>
              <Col span={3}><Statistic title="R1" value={indicators.pivot_r1} precision={2} valueStyle={{ color: '#3f8600' }} /></Col>
              <Col span={3}><Statistic title="R2" value={indicators.pivot_r2} precision={2} valueStyle={{ color: '#3f8600' }} /></Col>
              <Col span={3}><Statistic title="R3" value={indicators.pivot_r3} precision={2} valueStyle={{ color: '#3f8600' }} /></Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default IndicatorSection;
