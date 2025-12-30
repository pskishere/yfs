/**
 * 表格列配置
 */
import { Button, Tag } from 'antd';
import { CloseCircleOutlined } from '@ant-design/icons';
import type { Order } from '../types/index';
import { statusMaps } from '../utils/formatters';

/**
 * 持仓表格列定义
 * 
 * @returns Ant Design表格列配置数组
 */
export const getPositionColumns = (currencySymbol: string = '$') => [
  {
    title: '代码',
    dataIndex: 'symbol',
    key: 'symbol',
    align: 'left' as const,
    render: (text: string) => <strong>{text}</strong>,
  },
  {
    title: '数量',
    dataIndex: 'position',
    key: 'position',
    align: 'left' as const,
    render: (value: number | undefined) => value?.toFixed(0) || 0,
  },
  {
    title: '市价',
    dataIndex: 'marketPrice',
    key: 'marketPrice',
    align: 'left' as const,
    render: (value: number | undefined) => `${currencySymbol}${value?.toFixed(2) || '0.00'}`,
  },
  {
    title: '市值',
    dataIndex: 'marketValue',
    key: 'marketValue',
    align: 'left' as const,
    render: (value: number | undefined) => `${currencySymbol}${value?.toFixed(2) || '0.00'}`,
  },
  {
    title: '成本',
    dataIndex: 'averageCost',
    key: 'averageCost',
    align: 'left' as const,
    render: (value: number | undefined) => `${currencySymbol}${value?.toFixed(2) || '0.00'}`,
  },
  {
    title: '盈亏',
    dataIndex: 'unrealizedPNL',
    key: 'unrealizedPNL',
    align: 'left' as const,
    render: (value: number | undefined) => {
      const pnl = value || 0;
      return (
        <Tag color={pnl >= 0 ? 'success' : 'error'}>
          ${pnl.toFixed(2)}
        </Tag>
      );
    },
  },
];

/**
 * 订单表格列定义
 * 
 * @param handleCancelOrder - 撤销订单的处理函数
 * @returns Ant Design表格列配置数组
 */
export const getOrderColumns = (handleCancelOrder: (orderId: number) => void) => [
  {
    title: '订单ID',
    dataIndex: 'orderId',
    key: 'orderId',
    align: 'left' as const,
    render: (id: number) => `#${id}`,
  },
  {
    title: '代码',
    dataIndex: 'symbol',
    key: 'symbol',
    align: 'left' as const,
  },
  {
    title: '方向',
    dataIndex: 'action',
    key: 'action',
    align: 'left' as const,
    render: (action: string) => (
      <Tag color={action === 'BUY' ? 'green' : 'red'}>
        {action === 'BUY' ? '买入' : '卖出'}
      </Tag>
    ),
  },
  {
    title: '数量',
    dataIndex: 'totalQuantity',
    key: 'totalQuantity',
    align: 'left' as const,
    render: (qty: number | undefined) => qty?.toFixed(0) || 0,
  },
  {
    title: '类型',
    dataIndex: 'orderType',
    key: 'orderType',
    align: 'left' as const,
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    align: 'left' as const,
    render: (status: string) => {
      const config = statusMaps.order[status as keyof typeof statusMaps.order] || 
        { color: 'default', text: status };
      return <Tag color={config.color}>{config.text}</Tag>;
    },
  },
  {
    title: '已成交',
    dataIndex: 'filled',
    key: 'filled',
    align: 'left' as const,
    render: (filled: number | undefined) => filled?.toFixed(0) || 0,
  },
  {
    title: '操作',
    key: 'action',
    align: 'left' as const,
    render: (_: any, record: Order) => (
      record.status !== 'Filled' && record.status !== 'Cancelled' ? (
        <Button
          type="link"
          danger
          icon={<CloseCircleOutlined />}
          onClick={() => handleCancelOrder(record.orderId)}
        >
          撤销
        </Button>
      ) : null
    ),
  },
];
