/**
 * 市场数据组件 - 分析师推荐、收益数据、新闻
 */
import React from 'react';
import { Collapse, Table, Tag, Pagination } from 'antd';
import {
  BarChartOutlined,
  MoneyCollectOutlined,
  FileTextOutlined,
  RightOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import { formatLargeNumber, translateRating, translateAction, formatDateTime } from '../utils/formatters';

interface MarketDataProps {
  analysisResult: AnalysisResult;
  newsPage: number;
  setNewsPage: (page: number) => void;
}

/**
 * 市场数据组件
 */
export const MarketData: React.FC<MarketDataProps> = ({
  analysisResult,
  newsPage,
  setNewsPage,
}) => {
  if (!analysisResult.extra_data) return null;

  const collapseItems = [];

  // 分析师推荐
  if (analysisResult.extra_data.analyst_recommendations && analysisResult.extra_data.analyst_recommendations.length > 0) {
    collapseItems.push({
      key: 'analyst',
      label: (
        <span>
          <BarChartOutlined style={{ marginRight: 8 }} />
          <span>分析师推荐</span> <span style={{ color: '#8c8c8c', fontSize: '13px' }}>(最近{analysisResult.extra_data.analyst_recommendations.length}条)</span>
        </span>
      ),
      children: (
        <Table
          size="small"
          pagination={{ pageSize: 10, showSizeChanger: false }}
          dataSource={analysisResult.extra_data.analyst_recommendations}
          rowKey={(record) => `${record.Firm || ''}-${record.Date || ''}-${record.id || Math.random().toString()}`}
          columns={[
            { 
              title: '日期', 
              dataIndex: 'Date', 
              key: 'date',
              width: '18%',
              render: (val: string) => (
                <span style={{ color: '#8c8c8c', fontSize: 12 }}>{val}</span>
              )
            },
            { 
              title: '机构', 
              dataIndex: 'Firm', 
              key: 'firm',
              width: '22%',
              render: (val: string) => (
                <span style={{ fontWeight: 500, fontSize: 13 }}>{val}</span>
              )
            },
            { 
              title: '原评级', 
              dataIndex: 'From Grade', 
              key: 'from',
              width: '20%',
              render: (val: string) => {
                if (!val) return <span style={{ color: '#bfbfbf' }}>-</span>;
                const lower = val.toLowerCase();
                const color = 
                  lower.includes('strong buy') || lower.includes('outperform') ? 'green' :
                  lower.includes('buy') || lower.includes('overweight') || lower.includes('positive') ? 'cyan' :
                  lower.includes('hold') || lower.includes('neutral') ? 'default' :
                  lower.includes('sell') || lower.includes('underperform') || lower.includes('underweight') ? 'red' : 'default';
                return (
                  <Tag color={color}>
                    {translateRating(val)}
                  </Tag>
                );
              }
            },
            { 
              title: '新评级', 
              dataIndex: 'To Grade', 
              key: 'to',
              width: '20%',
              render: (val: string) => {
                if (!val) return <span style={{ color: '#bfbfbf' }}>-</span>;
                const lower = val.toLowerCase();
                const color = 
                  lower.includes('strong buy') || lower.includes('outperform') ? 'green' :
                  lower.includes('buy') || lower.includes('overweight') || lower.includes('positive') ? 'cyan' :
                  lower.includes('hold') || lower.includes('neutral') ? 'default' :
                  lower.includes('sell') || lower.includes('underperform') || lower.includes('underweight') ? 'red' : 'default';
                return (
                  <Tag color={color} style={{ fontWeight: 600 }}>
                    {translateRating(val)}
                  </Tag>
                );
              }
            },
            { 
              title: '变化', 
              dataIndex: 'Action', 
              key: 'action',
              render: (val: string) => {
                if (!val) return '-';
                const lower = val.toLowerCase();
                const translated = translateAction(val);
                
                let color = 'default';
                let icon = null;
                
                if (lower.includes('up') || lower.includes('upgrade')) {
                  color = 'success';
                  icon = <RiseOutlined />;
                } else if (lower.includes('down') || lower.includes('downgrade')) {
                  color = 'error';
                  icon = <FallOutlined />;
                } else if (lower.includes('init') || lower.includes('main')) {
                  color = 'processing';
                }
                
                return (
                  <Tag color={color} icon={icon}>
                    {translated}
                  </Tag>
                );
              }
            },
          ]}
          scroll={{ x: 600 }}
        />
      ),
    });
  }

  // 收益数据
  if (analysisResult.extra_data.earnings?.quarterly && analysisResult.extra_data.earnings.quarterly.length > 0) {
    collapseItems.push({
      key: 'earnings',
      label: (
        <span>
          <MoneyCollectOutlined style={{ marginRight: 8 }} />
          <span>季度收益</span> <span style={{ color: '#8c8c8c', fontSize: '13px' }}>({analysisResult.extra_data.earnings.quarterly.length}个季度)</span>
        </span>
      ),
      children: (
        <Table
          size="small"
          pagination={false}
          dataSource={analysisResult.extra_data.earnings.quarterly}
          rowKey={(record) => record.quarter || record.id || Math.random().toString()}
          columns={[
            { 
              title: '季度', 
              dataIndex: 'quarter', 
              key: 'quarter',
              width: '35%',
              render: (val: string) => (
                <span style={{ fontWeight: 600 }}>{val}</span>
              )
            },
            { 
              title: '营收', 
              dataIndex: 'Revenue', 
              key: 'revenue',
              render: (val: number) => val ? (
                <span style={{ color: '#1890ff', fontWeight: 500 }}>
                  {formatLargeNumber(val)}
                </span>
              ) : '-'
            },
            { 
              title: '盈利', 
              dataIndex: 'Earnings', 
              key: 'earnings',
              render: (val: number) => val ? (
                <span style={{ color: val >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>
                  {formatLargeNumber(val)}
                </span>
              ) : '-'
            },
          ]}
        />
      ),
    });
  }

  // 新闻
  if (analysisResult.extra_data?.news && analysisResult.extra_data.news.length > 0) {
    collapseItems.push({
      key: 'news',
      label: (
        <span>
          <FileTextOutlined style={{ marginRight: 8 }} />
          <span>最新新闻</span> <span style={{ color: '#8c8c8c', fontSize: '13px' }}>({analysisResult.extra_data.news.length}条)</span>
        </span>
      ),
      children: (() => {
        const newsPageSize = 30;
        const allNews = analysisResult.extra_data.news || [];
        const totalNews = allNews.length;
        const startIndex = (newsPage - 1) * newsPageSize;
        const endIndex = startIndex + newsPageSize;
        const currentNews = allNews.slice(startIndex, endIndex);
        
        return (
          <div style={{ padding: '8px 0' }}>
            {currentNews.map((item, index) => (
              <div 
                key={startIndex + index} 
                style={{ 
                  marginBottom: 16, 
                  paddingBottom: 16, 
                  borderBottom: index < currentNews.length - 1 ? '1px solid #f0f0f0' : 'none',
                  transition: 'all 0.3s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#fafafa';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <div style={{ 
                  fontWeight: 600, 
                  marginBottom: 6,
                  fontSize: 14,
                  lineHeight: 1.5
                }}>
                  {item.link ? (
                    <a 
                      href={item.link} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{ 
                        color: '#1890ff',
                        textDecoration: 'none'
                      }}
                    >
                      <RightOutlined style={{ fontSize: 10, marginRight: 6 }} />
                      {item.title || item.headline || '无标题'}
                    </a>
                  ) : (
                    <span>
                      <RightOutlined style={{ fontSize: 10, marginRight: 6 }} />
                      {item.title || item.headline || '无标题'}
                    </span>
                  )}
                </div>
                <div style={{ 
                  fontSize: 12, 
                  color: '#8c8c8c',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}>
                  {item.publisher && (
                    <Tag color="blue" style={{ margin: 0 }}>
                      {item.publisher}
                    </Tag>
                  )}
                  {item.providerPublishTime && (
                    <span style={{ fontSize: 12 }}>
                      {formatDateTime(item.providerPublishTime)}
                    </span>
                  )}
                </div>
              </div>
            ))}
            
            {totalNews > newsPageSize && (
              <div style={{ 
                marginTop: 16, 
                display: 'flex', 
                justifyContent: 'center' 
              }}>
                <Pagination
                  current={newsPage}
                  pageSize={newsPageSize}
                  total={totalNews}
                  onChange={(page) => setNewsPage(page)}
                  showSizeChanger={false}
                  showTotal={(total) => `共 ${total} 条新闻`}
                  size="small"
                />
              </div>
            )}
          </div>
        );
      })(),
    });
  }

  if (collapseItems.length === 0) return null;

  return (
    <div>
      <Collapse
        ghost
        defaultActiveKey={[]}
        items={collapseItems}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
