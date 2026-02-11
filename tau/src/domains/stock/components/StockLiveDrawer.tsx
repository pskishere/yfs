import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Drawer, List, Tag, Typography, Empty, message, Button, Space } from 'antd';
import { LineChartOutlined, ReloadOutlined } from '@ant-design/icons';
import { StockWebSocketClient, type StockPriceUpdate } from '../../../services/stockWebsocket';

const { Text } = Typography;

interface StockLiveDrawerProps {
  open: boolean;
  onClose: () => void;
}

interface StockItem extends Partial<StockPriceUpdate> {
  symbol: string;
}

const StockLiveDrawer: React.FC<StockLiveDrawerProps> = ({ open, onClose }) => {
  const [stocks, setStocks] = useState<StockItem[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<StockWebSocketClient | null>(null);

  // 处理价格更新
  const handlePriceUpdate = useCallback((update: StockPriceUpdate) => {
    setStocks(prev => {
      // 如果列表中还没有这个股票（后端推流了新股票），则添加
      if (!prev.some(s => s.symbol === update.symbol)) {
        return [...prev, update];
      }
      // 否则更新已有股票的价格
      return prev.map(s => 
        s.symbol === update.symbol ? { ...s, ...update } : s
      );
    });
  }, []);

  // 处理订阅列表更新
  const handleSubscribed = useCallback((data: { symbols: string[], initial_data?: StockItem[] }) => {
    setStocks(prev => {
      // 如果后端提供了初始数据，直接使用
      if (data.initial_data && data.initial_data.length > 0) {
        return data.initial_data;
      }
      
      // 兜底逻辑：根据 symbols 初始化
      return data.symbols.map(symbol => {
        const existing = prev.find(s => s.symbol === symbol);
        return existing || { symbol };
      });
    });
  }, []);

  // 初始化 WebSocket
  useEffect(() => {
    if (open && !wsRef.current) {
      wsRef.current = new StockWebSocketClient({
        onConnect: () => {
          setConnected(true);
        },
        onSubscribed: handleSubscribed,
        onPriceUpdate: handlePriceUpdate,
        onError: (err: string) => message.error(`WebSocket错误: ${err}`),
        onClose: () => setConnected(false)
      });
      wsRef.current.connect();
    }
  }, [open, handlePriceUpdate, handleSubscribed]);

  const formatPrice = (price?: number) => {
    if (price === undefined) return '--';
    return price.toFixed(2);
  };

  const formatChange = (change?: number, pct?: number) => {
    if (change === undefined || pct === undefined) return null;
    const color = change >= 0 ? '#cf1322' : '#3f8600';
    const prefix = change >= 0 ? '+' : '';
    return (
      <Text style={{ color, fontSize: '12px' }}>
        {prefix}{change.toFixed(2)} ({prefix}{pct.toFixed(2)}%)
      </Text>
    );
  };

  const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;

  return (
    <Drawer
      title={
        <Space>
          <LineChartOutlined />
          <span>股票订阅</span>
          {connected ? (
            <Tag color="success">已连接</Tag>
          ) : (
            <Tag color="default">连接中...</Tag>
          )}
        </Space>
      }
      placement="left"
      onClose={onClose}
      open={open}
      width={isMobile ? '100%' : 360}
      styles={{
        header: {
          paddingTop: 'calc(16px + var(--sat, 0px))',
        },
        body: {
          paddingBottom: 'calc(24px + var(--sab, 0px))',
        }
      }}
      extra={
        <Button 
          type="text" 
          icon={<ReloadOutlined spin={!connected} />} 
          onClick={() => wsRef.current?.connect()} 
        />
      }
    >
      <List
        dataSource={stocks}
        locale={{ emptyText: <Empty description="暂无订阅股票或正在加载..." /> }}
        renderItem={item => (
          <List.Item>
            <List.Item.Meta
              title={<Text strong>{item.symbol}</Text>}
              description={formatChange(item.change, item.change_pct)}
            />
            <div style={{ textAlign: 'right' }}>
              <Text style={{ fontSize: '18px', fontWeight: 'bold' }}>
                {formatPrice(item.price)}
              </Text>
            </div>
          </List.Item>
        )}
      />
    </Drawer>
  );
};

export default StockLiveDrawer;
