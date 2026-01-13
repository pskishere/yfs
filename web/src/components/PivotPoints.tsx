/**
 * 关键价位组件
 */
import React from 'react';
import { Collapse, Descriptions } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import { formatValue } from '../utils/formatters';

interface PivotPointsProps {
  analysisResult: AnalysisResult;
  currencySymbol: string;
  createIndicatorLabel: (label: string, indicatorKey: string) => React.ReactNode;
}

/**
 * 关键价位组件
 */
export const PivotPoints: React.FC<PivotPointsProps> = ({
  analysisResult,
  currencySymbol,
  createIndicatorLabel,
}) => {
  const formatCurrency = (value?: number, decimals: number = 2) =>
    `${currencySymbol}${formatValue(value ?? 0, decimals)}`;

  const indicators = analysisResult.indicators;

  // 如果没有关键价位数据，不显示
  if (!indicators.pivot && !indicators.pivot_r1 && !indicators.resistance_20d_high) {
    return null;
  }

  const renderPivotItems = () => {
    const items = [];

    if (indicators.pivot) {
      items.push({
        label: createIndicatorLabel('枢轴点', 'pivot'),
        children: (
          <span style={{ fontSize: 14, fontWeight: 600 }}>
            {formatCurrency(indicators.pivot)}
          </span>
        ),
      });
    }

    if (indicators.pivot_r1) {
      items.push({
        label: createIndicatorLabel('压力位R1', 'pivot_r1'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
            {formatCurrency(indicators.pivot_r1)}
          </span>
        ),
      });
    }

    if (indicators.pivot_r2) {
      items.push({
        label: createIndicatorLabel('压力位R2', 'pivot_r2'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
            {formatCurrency(indicators.pivot_r2)}
          </span>
        ),
      });
    }

    if (indicators.pivot_r3) {
      items.push({
        label: createIndicatorLabel('压力位R3', 'pivot_r3'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
            {formatCurrency(indicators.pivot_r3)}
          </span>
        ),
      });
    }

    if (indicators.pivot_s1) {
      items.push({
        label: createIndicatorLabel('支撑位S1', 'pivot_s1'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
            {formatCurrency(indicators.pivot_s1)}
          </span>
        ),
      });
    }

    if (indicators.pivot_s2) {
      items.push({
        label: createIndicatorLabel('支撑位S2', 'pivot_s2'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
            {formatCurrency(indicators.pivot_s2)}
          </span>
        ),
      });
    }

    if (indicators.pivot_s3) {
      items.push({
        label: createIndicatorLabel('支撑位S3', 'pivot_s3'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
            {formatCurrency(indicators.pivot_s3)}
          </span>
        ),
      });
    }

    if (indicators.resistance_20d_high) {
      items.push({
        label: createIndicatorLabel('20日高点', 'resistance_20d_high'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
            {formatCurrency(indicators.resistance_20d_high)}
          </span>
        ),
      });
    }

    if (indicators.support_20d_low) {
      items.push({
        label: createIndicatorLabel('20日低点', 'support_20d_low'),
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
            {formatCurrency(indicators.support_20d_low)}
          </span>
        ),
      });
    }

    return items;
  };

  return (
    <div id="section-pivot">
      <Collapse
        ghost
        defaultActiveKey={['pivot']}
        items={[{
          key: 'pivot',
          label: (
            <span>
              <BarChartOutlined style={{ marginRight: 8 }} />
              关键价位
            </span>
          ),
          children: (
            <Descriptions
              bordered
              column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
              size="small"
              layout="vertical"
              items={renderPivotItems()}
            />
          ),
        }]}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
