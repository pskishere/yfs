/**
 * 聊天抽屉组件 - 参考 MobileChatPage 的布局设计
 */
import React, { useState, useEffect, useRef } from 'react';
import { Drawer, Button, Input, Space, notification, Modal, Tooltip, Empty, Flex, Divider, Tag } from 'antd';
import { Sender, ThoughtChain } from '@ant-design/x';
import {
  StopOutlined,
  EditOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { wsClient } from '../services/websocket';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatDrawer.css';

interface ChatDrawerProps {
  open: boolean;
  onClose: () => void;
  sessionId?: string;
  model?: string; // 当前选中的 AI 模型
}

interface ThoughtItem {
  key: string;
  title: string;
  status: 'loading' | 'success' | 'error' | 'pending';
}

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: 'pending' | 'streaming' | 'completed' | 'cancelled' | 'error';
  thoughts?: ThoughtItem[];
}

/**
 * 消息气泡组件
 */
const MessageBubble: React.FC<{
  message: MessageItem;
  onEdit?: (message: MessageItem) => void;
  onRegenerate?: (messageId: string) => void;
  isStreaming?: boolean;
}> = ({ message, onEdit, onRegenerate, isStreaming }) => {
  const isUser = message.role === 'user';
  const isCompleted = message.status === 'completed';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 16,
        gap: 8,
      }}
    >
      <div style={{ maxWidth: isUser ? '75%' : '100%', width: isUser ? 'auto' : '100%', display: 'flex', alignItems: 'flex-end', gap: 8, flexDirection: 'column' }}>
        <div style={{ display: 'flex', width: '100%', justifyContent: isUser ? 'flex-end' : 'flex-start', alignItems: 'flex-end', gap: 8 }}>
          {/* 消息气泡 */}
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 12,
              background: isUser ? '#e6f7ff' : '#f5f5f5',
              wordBreak: 'break-word',
              flex: isUser ? '0 1 auto' : '1 1 auto',
            }}
          >
            {message.role === 'assistant' ? (
              <div className="markdown-content">
                {/* 思维链展示 */}
                {message.thoughts && message.thoughts.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <ThoughtChain 
                      items={message.thoughts.map(t => ({
                        key: t.key,
                        title: t.title,
                        status: t.status === 'pending' ? 'loading' : t.status,
                        icon: t.status === 'loading' ? <LoadingOutlined spin /> : 
                               t.status === 'success' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : undefined
                      }))} 
                    />
                  </div>
                )}

                {(message.status === 'streaming' || message.status === 'pending') && !message.content && (!message.thoughts || message.thoughts.length === 0) ? (
                  <div className="thinking-dots">
                    <span className="thinking-dot"></span>
                    <span className="thinking-dot"></span>
                    <span className="thinking-dot"></span>
                  </div>
                ) : (
                  <>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    {message.status === 'streaming' && message.content && (
                      <span className="streaming-cursor"></span>
                    )}
                  </>
                )}
              </div>
            ) : (
              <div>{message.content}</div>
            )}
          </div>

          {/* 用户消息：编辑按钮 */}
          {isUser && isCompleted && onEdit && (
            <Tooltip title="编辑">
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => onEdit(message)}
                style={{ flexShrink: 0 }}
              />
            </Tooltip>
          )}

          {/* AI消息：重新生成按钮 */}
          {!isUser && isCompleted && onRegenerate && !isStreaming && (
            <Tooltip title="重新生成">
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => onRegenerate(message.id)}
                style={{ flexShrink: 0 }}
              />
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * 聊天抽屉组件
 */
const ChatDrawer: React.FC<ChatDrawerProps> = ({
  open,
  onClose,
  sessionId,
  model,
}) => {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const currentStreamingIdRef = useRef<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [api, contextHolder] = notification.useNotification();

  /**
   * 自动滚动到底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /**
   * 初始化 WebSocket 连接
   */
  useEffect(() => {
    if (!open) {
      return;
    }

    const initConnection = async () => {
      try {
        // 切换会话时，先清空当前消息列表，避免显示旧会话内容
        setMessages([]);
        setIsConnected(false);

        // 设置回调函数
        wsClient.setCallbacks({
          onConnect: (wsSessionId) => {
            console.log('WebSocket 已连接，会话ID:', wsSessionId);
            setIsConnected(true);
          },
          onHistory: (historyMessages) => {
            const formattedMessages: MessageItem[] = historyMessages.map((msg: any) => ({
              id: msg.id?.toString() || `msg-${Date.now()}`,
              role: msg.role,
              content: msg.content || '',
              status: msg.status || 'completed',
            }));
            setMessages(formattedMessages);
          },
          onMessageCreated: (data) => {
            console.log('消息已创建:', data);
            const userServerId = data.user_message_id?.toString();
            const aiServerId = data.ai_message_id?.toString();
            
            if (userServerId || aiServerId) {
              setMessages((prev) =>
                prev.map((msg) => {
                  // 如果是用户消息且没有正式 ID，更新为服务器返回的 user_message_id
                  if (msg.role === 'user' && msg.id.startsWith('user-') && userServerId) {
                    return { ...msg, id: userServerId };
                  }
                  // 如果是当前正在等待的 AI 消息，更新为服务器返回的 ai_message_id
                  if (msg.id === currentStreamingIdRef.current && aiServerId) {
                    currentStreamingIdRef.current = aiServerId;
                    return { ...msg, id: aiServerId };
                  }
                  return msg;
                })
              );
            }
          },
          onGenerationStarted: (data) => {
            console.log('开始生成:', data);
            setIsStreaming(true);
            const serverId = data.message_id?.toString() || null;
            if (serverId) {
              setMessages((prev) => {
                const exists = prev.some((msg) => msg.id === serverId);
                if (exists) {
                  return prev.map((msg) =>
                    msg.id === currentStreamingIdRef.current ? { ...msg, id: serverId } : msg
                  );
                } else {
                  // 如果消息不存在（如编辑后重新生成），则添加新消息
                  return [
                    ...prev,
                    {
                      id: serverId,
                      role: 'assistant',
                      content: '',
                      status: 'streaming',
                    },
                  ];
                }
              });
              currentStreamingIdRef.current = serverId;
            }
          },
          onToken: (data) => {
            const targetId = data.message_id?.toString() || currentStreamingIdRef.current || '';
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id === targetId) {
                  return {
                    ...msg,
                    content: msg.content + data.token,
                    status: 'streaming',
                  };
                }
                return msg;
              })
            );
          },
          onThought: (data) => {
            const targetId = data.message_id?.toString() || currentStreamingIdRef.current || '';
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id === targetId) {
                  const thoughts = [...(msg.thoughts || [])];
                  const existingThoughtIndex = thoughts.findIndex(t => t.key === data.tool);
                  
                  if (existingThoughtIndex > -1) {
                    thoughts[existingThoughtIndex] = {
                      ...thoughts[existingThoughtIndex],
                      title: data.thought,
                      status: data.status,
                    };
                  } else {
                    thoughts.push({
                      key: data.tool,
                      title: data.thought,
                      status: data.status,
                    });
                  }
                  
                  return {
                    ...msg,
                    thoughts,
                    status: 'streaming',
                  };
                }
                return msg;
              })
            );
          },
          onGenerationCompleted: (data) => {
            setIsStreaming(false);
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id === data.message_id?.toString()) {
                  return {
                    ...msg,
                    content: data.message,
                    status: 'completed',
                  };
                }
                return msg;
              })
            );
          },
          onGenerationCancelled: (data) => {
            setIsStreaming(false);
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id === data.message_id?.toString()) {
                  return {
                    ...msg,
                    status: 'cancelled',
                  };
                }
                return msg;
              })
            );
          },
          onGenerationError: (data) => {
            setIsStreaming(false);
            api.error({
              message: '生成失败',
              description: data.error || '未知错误',
            });
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id === data.message_id?.toString()) {
                  return {
                    ...msg,
                    status: 'error',
                    content: msg.content || '生成失败',
                  };
                }
                return msg;
              })
            );
          },
          onError: (error) => {
            api.error({
              message: '错误',
              description: error,
            });
          },
          onMessagesDeleted: (data) => {
            if (data.messages) {
              const formattedMessages: MessageItem[] = data.messages.map((msg: any) => ({
                id: msg.id?.toString() || `msg-${Date.now()}`,
                role: msg.role,
                content: msg.content || '',
                status: msg.status || 'completed',
              }));
              setMessages(formattedMessages);
            }
          },
          onMessagesUpdated: (data) => {
            if (data.messages) {
              const formattedMessages: MessageItem[] = data.messages.map((msg: any) => ({
                id: msg.id?.toString() || `msg-${Date.now()}`,
                role: msg.role,
                content: msg.content || '',
                status: msg.status || 'completed',
              }));
              setMessages(formattedMessages);
            }
          },
          onEditStarted: (data) => {
            console.log('开始编辑:', data);
            setIsStreaming(true);
            api.info({
              message: '正在重新生成回复',
              duration: 2,
            });
          },
          onRegenerationStarted: (data) => {
            console.log('开始重新生成:', data);
            setIsStreaming(true);

            // 添加AI消息占位符
            const aiPlaceholder: MessageItem = {
              id: data.message_id?.toString() || `ai-${Date.now()}`,
              role: 'assistant',
              content: '',
              status: 'streaming',
            };
            setMessages((prev) => [...prev, aiPlaceholder]);
          },
          onClose: () => {
            setIsConnected(false);
          },
        });

        // 连接 WebSocket
        await wsClient.connect(sessionId, model);
      } catch (error) {
        console.error('连接 WebSocket 失败:', error);
        api.error({
          message: '连接失败',
          description: '无法连接到聊天服务器',
        });
      }
    };

    initConnection();

    return () => {
      wsClient.disconnect();
    };
  }, [open, sessionId, model]);

  /**
   * 发送消息
   */
  const handleSendMessage = async (message: string) => {
    if (!message.trim() || !isConnected) return;

    const userMessage: MessageItem = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      status: 'completed',
    };

    const aiPlaceholder: MessageItem = {
      id: `ai-pending-${Date.now()}`,
      role: 'assistant',
      content: '',
      status: 'pending',
    };

    setMessages((prev) => [...prev, userMessage, aiPlaceholder]);
    currentStreamingIdRef.current = aiPlaceholder.id;
    setIsStreaming(true);
    setInputText('');

    // 发送到服务器
    wsClient.sendMessage(message);
  };

  /**
   * 重新生成
   */
  const handleRegenerate = (messageId?: string) => {
    if (!isConnected || isStreaming) {
      return;
    }

    const numId = messageId ? parseInt(messageId) : undefined;
    wsClient.regenerate(numId);
  };

  /**
   * 开始编辑消息
   */
  const handleStartEdit = (message: MessageItem) => {
    setEditingMessageId(message.id);
    setEditingContent(message.content);
  };

  /**
   * 确认编辑
   */
  const handleConfirmEdit = () => {
    if (!editingMessageId || !editingContent.trim()) {
      return;
    }

    // 尝试解析消息 ID，如果失败则报错
    const messageId = parseInt(editingMessageId);
    if (isNaN(messageId)) {
      console.error('无效的消息 ID:', editingMessageId);
      api.error({
        message: '编辑失败',
        description: '消息 ID 无效，无法编辑',
      });
      return;
    }

    wsClient.editMessage(messageId, editingContent.trim());

    // 关闭编辑框
    setEditingMessageId(null);
    setEditingContent('');
  };

  /**
   * 取消编辑
   */
  const handleCancelEdit = () => {
    setEditingMessageId(null);
    setEditingContent('');
  };

  /**
   * 取消生成
   */
  const handleCancel = () => {
    wsClient.cancelGeneration();
  };

  return (
    <>
      {contextHolder}
      <Drawer
        title={
          <Space>
            <span>AI 对话</span>
            {model && (
              <span style={{ fontSize: 12, color: '#8c8c8c', fontWeight: 'normal' }}>
                ({model})
              </span>
            )}
          </Space>
        }
        placement="right"
        size="large"
        onClose={onClose}
        open={open}
        styles={{
          body: {
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          },
        }}
      >
        {/* 消息列表区域 */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            background: '#fafafa',
          }}
        >
          {messages.length === 0 ? (
            <Empty
              description="开始对话吧"
              style={{ marginTop: 60 }}
              imageStyle={{ height: 80 }}
            >
              <p style={{ color: '#999', fontSize: 14 }}>
                输入消息询问股票相关问题
              </p>
            </Empty>
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onEdit={handleStartEdit}
                  onRegenerate={handleRegenerate}
                  isStreaming={isStreaming}
                />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* 输入区域 */}
        <div
          style={{
            borderTop: '1px solid #f0f0f0',
            padding: '12px 16px',
            background: '#fff',
          }}
        >
          <Sender
            className="chat-drawer-sender"
            placeholder={isConnected ? '输入消息，询问股票相关问题...' : '连接中...'}
            value={inputText}
            onChange={setInputText}
            onSubmit={handleSendMessage}
            disabled={!isConnected}
            loading={isStreaming}
            submitType="enter"
            autoSize={{ minRows: 1, maxRows: 6 }}
            footer={(actionNode: React.ReactNode) => {
              return (
                <Flex justify="space-between" align="center">
                  <Flex gap="small" align="center">
                    <div style={{ fontSize: 12, color: '#999' }}>
                      {isConnected ? (
                        <span>按 Enter 发送，Shift + Enter 换行</span>
                      ) : (
                        <span>连接中...</span>
                      )}
                    </div>
                  </Flex>
                  <Flex align="center">
                    {isStreaming ? (
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<StopOutlined />}
                        onClick={handleCancel}
                        style={{
                          borderRadius: '50%',
                          width: 40,
                          height: 40,
                          padding: 0,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                      }}
                    />
                  ) : (
                      <>
                        <Divider type="vertical" />
                        {actionNode}
                      </>
                    )}
                  </Flex>
                </Flex>
              );
            }}
            suffix={false}
            onCancel={handleCancel}
          />
        </div>
      </Drawer>

      {/* 编辑消息对话框 */}
      <Modal
        title="编辑消息"
        open={!!editingMessageId}
        onOk={handleConfirmEdit}
        onCancel={handleCancelEdit}
        okText="确认"
        cancelText="取消"
      >
        <Input.TextArea
          value={editingContent}
          onChange={(e) => setEditingContent(e.target.value)}
          rows={4}
          placeholder="修改消息内容..."
        />
        <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
          修改后将删除此消息之后的所有内容，并重新生成回复
        </div>
      </Modal>
    </>
  );
};

export default ChatDrawer;
