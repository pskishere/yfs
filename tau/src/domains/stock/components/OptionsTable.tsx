/**
 * 期权数据表格组件
 */
import React, { useState } from 'react';
import { Table, Tabs, Typography, Descriptions, Tag, Select, Empty } from 'antd';
import type { OptionsData } from '../../../types/index';

const { Text } = Typography;
const { Option } = Select;

interface OptionsTableProps {
  data: OptionsData;
}

/**
 * 格式化数值
 */
const formatNumber = (value: number | undefined | null, precision = 2) => {
  if (value === null || value === undefined) return '-';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  });
};

/**
 * 格式化百分比
 */
const formatPercent = (value: number | undefined | null) => {
  if (value === null || value === undefined) return '-';
  const val = value * 100;
  return (
    <Text type={val > 0 ? 'danger' : val < 0 ? 'success' : undefined}>
      {val > 0 ? '+' : ''}{val.toFixed(2)}%
    </Text>
  );
};

export const OptionsTable: React.FC<OptionsTableProps> = ({ data }) => {
  // 兼容两种数据结构: OptionsData (多日期) 和 OptionsSummary (单日期汇总)
  const isSummary = 'current_expiry' in data && 'calls' in data;
  
  const [activeDate, setActiveDate] = useState<string | undefined>(
    isSummary ? (data as any).current_expiry : (data as any).expiration_dates?.[0]
  );
  const [activeTab, setActiveTab] = useState<string>('calls');

  const expirationDates = isSummary ? (data as any).expirations : (data as any).expiration_dates;

  if (!data || !expirationDates || expirationDates.length === 0) {
    return <Empty description="暂无期权数据" />;
  }

  const columns = [
    {
      title: '行权价',
      dataIndex: 'strike',
      key: 'strike',
      render: (val: number) => <strong>{formatNumber(val)}</strong>,
      fixed: 'left' as const,
      width: 100,
    },
    {
      title: '最新价',
      dataIndex: 'lastPrice',
      key: 'lastPrice',
      render: (val: number) => formatNumber(val),
    },
    {
      title: '涨跌幅',
      dataIndex: 'percentChange',
      key: 'percentChange',
      render: (val: number) => formatPercent(val / 100),
    },
    {
      title: '买入价',
      dataIndex: 'bid',
      key: 'bid',
      render: (val: number) => formatNumber(val),
    },
    {
      title: '卖出价',
      dataIndex: 'ask',
      key: 'ask',
      render: (val: number) => formatNumber(val),
    },
    {
      title: '成交量',
      dataIndex: 'volume',
      key: 'volume',
      render: (val: number) => val ? val.toLocaleString() : '-',
    },
    {
      title: '未平仓',
      dataIndex: 'openInterest',
      key: 'openInterest',
      render: (val: number) => val ? val.toLocaleString() : '-',
    },
    {
      title: '隐含波动率',
      dataIndex: 'impliedVolatility',
      key: 'impliedVolatility',
      render: (val: number) => `${(val * 100).toFixed(2)}%`,
    },
    {
      title: '状态',
      dataIndex: 'inTheMoney',
      key: 'inTheMoney',
      render: (inTheMoney: boolean) => (
        inTheMoney ? <Tag color="gold" style={{ fontSize: '10px' }}>价内</Tag> : <Tag style={{ fontSize: '10px' }}>价外</Tag>
      ),
    },
  ];

  const currentChain = isSummary 
    ? { calls: (data as any).calls, puts: (data as any).puts }
    : (activeDate ? (data as any).chains[activeDate] : null);

  const tabItems = [
    {
      key: 'calls',
      label: `看涨期权 (Calls) ${currentChain ? `(${currentChain.calls.length})` : ''}`,
      children: (
        <Table
          dataSource={currentChain?.calls.map((item: any) => ({ ...item, key: item.contractSymbol }))}
          columns={columns}
          size="small"
          pagination={{ pageSize: 10, size: 'small', showSizeChanger: false }}
          scroll={{ x: 800 }}
          bordered
          style={{ fontSize: '12px' }}
        />
      ),
    },
    {
      key: 'puts',
      label: `看跌期权 (Puts) ${currentChain ? `(${currentChain.puts.length})` : ''}`,
      children: (
        <Table
          dataSource={currentChain?.puts.map((item: any) => ({ ...item, key: item.contractSymbol }))}
          columns={columns}
          size="small"
          pagination={{ pageSize: 10, size: 'small', showSizeChanger: false }}
          scroll={{ x: 800 }}
          bordered
          style={{ fontSize: '12px' }}
        />
      ),
    },
  ];

  return (
    <div id="section-options">
      <div>
        <Descriptions
          column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
          size="small"
          layout="horizontal"
          items={[
            {
              label: '到期日',
              children: (
                <Select
                  size="small"
                  value={activeDate}
                  onChange={setActiveDate}
                  style={{ width: 140 }}
                  variant="borderless"
                  disabled={isSummary} // Summary 模式下暂时只支持单日期
                >
                  {expirationDates.slice(0, 10).map((date: string) => (
                    <Option key={date} value={date}>{date}</Option>
                  ))}
                </Select>
              ),
            },
            {
              label: '合约总数',
              children: (
                <span style={{ fontSize: 14, fontWeight: 500 }}>
                  {currentChain ? (currentChain.calls.length + currentChain.puts.length) : '-'}
                </span>
              ),
            },
            {
              label: '当前状态',
              children: (
                <Tag color="blue">{isSummary ? '最新到期日汇总' : '全量数据'}</Tag>
              )
            }
          ]}
        />

        <div style={{ marginTop: 16 }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="small"
            items={tabItems}
          />
        </div>
      </div>
    </div>
  );
};
