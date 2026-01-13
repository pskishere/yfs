/**
 * 周期分析组件
 */
import React, { useState } from 'react';
import { Collapse, Descriptions, Space, Tag, Tabs, Table } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import { formatValue } from '../utils/formatters';

interface CycleAnalysisProps {
  analysisResult: AnalysisResult;
  currencySymbol: string;
  createIndicatorLabel: (label: string, indicatorKey: string) => React.ReactNode;
}

/**
 * 周期分析组件
 */
export const CycleAnalysis: React.FC<CycleAnalysisProps> = ({
  analysisResult,
  currencySymbol,
  createIndicatorLabel,
}) => {
  const formatCurrency = (value?: number, decimals: number = 2) =>
    `${currencySymbol}${formatValue(value ?? 0, decimals)}`;

  const indicators = analysisResult.indicators;

  // 分页状态
  const [cyclePeriodPageSize, setCyclePeriodPageSize] = useState<number>(10);
  const [cyclePeriodCurrent, setCyclePeriodCurrent] = useState<number>(1);
  const [yearlyCyclePageSize, setYearlyCyclePageSize] = useState<number>(10);
  const [yearlyCycleCurrent, setYearlyCycleCurrent] = useState<number>(1);
  const [monthlyCyclePageSize, setMonthlyCyclePageSize] = useState<number>(10);
  const [monthlyCycleCurrent, setMonthlyCycleCurrent] = useState<number>(1);

  // 如果没有周期分析数据，不显示
  if (indicators.dominant_cycle === undefined && indicators.avg_cycle_length === undefined) {
    return null;
  }

  /**
   * 渲染周期概述信息
   */
  const renderCycleOverview = () => {
    const items = [];

    // 平均周期
    if (indicators.avg_cycle_length !== undefined) {
      items.push({
        label: '平均周期',
        children: (
          <span style={{ fontSize: 14, fontWeight: 500 }}>
            {indicators.avg_cycle_length.toFixed(1)}天
          </span>
        ),
      });
    }

    // 周期稳定性评估
    if (indicators.cycle_stability) {
      items.push({
        label: '周期稳定性',
        children: (
          <Space size="small" orientation="vertical">
            <Tag
              color={
                indicators.cycle_stability === 'high' ? 'success' :
                  indicators.cycle_stability === 'medium' ? 'default' :
                    indicators.cycle_stability === 'low' ? 'warning' : 'error'
              }
              style={{ fontSize: 12 }}
            >
              {indicators.cycle_stability === 'high' ? '非常稳定' :
                indicators.cycle_stability === 'medium' ? '较为稳定' :
                  indicators.cycle_stability === 'low' ? '不够稳定' : '不稳定'}
            </Tag>
            {indicators.cycle_stability_desc && (
              <span style={{ fontSize: 11, color: '#999' }}>
                {indicators.cycle_stability_desc}
              </span>
            )}
          </Space>
        ),
      });
    }

    // 横盘判断或当前阶段
    if (indicators.sideways_market !== undefined) {
      if (indicators.sideways_market) {
        // 横盘状态
        items.push({
          label: '市场状态',
          children: (
            <Space size="small" direction="vertical" style={{ width: '100%' }}>
              <Tag color="orange" style={{ fontSize: 12 }}>横盘</Tag>
              {indicators.sideways_strength !== undefined && (
                <span style={{ fontSize: 11, color: '#999' }}>
                  强度: {(indicators.sideways_strength * 100).toFixed(0)}%
                </span>
              )}
              {indicators.sideways_amplitude_20 !== undefined && (
                <div style={{ fontSize: 11, color: '#666' }}>
                  20日振幅: {indicators.sideways_amplitude_20.toFixed(2)}%
                </div>
              )}
              {indicators.sideways_price_change_pct !== undefined && (
                <div style={{ fontSize: 11, color: '#666' }}>
                  20日价格变化: {indicators.sideways_price_change_pct.toFixed(2)}%
                </div>
              )}
              {indicators.sideways_price_range_pct !== undefined && (
                <div style={{ fontSize: 11, color: '#666' }}>
                  波动范围: {indicators.sideways_price_range_pct.toFixed(2)}%
                </div>
              )}
              {indicators.sideways_reasons && indicators.sideways_reasons.length > 0 && (
                <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>判断依据:</div>
                  {indicators.sideways_reasons.map((reason, idx) => (
                    <div key={idx} style={{ marginLeft: 8 }}>• {reason}</div>
                  ))}
                </div>
              )}
            </Space>
          ),
        });
      } else if (indicators.cycle_phase) {
        // 上涨或下跌阶段
        items.push({
          label: '市场状态',
          children: (
            <Space size="small" orientation="vertical">
              <Tag
                color={
                  indicators.cycle_phase === 'early_rise' ? 'success' :
                    indicators.cycle_phase === 'mid_rise' ? 'default' :
                      indicators.cycle_phase === 'late_rise' ? 'warning' : 'error'
                }
                style={{ fontSize: 12 }}
              >
                {indicators.cycle_phase === 'early_rise' ? '早期上涨' :
                  indicators.cycle_phase === 'mid_rise' ? '中期上涨' :
                    indicators.cycle_phase === 'late_rise' ? '后期上涨' : '下跌'}
              </Tag>
              {indicators.cycle_phase_desc && (
                <span style={{ fontSize: 11, color: '#999' }}>
                  {indicators.cycle_phase_desc}
                </span>
              )}
              {indicators.cycle_position !== undefined && (
                <div style={{ fontSize: 11, color: '#999' }}>
                  周期进度: {(indicators.cycle_position * 100).toFixed(0)}%
                  {indicators.days_from_last_trough !== undefined && (
                    <span style={{ marginLeft: 4 }}>
                      (距低点{indicators.days_from_last_trough}天)
                    </span>
                  )}
                </div>
              )}
              {indicators.cycle_suggestion && (
                <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                  {indicators.cycle_suggestion}
                </div>
              )}
            </Space>
          ),
        });
      }
    } else if (indicators.cycle_phase) {
      // 如果没有横盘判断但有阶段信息
      items.push({
        label: '市场状态',
        children: (
          <Space size="small" orientation="vertical">
            <Tag
              color={
                indicators.cycle_phase === 'early_rise' ? 'success' :
                  indicators.cycle_phase === 'mid_rise' ? 'default' :
                    indicators.cycle_phase === 'late_rise' ? 'warning' : 'error'
              }
              style={{ fontSize: 12 }}
            >
              {indicators.cycle_phase === 'early_rise' ? '早期上涨' :
                indicators.cycle_phase === 'mid_rise' ? '中期上涨' :
                  indicators.cycle_phase === 'late_rise' ? '后期上涨' : '下跌'}
            </Tag>
            {indicators.cycle_phase_desc && (
              <span style={{ fontSize: 11, color: '#999' }}>
                {indicators.cycle_phase_desc}
              </span>
            )}
            {indicators.cycle_position !== undefined && (
              <div style={{ fontSize: 11, color: '#999' }}>
                周期进度: {(indicators.cycle_position * 100).toFixed(0)}%
                {indicators.days_from_last_trough !== undefined && (
                  <span style={{ marginLeft: 4 }}>
                    (距低点{indicators.days_from_last_trough}天)
                  </span>
                )}
              </div>
            )}
            {indicators.cycle_suggestion && (
              <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                {indicators.cycle_suggestion}
              </div>
            )}
          </Space>
        ),
      });
    }

    // 多周期检测
    if (indicators.short_cycles || indicators.medium_cycles || indicators.long_cycles) {
      items.push({
        label: '多周期检测',
        span: 3,
        children: (
          <Space orientation="vertical" size="small" style={{ width: '100%' }}>
            {indicators.short_cycles && indicators.short_cycles.length > 0 && (
              <div>
                <span style={{ fontSize: 13, fontWeight: 500 }}>短周期: </span>
                {indicators.short_cycles.map((cycle, idx) => (
                  <Tag key={idx} style={{ marginRight: 4 }}>
                    {cycle}天
                  </Tag>
                ))}
                {indicators.short_cycle_strength !== undefined && (
                  <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                    强度: {(indicators.short_cycle_strength * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            )}
            {indicators.medium_cycles && indicators.medium_cycles.length > 0 && (
              <div>
                <span style={{ fontSize: 13, fontWeight: 500 }}>中周期: </span>
                {indicators.medium_cycles.map((cycle, idx) => (
                  <Tag key={idx} color="blue" style={{ marginRight: 4 }}>
                    {cycle}天
                  </Tag>
                ))}
                {indicators.medium_cycle_strength !== undefined && (
                  <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                    强度: {(indicators.medium_cycle_strength * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            )}
            {indicators.long_cycles && indicators.long_cycles.length > 0 && (
              <div>
                <span style={{ fontSize: 13, fontWeight: 500 }}>长周期: </span>
                {indicators.long_cycles.map((cycle, idx) => (
                  <Tag key={idx} color="purple" style={{ marginRight: 4 }}>
                    {cycle}天
                  </Tag>
                ))}
                {indicators.long_cycle_strength !== undefined && (
                  <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                    强度: {(indicators.long_cycle_strength * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            )}
          </Space>
        ),
      });
    }

    // 周期振幅
    if (indicators.avg_cycle_amplitude !== undefined) {
      items.push({
        label: '周期振幅',
        children: (
          <Space orientation="vertical" size="small">
            <span style={{ fontSize: 14, fontWeight: 500 }}>
              平均: {indicators.avg_cycle_amplitude.toFixed(2)}%
            </span>
            {indicators.max_cycle_amplitude !== undefined && indicators.min_cycle_amplitude !== undefined && (
              <span style={{ fontSize: 12, color: '#999' }}>
                范围: {indicators.min_cycle_amplitude.toFixed(2)}% - {indicators.max_cycle_amplitude.toFixed(2)}%
              </span>
            )}
          </Space>
        ),
      });
    }

    // 统计信息
    if (indicators.peak_count !== undefined || indicators.trough_count !== undefined) {
      items.push({
        label: '统计信息',
        children: (
          <Space orientation="vertical" size="small">
            <span style={{ fontSize: 13 }}>
              高点: <strong>{indicators.peak_count || 0}</strong>个
            </span>
            <span style={{ fontSize: 13 }}>
              低点: <strong>{indicators.trough_count || 0}</strong>个
            </span>
            {indicators.avg_peak_period !== undefined && (
              <span style={{ fontSize: 12, color: '#999' }}>
                高点平均周期: {indicators.avg_peak_period.toFixed(1)}天
              </span>
            )}
            {indicators.avg_trough_period !== undefined && (
              <span style={{ fontSize: 12, color: '#999' }}>
                低点平均周期: {indicators.avg_trough_period.toFixed(1)}天
              </span>
            )}
          </Space>
        ),
      });
    }

    return items;
  };

  /**
   * 渲染周期时间段表格
   */
  const renderCyclePeriodTable = () => {
    if (!indicators.cycle_periods || indicators.cycle_periods.length === 0) {
      return null;
    }

    return (
      <div style={{ overflowX: 'auto', width: '100%' }}>
        <Table
          dataSource={indicators.cycle_periods.slice().reverse()}
          columns={[
            {
              title: '周期类型',
              key: 'cycle_type',
              width: 100,
              fixed: 'left' as const,
              align: 'left' as const,
              render: (_: any, record: any) => {
                const isRise = record.cycle_type === 'rise';
                const isSideways = record.cycle_type === 'sideways';
                const isDecline = record.cycle_type === 'decline';
                
                let tagColor = 'default';
                if (isRise) tagColor = 'success';
                else if (isDecline) tagColor = 'error';
                else if (isSideways) tagColor = 'warning';
                
                return (
                  <Tag color={tagColor} style={{ fontSize: 12, fontWeight: 500 }}>
                    {record.cycle_type_desc || (isRise ? '上涨' : isDecline ? '下跌' : '横盘')}
                  </Tag>
                );
              },
            },
            {
              title: '起始日期',
              key: 'start_time',
              width: 120,
              render: (_: any, record: any) => {
                const timeStr = record.start_time;
                if (timeStr) {
                  return timeStr.split('T')[0].split(' ')[0];
                }
                if (analysisResult.candles && record.start_index < analysisResult.candles.length) {
                  const candle = analysisResult.candles[record.start_index];
                  if (candle && candle.time) {
                    return candle.time.split('T')[0].split(' ')[0];
                  }
                }
                return '-';
              },
            },
            {
              title: '起始价格',
              key: 'start_price',
              width: 120,
              render: (_: any, record: any) => {
                const isRise = record.cycle_type === 'rise';
                const isSideways = record.cycle_type === 'sideways';
                const isDecline = record.cycle_type === 'decline';
                
                let startPrice;
                if (isSideways) {
                  const amplitude = record.amplitude || 0;
                  startPrice = amplitude >= 0 ? record.low_price : record.high_price;
                } else if (isRise) {
                  startPrice = record.low_price;
                } else {
                  startPrice = record.high_price;
                }
                
                const color = isRise ? '#3f8600' : isDecline ? '#cf1322' : '#faad14';
                return (
                  <span style={{ fontWeight: 500, color: color }}>
                    {formatCurrency(startPrice)}
                  </span>
                );
              },
            },
            {
              title: '结束日期',
              key: 'end_time',
              width: 120,
              render: (_: any, record: any) => {
                const timeStr = record.end_time;
                if (timeStr) {
                  return timeStr.split('T')[0].split(' ')[0];
                }
                if (analysisResult.candles && record.end_index < analysisResult.candles.length) {
                  const candle = analysisResult.candles[record.end_index];
                  if (candle && candle.time) {
                    return candle.time.split('T')[0].split(' ')[0];
                  }
                }
                return '-';
              },
            },
            {
              title: '结束价格',
              key: 'end_price',
              width: 120,
              render: (_: any, record: any) => {
                const isRise = record.cycle_type === 'rise';
                const isSideways = record.cycle_type === 'sideways';
                const isDecline = record.cycle_type === 'decline';
                
                let endPrice;
                if (isSideways) {
                  const amplitude = record.amplitude || 0;
                  endPrice = amplitude >= 0 ? record.high_price : record.low_price;
                } else if (isRise) {
                  endPrice = record.high_price;
                } else {
                  endPrice = record.low_price;
                }
                
                const color = isRise ? '#cf1322' : isDecline ? '#3f8600' : '#faad14';
                return (
                  <span style={{ fontWeight: 500, color: color }}>
                    {formatCurrency(endPrice)}
                  </span>
                );
              },
            },
            {
              title: '持续天数',
              dataIndex: 'duration',
              key: 'duration',
              width: 80,
              align: 'left' as const,
              render: (val: number) => `${val}天`,
            },
            {
              title: '振幅',
              key: 'amplitude',
              width: 100,
              align: 'left' as const,
              render: (_: any, record: any) => {
                const isRise = record.cycle_type === 'rise';
                const isSideways = record.cycle_type === 'sideways';
                const isDecline = record.cycle_type === 'decline';
                
                let amplitude = record.amplitude;
                if (amplitude === undefined) {
                  const startPrice = isRise ? record.low_price : isDecline ? record.high_price : (record.low_price || record.high_price);
                  const endPrice = isRise ? record.high_price : isDecline ? record.low_price : (record.high_price || record.low_price);
                  amplitude = ((endPrice - startPrice) / startPrice) * 100;
                }
                
                let color = '#faad14';
                if (!isSideways) {
                  color = amplitude >= 0 ? '#cf1322' : '#3f8600';
                } else {
                  color = amplitude >= 0 ? '#faad14' : '#fa8c16';
                }
                
                return (
                  <span style={{ fontSize: 12, color: color }}>
                    {amplitude >= 0 ? '+' : ''}{amplitude.toFixed(2)}%
                  </span>
                );
              },
            },
          ]}
          pagination={{
            current: cyclePeriodCurrent,
            pageSize: cyclePeriodPageSize,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个周期`,
            pageSizeOptions: ['10', '20', '30', '50'],
            onChange: (page, pageSize) => {
              setCyclePeriodCurrent(page);
              setCyclePeriodPageSize(pageSize);
            },
            onShowSizeChange: (_current, size) => {
              setCyclePeriodCurrent(1);
              setCyclePeriodPageSize(size);
            },
            locale: {
              items_per_page: '条/页',
              jump_to: '跳至',
              page: '页',
            },
          }}
          size="small"
          style={{ fontSize: 12 }}
          scroll={{ x: 'max-content' }}
          rowKey={(record) => `period-${record.period_index || record.id || Math.random().toString()}`}
        />
      </div>
    );
  };

  /**
   * 渲染年周期表格
   */
  const renderYearlyCycleTable = () => {
    if (!indicators.yearly_cycles || indicators.yearly_cycles.length === 0) {
      return null;
    }

    return (
      <div style={{ overflowX: 'auto', width: '100%' }}>
        <Table
          dataSource={indicators.yearly_cycles.slice().reverse()}
          columns={[
            {
              title: '年份',
              dataIndex: 'year',
              key: 'year',
              width: 80,
              fixed: 'left' as const,
              align: 'left' as const,
              render: (year: number) => `${year}年`,
            },
            {
              title: '第一天',
              key: 'first_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.first_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '第一天收盘价',
              key: 'first_close',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => formatCurrency(record.first_close),
            },
            {
              title: '最后一天',
              key: 'last_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.last_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '最后一天收盘价',
              key: 'last_close',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => formatCurrency(record.last_close),
            },
            {
              title: '周期涨幅',
              key: 'first_to_last_change',
              width: 150,
              align: 'left' as const,
              render: (_: any, record: any) => {
                const change = record.first_to_last_change || 0;
                const color = change >= 0 ? '#cf1322' : '#3f8600';
                return (
                  <span style={{ color, fontWeight: 500 }}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </span>
                );
              },
            },
            {
              title: '最低价',
              key: 'min_low',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => record.min_low ? formatCurrency(record.min_low) : '-',
            },
            {
              title: '最低价日期',
              key: 'min_low_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.min_low_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '最高价',
              key: 'max_high',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => record.max_high ? formatCurrency(record.max_high) : '-',
            },
            {
              title: '最高价日期',
              key: 'max_high_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.max_high_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '最低到最高涨幅',
              key: 'low_to_high_change',
              width: 150,
              align: 'left' as const,
              render: (_: any, record: any) => {
                const change = record.low_to_high_change || 0;
                const color = '#cf1322';
                return (
                  <span style={{ color, fontWeight: 500 }}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </span>
                );
              },
            },
            {
              title: '交易日数',
              dataIndex: 'trading_days',
              key: 'trading_days',
              width: 100,
              align: 'left' as const,
              render: (days: number) => `${days}天`,
            },
          ]}
          pagination={{
            current: yearlyCycleCurrent,
            pageSize: yearlyCyclePageSize,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个年度`,
            pageSizeOptions: ['10', '20', '30', '50'],
            onChange: (page, pageSize) => {
              setYearlyCycleCurrent(page);
              setYearlyCyclePageSize(pageSize);
            },
            onShowSizeChange: (_current, size) => {
              setYearlyCycleCurrent(1);
              setYearlyCyclePageSize(size);
            },
            locale: {
              items_per_page: '条/页',
              jump_to: '跳至',
              page: '页',
            },
          }}
          size="small"
          style={{ fontSize: 12 }}
          scroll={{ x: 'max-content' }}
          rowKey={(record) => `yearly-${record.year}`}
        />
      </div>
    );
  };

  /**
   * 渲染月周期表格
   */
  const renderMonthlyCycleTable = () => {
    if (!indicators.monthly_cycles || indicators.monthly_cycles.length === 0) {
      return null;
    }

    return (
      <div style={{ overflowX: 'auto', width: '100%' }}>
        <Table
          dataSource={indicators.monthly_cycles.slice().reverse()}
          columns={[
            {
              title: '月份',
              key: 'year_month',
              width: 100,
              fixed: 'left' as const,
              align: 'left' as const,
              render: (_: any, record: any) => {
                if (record.month) {
                  const [year, month] = record.month.split('-');
                  return `${year}年${month}月`;
                }
                return '-';
              },
            },
            {
              title: '第一天',
              key: 'first_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.first_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '第一天收盘价',
              key: 'first_close',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => formatCurrency(record.first_close),
            },
            {
              title: '最后一天',
              key: 'last_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.last_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '最后一天收盘价',
              key: 'last_close',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => formatCurrency(record.last_close),
            },
            {
              title: '周期涨幅',
              key: 'first_to_last_change',
              width: 150,
              align: 'left' as const,
              render: (_: any, record: any) => {
                const change = record.first_to_last_change || 0;
                const color = change >= 0 ? '#cf1322' : '#3f8600';
                return (
                  <span style={{ color, fontWeight: 500 }}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </span>
                );
              },
            },
            {
              title: '最低价',
              key: 'min_low',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => record.min_low ? formatCurrency(record.min_low) : '-',
            },
            {
              title: '最低价日期',
              key: 'min_low_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.min_low_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '最高价',
              key: 'max_high',
              width: 120,
              align: 'left' as const,
              render: (_: any, record: any) => record.max_high ? formatCurrency(record.max_high) : '-',
            },
            {
              title: '最高价日期',
              key: 'max_high_date',
              width: 120,
              render: (_: any, record: any) => {
                const dateStr = record.max_high_date;
                if (dateStr) return dateStr.split('T')[0].split(' ')[0];
                return '-';
              },
            },
            {
              title: '最低到最高涨幅',
              key: 'low_to_high_change',
              width: 150,
              align: 'left' as const,
              render: (_: any, record: any) => {
                const change = record.low_to_high_change || 0;
                const color = '#cf1322';
                return (
                  <span style={{ color, fontWeight: 500 }}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </span>
                );
              },
            },
            {
              title: '交易日数',
              dataIndex: 'trading_days',
              key: 'trading_days',
              width: 100,
              align: 'left' as const,
              render: (days: number) => `${days}天`,
            },
          ]}
          pagination={{
            current: monthlyCycleCurrent,
            pageSize: monthlyCyclePageSize,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个月度`,
            pageSizeOptions: ['10', '20', '30', '50'],
            onChange: (page, pageSize) => {
              setMonthlyCycleCurrent(page);
              setMonthlyCyclePageSize(pageSize);
            },
            onShowSizeChange: (_current, size) => {
              setMonthlyCycleCurrent(1);
              setMonthlyCyclePageSize(size);
            },
            locale: {
              items_per_page: '条/页',
              jump_to: '跳至',
              page: '页',
            },
          }}
          size="small"
          style={{ fontSize: 12 }}
          scroll={{ x: 'max-content' }}
          rowKey={(record) => `monthly-${record.month}`}
        />
      </div>
    );
  };

  // 构建 Tabs 项
  const buildTabItems = () => {
    const tabItems = [];

    // 周期时间段表格
    if (indicators.cycle_periods && indicators.cycle_periods.length > 0) {
      tabItems.push({
        key: 'cycle-periods',
        label: `周期时间段 (${indicators.cycle_periods.length})`,
        children: renderCyclePeriodTable(),
      });
    }

    // 年周期表格
    if (indicators.yearly_cycles && indicators.yearly_cycles.length > 0) {
      tabItems.push({
        key: 'yearly-cycles',
        label: `年周期 (${indicators.yearly_cycles.length})`,
        children: renderYearlyCycleTable(),
      });
    }

    // 月周期表格
    if (indicators.monthly_cycles && indicators.monthly_cycles.length > 0) {
      tabItems.push({
        key: 'monthly-cycles',
        label: `月周期 (${indicators.monthly_cycles.length})`,
        children: renderMonthlyCycleTable(),
      });
    }

    return tabItems;
  };

  const tabItems = buildTabItems();

  return (
    <div id="section-cycle">
      <Collapse
        ghost
        defaultActiveKey={['cycle']}
        items={[{
          key: 'cycle',
          label: (
            <span>
              <BarChartOutlined style={{ marginRight: 8 }} />
              {createIndicatorLabel('周期分析', 'cycle')}
              {indicators.cycle_summary && (
                <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
                  {indicators.cycle_summary}
                </span>
              )}
            </span>
          ),
          children: (
            <div>
              {/* 周期概述 */}
              <Descriptions
                bordered
                column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                size="small"
                layout="horizontal"
                items={renderCycleOverview()}
              />
              
              {/* 周期表格 */}
              {tabItems.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Tabs
                    defaultActiveKey="cycle-periods"
                    items={tabItems}
                  />
                </div>
              )}
            </div>
          ),
        }]}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
