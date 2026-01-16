/**
 * 最新新闻组件
 */
import React from 'react';
import { Collapse, Space, Typography, Pagination } from 'antd';
import { 
  FileTextOutlined,
  RightOutlined
} from '@ant-design/icons';
import type { AnalysisResult, NewsItem } from '../types/index';

interface NewsDataProps {
  analysisResult: AnalysisResult;
  newsPage?: number;
  setNewsPage?: (page: number) => void;
}

/**
 * 最新新闻组件
 */
export const NewsData: React.FC<NewsDataProps> = ({
  analysisResult,
  newsPage: propsNewsPage,
  setNewsPage: propsSetNewsPage,
}) => {
  const [internalNewsPage, setInternalNewsPage] = React.useState<number>(1);
  const newsPage = propsNewsPage !== undefined ? propsNewsPage : internalNewsPage;
  const setNewsPage = propsSetNewsPage !== undefined ? propsSetNewsPage : setInternalNewsPage;
  const newsPageSize = 30;

  const formatDateTime = (timestamp: number) => {
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(timestamp * 1000));
  };

  const newsData = analysisResult.indicators.news_data || [];

  // 检查是否有新闻数据
  if (!newsData || newsData.length === 0) {
    return null;
  }

  const currentNews = newsData.slice((newsPage - 1) * newsPageSize, newsPage * newsPageSize);
  
  const collapseItems = [
    {
      key: 'news',
      label: (
        <span>
          <FileTextOutlined style={{ marginRight: 8 }} />
          <span>最新新闻</span>
          <span style={{ color: '#8c8c8c', fontSize: '13px', marginLeft: 8 }}>
            ({newsData.length}条)
          </span>
        </span>
      ),
      children: (
        <div style={{ padding: '0 8px' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {currentNews.map((item: NewsItem, index: number) => (
              <div 
                key={index} 
                style={{ 
                  paddingBottom: 12, 
                  borderBottom: index === currentNews.length - 1 ? 'none' : '1px solid #f0f0f0',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start'
                }}
              >
                <div style={{ flex: 1, marginRight: 16 }}>
                  <Typography.Link 
                    href={item.link} 
                    target="_blank" 
                    style={{ fontSize: '15px', fontWeight: 500, display: 'block', marginBottom: 4 }}
                  >
                    {item.title}
                  </Typography.Link>
                  <Space split={<span style={{ color: '#d9d9d9' }}>|</span>} style={{ fontSize: '12px', color: '#8c8c8c' }}>
                    <span>{item.publisher}</span>
                    <span>{formatDateTime(item.provider_publish_time)}</span>
                  </Space>
                </div>
                <RightOutlined style={{ color: '#bfbfbf', marginTop: 4 }} />
              </div>
            ))}
          </Space>
          
          {newsData.length > newsPageSize && (
            <div style={{ textAlign: 'right', marginTop: 16 }}>
              <Pagination
                size="small"
                current={newsPage}
                total={newsData.length}
                pageSize={newsPageSize}
                onChange={(page) => setNewsPage(page)}
                showSizeChanger={false}
              />
            </div>
          )}
        </div>
      ),
    }
  ];

  return (
    <div id="section-news">
      <Collapse
        ghost
        defaultActiveKey={[]}
        items={collapseItems}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
