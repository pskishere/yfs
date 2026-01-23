/**
 * K线图组件
 */
import React from 'react';
import type { AnalysisResult } from '../../../types/index';
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
      <div style={{ overflowX: 'auto', minWidth: '100%', width: '100%' }}>
        <TradingViewChart
          symbol={currentSymbol}
          height={isMobile ? 300 : 500}
          theme="light"
          indicators={analysisResult?.indicators}
          candles={analysisResult?.candles}
        />
      </div>
    </div>
  );
};
