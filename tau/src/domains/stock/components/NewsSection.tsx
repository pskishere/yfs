import React from 'react';
import { List, Typography, Tag, Space, Image, Empty } from 'antd';
import { NewsItem } from '../../../types';
import dayjs from 'dayjs';

const { Title, Text, Link } = Typography;

interface NewsSectionProps {
  newsData: NewsItem[];
  currentSymbol: string;
}

const NewsSection: React.FC<NewsSectionProps> = ({ newsData, currentSymbol }) => {
  if (!newsData || newsData.length === 0) {
    return <Empty description="暂无相关新闻" />;
  }

  return (
    <div style={{ padding: '16px' }}>
      <Title level={4}>相关新闻 - {currentSymbol}</Title>
      <List
        itemLayout="vertical"
        size="large"
        dataSource={newsData}
        renderItem={(item) => (
          <List.Item
            key={item.uuid}
            extra={
              item.thumbnail && (
                <Image
                  width={200}
                  alt="thumbnail"
                  src={item.thumbnail}
                  fallback="https://via.placeholder.com/200x120?text=No+Image"
                />
              )
            }
          >
            <List.Item.Meta
              title={
                <Link href={item.link} target="_blank" rel="noopener noreferrer">
                  {item.title}
                </Link>
              }
              description={
                <Space split={<Text type="secondary">|</Text>}>
                  <Text strong>{item.publisher}</Text>
                  <Text type="secondary">
                    {dayjs(item.provider_publish_time * 1000).format('YYYY-MM-DD HH:mm')}
                  </Text>
                  <Tag color="blue">{item.type}</Tag>
                </Space>
              }
            />
            {item.related_tickers && item.related_tickers.length > 0 && (
              <div style={{ marginTop: '8px' }}>
                <Text type="secondary" style={{ marginRight: '8px' }}>相关股票:</Text>
                <Space wrap>
                  {item.related_tickers.map((ticker) => (
                    <Tag key={ticker} color={ticker === currentSymbol ? 'gold' : 'default'}>
                      {ticker}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
          </List.Item>
        )}
      />
    </div>
  );
};

export default NewsSection;
