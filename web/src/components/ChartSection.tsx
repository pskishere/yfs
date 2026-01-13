/**
 * K线图组件
 */
import React from 'react';
import { Collapse } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import TradingViewChart from './TradingViewChart';

interface ChartSectionProps {
  currentSymbol: string;
  analysisResult: AnalysisResult;
  isMobile?: boolean;
}

/**
 * K线图模块组件
 */
export const ChartSection: React.FC<ChartSectionProps> = ({
  currentSymbol,
  analysisResult,
  isMobile = false,
}) => {
  if (!currentSymbol) return null;

  return (
    <div id="section-chart">
      <Collapse
        ghost
        defaultActiveKey={[]}
        items={[{
          key: 'chart',
          label: (
            <span>
              <BarChartOutlined style={{ marginRight: 8 }} />
              K线图
            </span>
          ),
          children: (
            <div style={{ overflowX: 'auto', minWidth: '100%', width: '100%' }}>
              <TradingViewChart
                symbol={currentSymbol}
                height={isMobile ? 300 : 500}
                theme="light"
                indicators={analysisResult?.indicators}
                candles={analysisResult?.candles}
              />
            </div>
          ),
        }]}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
