/**
 * 会话列表抽屉组件 - 显示、切换和删除聊天会话
 */
import React, { useState, useEffect } from 'react';
import { Drawer, List, Button, Typography, Space, Tag, Popconfirm, message, Empty } from 'antd';
import { DeleteOutlined, MessageOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
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

/**
 * 会话列表抽屉组件
 */
const ChatSessionDrawer: React.FC<ChatSessionDrawerProps> = ({
  open,
  onClose,
  onSelectSession,
}) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [isMobile, setIsMobile] = useState<boolean>(typeof window !== 'undefined' && window.innerWidth <= 768);
  const { t } = useTranslation();

  // 监听窗口大小变化
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  /**
   * 加载会话列表
   */
  const loadSessions = async () => {
    setLoading(true);
    try {
      const data = await getChatSessions();
      setSessions(data);
    } catch (error) {
      console.error('加载会话列表失败:', error);
      message.error(t('session.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  /**
   * 处理新建会话
   * 不再调用 API 创建会话，而是清空当前会话 ID，
   * 实际的会话创建将延迟到发送第一条消息时。
   */
  const handleCreateSession = () => {
    onClose();
    onSelectSession?.(undefined);
  };

  /**
   * 删除会话
   */
  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteChatSession(sessionId);
      message.success(t('session.deleted'));
      await loadSessions();
    } catch (error) {
      console.error('删除会话失败:', error);
      message.error(t('session.deleteFailed'));
    }
  };

  /**
   * 打开会话
   */
  const handleOpenSession = (sessionId: string) => {
    onClose();
    onSelectSession?.(sessionId);
  };

  /**
   * 获取会话标题
   */
  const getSessionTitle = (session: ChatSession): string => {
    if (session.title) {
      return session.title;
    }
    if (session.summary) {
      return session.summary;
    }
    if (session.context_symbols && session.context_symbols.length > 0) {
      let title = `关于 ${session.context_symbols.join(', ')} 的对话`;
      if (session.model) {
        title += ` (${session.model})`;
      }
      return title;
    }
    if (session.last_message) {
      const content = session.last_message.content;
      const plainText = content
        .replace(/[#*`]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
      return plainText.slice(0, 30) + (plainText.length > 30 ? '...' : '');
    }
    const base = t('session.newTitle');
    return session.model ? `${base} (${session.model})` : base;
  };

  useEffect(() => {
    if (open) {
      loadSessions();
    }
  }, [open]);

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
        header: {
          paddingTop: 'calc(16px + var(--sat, 0px))',
        },
        body: {
          paddingBottom: 'calc(16px + var(--sab, 0px))',
        },
        wrapper: {
          width: isMobile ? '100%' : 360
        }
      }}
      extra={
        <Space>
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={loadSessions}
            loading={loading}
            title={t('session.refresh')}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreateSession}
            size="small"
          >
            {t('session.new')}
          </Button>
        </Space>
      }
    >
      <List
        loading={loading}
        dataSource={sessions}
        locale={{
          emptyText: (
            <Empty
              description={t('session.empty')}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
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
                    {session.context_symbols && session.context_symbols.length > 0 && (
                      <>
                        {session.context_symbols.slice(0, 3).map(symbol => (
                          <Tag key={symbol} style={{ fontSize: 11 }}>
                            {symbol}
                          </Tag>
                        ))}
                        {session.context_symbols.length > 3 && (
                          <Tag style={{ fontSize: 11 }}>
                            +{session.context_symbols.length - 3}
                          </Tag>
                        )}
                      </>
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
                handleDeleteSession(session.session_id);
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
