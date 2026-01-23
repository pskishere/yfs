/**
 * 期权数据表格组件
 */
import React, { useState } from 'react';
import { Table, Tabs, Typography, Descriptions, Tag, Select } from 'antd';
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
  const [activeDate, setActiveDate] = useState<string | undefined>(
    data?.expiration_dates?.[0]
  );
  const [activeTab, setActiveTab] = useState<string>('calls');

  if (!data || !data.expiration_dates || data.expiration_dates.length === 0) {
    return null;
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

  const currentChain = activeDate ? data.chains[activeDate] : null;

  const tabItems = [
    {
      key: 'calls',
      label: `看涨期权 (Calls) ${currentChain ? `(${currentChain.calls.length})` : ''}`,
      children: (
        <Table
          dataSource={currentChain?.calls.map(item => ({ ...item, key: item.contractSymbol }))}
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
          dataSource={currentChain?.puts.map(item => ({ ...item, key: item.contractSymbol }))}
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
                >
                  {data.expiration_dates.slice(0, 10).map(date => (
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
