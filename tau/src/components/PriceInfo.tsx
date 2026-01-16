/**
 * 价格信息组件
 */
import React from 'react';
import { Collapse, Descriptions, Space, Tag } from 'antd';
import { BarChartOutlined, RiseOutlined, FallOutlined, RightOutlined } from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import { formatValue, statusMaps } from '../utils/formatters';

interface PriceInfoProps {
  analysisResult: AnalysisResult;
  currentSymbol: string;
  stockName: string;
  currencySymbol: string;
  createIndicatorLabel: (label: string, indicatorKey: string) => React.ReactNode;
}

/**
 * 获取趋势标签
 */
const getTrendTag = (direction: string | undefined): React.ReactNode => {
  const config = direction && statusMaps.trend[direction as keyof typeof statusMaps.trend]
    ? statusMaps.trend[direction as keyof typeof statusMaps.trend]
    : { color: 'default', text: direction || '未知' };
  
  const icon = direction === 'up' ? <RiseOutlined /> :
               direction === 'down' ? <FallOutlined /> :
               direction === 'neutral' ? <RightOutlined /> : null;
  
  return (
    <Tag color={config.color}>
      {icon} {config.text}
    </Tag>
  );
};

/**
 * 价格信息组件
 */
export const PriceInfo: React.FC<PriceInfoProps> = ({
  analysisResult,
  currentSymbol,
  stockName,
  currencySymbol,
  createIndicatorLabel,
}) => {
  const formatCurrency = (value?: number, decimals: number = 2) =>
    `${currencySymbol}${formatValue(value ?? 0, decimals)}`;

  return (
    <div id="section-price-info">
      <Collapse
        ghost
        defaultActiveKey={[]}
        items={[{
          key: 'price-info',
          label: (
            <span>
              <BarChartOutlined style={{ marginRight: 8 }} />
              价格信息
              {currentSymbol && (
                <span style={{ marginLeft: 8, color: '#595959', fontWeight: 500 }}>
                  {currentSymbol} {stockName ? `(${stockName})` : ''}
                </span>
              )}
            </span>
          ),
          children: (
            <Descriptions
              bordered
              column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
              size="small"
              layout="vertical"
              items={(() => {
                const items = [
                  {
                    label: '当前价格',
                    children: (
                      <span style={{ fontSize: 16, fontWeight: 600 }}>
                        {formatCurrency(analysisResult.indicators.current_price)}
                      </span>
                    ),
                  },
                  {
                    label: '价格变化',
                    children: (
                      <Space>
                        {(analysisResult.indicators.price_change_pct ?? 0) >= 0 ? (
                          <RiseOutlined style={{ color: '#3f8600' }} />
                        ) : (
                          <FallOutlined style={{ color: '#cf1322' }} />
                        )}
                        <span style={{
                          fontSize: 14,
                          fontWeight: 600,
                          color: (analysisResult.indicators.price_change_pct ?? 0) >= 0 ? '#3f8600' : '#cf1322',
                        }}>
                          {formatValue(analysisResult.indicators.price_change_pct)}%
                        </span>
                      </Space>
                    ),
                  },
                  {
                    label: '数据点数',
                    children: `${analysisResult.indicators.data_points || 0}条数据`,
                  },
                  {
                    label: '趋势方向',
                    children: getTrendTag(analysisResult.indicators.trend_direction),
                  },
                ];

                // 添加移动平均线
                const maItems = [5, 10, 20, 50]
                  .map((period) => {
                    const key = `ma${period}`;
                    const value = analysisResult.indicators[key];
                    if (value === undefined) return null as any;
                    const currentPrice = analysisResult.indicators.current_price || 0;
                    const diff = ((currentPrice - value) / value * 100);
                    return {
                      label: createIndicatorLabel(`MA${period}`, 'ma'),
                      children: (
                        <Space>
                          <span style={{
                            fontSize: 16,
                            fontWeight: 600,
                            color: diff >= 0 ? '#3f8600' : '#cf1322',
                          }}>
                            {formatCurrency(value)}
                          </span>
                          <span style={{
                            fontSize: 14,
                            color: diff >= 0 ? '#3f8600' : '#cf1322',
                          }}>
                            ({diff >= 0 ? '+' : ''}{diff.toFixed(1)}%)
                          </span>
                        </Space>
                      ),
                    };
                  })
                  .filter(item => item !== null);
                
                return [...items, ...maItems];
              })()}
            />
          ),
        }]}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
