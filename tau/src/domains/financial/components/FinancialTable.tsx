/**
 * 财务报表表格组件
 */
import React from 'react';
import { Table } from 'antd';
import { translateFinancialTerm } from '../../../utils/formatters';

interface FinancialTableProps {
  data: any[];
  currencySymbol?: string;
}

/**
 * 渲染财务数据
 * 
 * @param value - 财务数值
 * @returns 格式化后的字符串
 */
const renderFinancialValue = (value: any, currencySymbol: string): string => {
  if (value === null || value === undefined || value === '') return '-';
  const num = parseFloat(value);
  if (!isNaN(num)) {
    if (Math.abs(num) >= 1e9) {
      return `${currencySymbol}${(num / 1e9).toFixed(2)}B`;
    } else if (Math.abs(num) >= 1e6) {
      return `${currencySymbol}${(num / 1e6).toFixed(2)}M`;
    }
    return `${currencySymbol}${num.toFixed(2)}`;
  }
  return value;
};

/**
 * 生成表格列配置
 * 
 * @param firstRecord - 第一条记录，用于确定列结构
 * @returns Ant Design表格列配置数组
 */
const getColumns = (firstRecord: any, currencySymbol: string) => {
  const dateCol = firstRecord.index || firstRecord.Date ? {
    title: '日期',
    dataIndex: firstRecord.index ? 'index' : 'Date',
    key: 'date',
    width: 120,
    fixed: 'left' as const,
  } : null;

  const otherCols = Object.keys(firstRecord)
    .filter(key => key !== 'index' && key !== 'Date')
    .map(key => ({
      title: translateFinancialTerm(key),
      dataIndex: key,
      key: key,
      render: (value: any) => renderFinancialValue(value, currencySymbol),
    }));

  return dateCol ? [dateCol, ...otherCols] : otherCols;
};

/**
 * 财务报表表格组件
 */
export const FinancialTable: React.FC<FinancialTableProps> = ({ data, currencySymbol = '$' }) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return null;
  }

  const dataSource = data.map((record: any, index: number) => ({
    key: index,
    ...record,
  }));

  return (
    <Table
      size="small"
      bordered
      dataSource={dataSource}
      columns={getColumns(data[0], currencySymbol)}
      scroll={{ x: 'max-content' }}
      pagination={false}
    />
  );
};
