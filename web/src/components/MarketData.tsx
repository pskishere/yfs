/**
 * 市场数据组件
 */
import React from 'react';
import { Collapse, Descriptions } from 'antd';
import { GlobalOutlined } from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';

interface MarketDataProps {
  analysisResult: AnalysisResult;
  currencySymbol: string;
  createIndicatorLabel: (label: string, indicatorKey: string) => React.ReactNode;
}

/**
 * 市场数据组件
 */
export const MarketData: React.FC<MarketDataProps> = ({
  analysisResult,
  createIndicatorLabel,
}) => {
  const extraData = analysisResult.extra_data;

  if (!extraData || Object.keys(extraData).length === 0) {
    return null;
  }

  // 过滤掉已在其他地方显示的字段
  const skipFields = ['stock_name', 'currency', 'currency_symbol', 'symbol'];
  const displayFields = Object.entries(extraData).filter(([key]) => !skipFields.includes(key));

  if (displayFields.length === 0) {
    return null;
  }

  return (
    <div id="section-market-data" style={{ marginTop: 16 }}>
      <Collapse
        ghost
        defaultActiveKey={[]}
        items={[{
          key: 'market-data',
          label: (
            <span>
              <GlobalOutlined style={{ marginRight: 8 }} />
              市场额外数据
            </span>
          ),
          children: (
            <Descriptions bordered column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }} size="small">
              {displayFields.map(([key, value]) => (
                <Descriptions.Item key={key} label={createIndicatorLabel(key, 'extra')}>
                  {String(value)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          ),
        }]}
      />
    </div>
  );
};
