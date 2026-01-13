/**
 * 交易信号组件
 */
import React from 'react';
import { Collapse, Descriptions, Tag } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import { formatValue, statusMaps } from '../utils/formatters';
import { renderSignalWithIcon } from '../utils/signalRenderer';

interface TradingSignalsProps {
  analysisResult: AnalysisResult;
  currencySymbol: string;
}

/**
 * 交易信号组件
 */
export const TradingSignals: React.FC<TradingSignalsProps> = ({
  analysisResult,
  currencySymbol,
}) => {
  const formatCurrency = (value?: number, decimals: number = 2) =>
    `${currencySymbol}${formatValue(value ?? 0, decimals)}`;

  const signals = analysisResult.signals;
  const indicators = analysisResult.indicators;

  if (!signals) return null;

  const renderSignalItems = () => {
    const items = [];

    // 风险等级
    if (signals.risk) {
      const riskLevel = String(signals.risk.level || 'unknown');
      const config = statusMaps.risk[riskLevel as keyof typeof statusMaps.risk] || 
        { color: 'default', text: '未知' };
      items.push({
        label: '风险等级',
        children: <Tag color={config.color}>{config.text}</Tag>,
      });
    }

    // 止损价
    if (signals.stop_loss) {
      items.push({
        label: '建议止损',
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#cf1322' }}>
            {formatCurrency(signals.stop_loss)}
          </span>
        ),
      });
    }

    // 止盈价
    if (signals.take_profit) {
      items.push({
        label: '建议止盈',
        children: (
          <span style={{ fontSize: 16, fontWeight: 600, color: '#3f8600' }}>
            {formatCurrency(signals.take_profit)}
          </span>
        ),
      });
    }

    // 风险回报比
    if (signals.stop_loss && signals.take_profit && indicators.current_price && indicators.current_price > 0) {
      const currentPrice = indicators.current_price;
      items.push({
        label: '风险回报比',
        span: 3,
        children: (
          <Tag color="blue" style={{ fontSize: 14 }}>
            1:{formatValue(
              Math.abs(
                ((signals.take_profit - currentPrice) / currentPrice) /
                ((signals.stop_loss - currentPrice) / currentPrice)
              ), 1
            )}
          </Tag>
        ),
      });
    }

    // 信号列表
    if (signals.signals && signals.signals.length > 0) {
      items.push({
        label: '信号列表',
        span: 3,
        children: (
          <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
            {signals.signals.map((signal: string, index: number) => (
              <li key={index} style={{ marginBottom: 4, fontSize: 14 }}>
                {renderSignalWithIcon(signal)}
              </li>
            ))}
          </ul>
        ),
      });
    }

    return items;
  };

  return (
    <Collapse
      ghost
      defaultActiveKey={['signals']}
      items={[{
        key: 'signals',
        label: (
          <span>
            <BarChartOutlined style={{ marginRight: 8 }} />
            交易信号
          </span>
        ),
        children: (
          <Descriptions
            bordered
            column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }}
            size="small"
            layout="vertical"
            items={renderSignalItems()}
          />
        ),
      }]}
      style={{ marginTop: 0 }}
    />
  );
};
