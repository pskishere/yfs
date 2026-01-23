import React, { useEffect, useState } from 'react';
import { Card, Typography, List, Alert, Button, Space, Table, Tag, message } from 'antd';
import { SmileOutlined, ThunderboltOutlined, ReloadOutlined, RobotOutlined, ApiOutlined } from '@ant-design/icons';
import { exampleService } from '../service';
import type { ExampleItem } from '../types';

const { Title, Paragraph } = Typography;

export const ExampleView: React.FC = () => {
  const [items, setItems] = useState<ExampleItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const data = await exampleService.getItems();
      setItems(data);
    } catch (error) {
      console.error('Failed to fetch items:', error);
      message.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleGenerateRandom = async () => {
    setActionLoading(true);
    try {
      await exampleService.generateRandomNumber({ min_val: 1, max_val: 1000 });
      message.success('Random number generated');
      fetchItems();
    } catch (error) {
      message.error('Operation failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCheckStatus = async () => {
    setActionLoading(true);
    try {
      await exampleService.checkSystemStatus();
      message.success('System status checked');
      fetchItems();
    } catch (error) {
      message.error('Operation failed');
    } finally {
      setActionLoading(false);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Type',
      dataIndex: 'item_type',
      key: 'item_type',
      render: (type: string) => (
        <Tag color={type === 'random_number' ? 'blue' : 'green'}>
          {type}
        </Tag>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
      render: (text: string) => (
        <span style={{ fontFamily: 'monospace' }}>{text}</span>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}><SmileOutlined /> Example Module</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchItems} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      <Alert
        message="System Verification"
        description="This module verifies the end-to-end flow. You can use the buttons below to trigger backend APIs directly, or ask the AI Agent to perform these tasks. Both actions will generate records in the history table below."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        <Card title={<span><ApiOutlined /> Direct API Testing</span>} bordered={false}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Paragraph>
              Call backend APIs directly from frontend.
            </Paragraph>
            <Space>
              <Button type="primary" onClick={handleGenerateRandom} loading={actionLoading}>
                Generate Random Number
              </Button>
              <Button onClick={handleCheckStatus} loading={actionLoading}>
                Check System Status
              </Button>
            </Space>
          </Space>
        </Card>

        <Card title={<span><RobotOutlined /> Agent Testing</span>} bordered={false}>
           <Paragraph>
              Ask the AI Agent:
            </Paragraph>
            <List
              size="small"
              dataSource={[
                '"Generate a random number between 1 and 100"',
                '"Check system status"'
              ]}
              renderItem={item => <List.Item><code>{item}</code></List.Item>}
            />
        </Card>
      </div>

      <Card title="Operation History" bordered={false}>
        <Table
          dataSource={items}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </Card>
    </div>
  );
};
