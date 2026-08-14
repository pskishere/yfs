/**
 * 会话列表抽屉组件 - 显示、切换和删除聊天会话
 */
import React, { useState, useEffect } from 'react';
import { Drawer, List, Button, Typography, Space, Tag, Popconfirm, message, Empty } from 'antd';
import { DeleteOutlined, MessageOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getChatSessions, deleteChatSession, type ChatSession } from '../services/api';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Text } = Typography;

interface ChatSessionDrawerProps {
  open: boolean;
  onClose: () => void;
  onSelectSession?: (sessionId?: string) => void;
}

const ChatSessionDrawer: React.FC<ChatSessionDrawerProps> = ({
  open,
  onClose,
  onSelectSession,
}) => {
  const [isMobile, setIsMobile] = useState<boolean>(typeof window !== 'undefined' && window.innerWidth <= 768);
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const { data: sessions = [], isFetching, refetch } = useQuery({
    queryKey: ['sessions'],
    queryFn: getChatSessions,
    enabled: open,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteChatSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      message.success(t('session.deleted'));
    },
    onError: () => {
      message.error(t('session.deleteFailed'));
    },
  });

  const handleCreateSession = () => {
    onClose();
    onSelectSession?.(undefined);
  };

  const handleOpenSession = (sessionId: string) => {
    onClose();
    onSelectSession?.(sessionId);
  };

  const getSessionTitle = (session: ChatSession): string => {
    if (session.title) return session.title;
    if (session.summary) return session.summary;
    if (session.context_symbols && session.context_symbols.length > 0) {
      let title = `关于 ${session.context_symbols.join(', ')} 的对话`;
      if (session.model) title += ` (${session.model})`;
      return title;
    }
    if (session.last_message) {
      const plainText = session.last_message.content
        .replace(/[#*`]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
      return plainText.slice(0, 30) + (plainText.length > 30 ? '...' : '');
    }
    const base = t('session.newTitle');
    return session.model ? `${base} (${session.model})` : base;
  };

  return (
    <Drawer
      title={
        <Space>
          <MessageOutlined />
          <span>{t('session.title')}</span>
        </Space>
      }
      placement="left"
      onClose={onClose}
      open={open}
      styles={{
        header: { paddingTop: 'calc(16px + var(--sat, 0px))' },
        body: { paddingBottom: 'calc(16px + var(--sab, 0px))' },
        wrapper: { width: isMobile ? '100%' : 360 },
      }}
      extra={
        <Space>
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            loading={isFetching}
            title={t('session.refresh')}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateSession} size="small">
            {t('session.new')}
          </Button>
        </Space>
      }
    >
      <List
        loading={isFetching}
        dataSource={sessions}
        locale={{
          emptyText: (
            <Empty description={t('session.empty')} image={Empty.PRESENTED_IMAGE_SIMPLE}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateSession}>
                {t('session.createFirst')}
              </Button>
            </Empty>
          ),
        }}
        renderItem={(session) => (
          <List.Item
            key={session.session_id}
            style={{
              cursor: 'pointer',
              background: 'transparent',
              borderRadius: 8,
              marginBottom: 8,
              padding: 12,
              border: '1px solid #f0f0f0',
              transition: 'all 0.3s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#f5f5f5';
              e.currentTarget.style.borderColor = '#d9d9d9';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.borderColor = '#f0f0f0';
            }}
            onClick={() => handleOpenSession(session.session_id)}
          >
            <List.Item.Meta
              title={
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text strong ellipsis>
                    {getSessionTitle(session)}
                  </Text>
                  <Space size={4} wrap>
                    <Tag color="blue" style={{ fontSize: 11 }}>
                      {t('session.messageCount', { count: session.message_count })}
                    </Tag>
                    {session.context_symbols?.slice(0, 3).map(symbol => (
                      <Tag key={symbol} style={{ fontSize: 11 }}>{symbol}</Tag>
                    ))}
                    {(session.context_symbols?.length ?? 0) > 3 && (
                      <Tag style={{ fontSize: 11 }}>+{session.context_symbols.length - 3}</Tag>
                    )}
                  </Space>
                </Space>
              }
              description={
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {dayjs(session.updated_at).fromNow()}
                </Text>
              }
            />
            <Popconfirm
              title={t('session.confirmDelete')}
              description={t('session.confirmDeleteDesc')}
              onConfirm={(e) => {
                e?.stopPropagation();
                deleteMutation.mutate(session.session_id);
              }}
              onCancel={(e) => e?.stopPropagation()}
              okText={t('session.ok')}
              cancelText={t('session.cancel')}
            >
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
                loading={deleteMutation.isPending && deleteMutation.variables === session.session_id}
                onClick={(e) => e.stopPropagation()}
              />
            </Popconfirm>
          </List.Item>
        )}
      />
    </Drawer>
  );
};

export default ChatSessionDrawer;
