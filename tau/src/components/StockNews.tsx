/**
 * 股票新闻组件
 */
import React, { useEffect, useState } from 'react';
import { List, Card, Typography, Space, Tag, Spin, Empty, Button } from 'antd';
import { GlobalOutlined, ClockCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { getNews } from '../services/api';
import type { NewsItem } from '../types/index';
import dayjs from 'dayjs';

const { Text, Link } = Typography;

interface StockNewsProps {
  symbol: string;
  id?: string;
}

/**
 * 股票新闻组件
 */
export const StockNews: React.FC<StockNewsProps> = ({ symbol, id }) => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNewsData = async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getNews(symbol);
      if (response.success && response.data) {
        setNews(response.data);
      } else {
        setError(response.message || '获取新闻失败');
      }
    } catch (err: any) {
      setError(err.message || '获取新闻发生错误');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNewsData();
  }, [symbol]);

  const renderThumbnail = (item: NewsItem) => {
    if (!item.thumbnail || !item.thumbnail.resolutions || item.thumbnail.resolutions.length === 0) {
      return null;
    }
    // 找到合适分辨率的图片
    const thumb = item.thumbnail.resolutions.find(r => r.tag === '140x140') || item.thumbnail.resolutions[0];
    return (
      <img
        alt={item.title}
        src={thumb.url}
        style={{ width: 100, height: 70, objectFit: 'cover', borderRadius: 4, marginRight: 16 }}
      />
    );
  };

  if (loading && news.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Spin tip="加载新闻中..." />
      </div>
    );
  }

  if (error && news.length === 0) {
    return (
      <Card title="股票新闻" extra={<Button icon={<ReloadOutlined />} onClick={fetchNewsData} size="small">重试</Button>}>
        <Empty description={error} />
      </Card>
    );
  }

  return (
    <Card 
      id={id}
      title={
        <span>
          <GlobalOutlined style={{ marginRight: 8 }} />
          股票新闻
        </span>
      }
      extra={
        <Button 
          icon={<ReloadOutlined />} 
          onClick={fetchNewsData} 
          size="small" 
          loading={loading}
          type="text"
        >
          刷新
        </Button>
      }
      bodyStyle={{ padding: '0 24px' }}
      style={{ marginTop: 16 }}
    >
      <List
        itemLayout="horizontal"
        dataSource={news}
        renderItem={(item) => (
          <List.Item
            key={item.uuid}
            extra={renderThumbnail(item)}
            style={{ padding: '16px 0' }}
          >
            <List.Item.Meta
              title={
                <Link href={item.link} target="_blank" strong style={{ fontSize: '16px' }}>
                  {item.title}
                </Link>
              }
              description={
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Space split={<Text type="secondary">|</Text>}>
                    <Text type="secondary">{item.publisher}</Text>
                    <Space size={4}>
                      <ClockCircleOutlined style={{ fontSize: '12px', color: '#999' }} />
                      <Text type="secondary">
                        {dayjs(item.provider_publish_time * 1000).format('YYYY-MM-DD HH:mm')}
                      </Text>
                    </Space>
                    <Tag color="blue">{item.type}</Tag>
                  </Space>
                </Space>
              }
            />
          </List.Item>
        )}
        locale={{
          emptyText: <Empty description="暂无新闻数据" />
        }}
      />
    </Card>
  );
};
