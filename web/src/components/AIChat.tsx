/**
 * AI 聊天组件 - 使用 @ant-design/x 实现股票分析聊天界面（完整版）
 */
import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Bubble, Sender, Welcome, Prompts } from '@ant-design/x';
import { Flex, notification, Button, Space, Tooltip, Modal, Input } from 'antd';
import { 
  StopOutlined, 
  ReloadOutlined, 
  EditOutlined
} from '@ant-design/icons';
import { wsClient, type ChatMessage } from '../services/websocket';
import ReactMarkdown from 'react-markdown';
import './AIChat.css';

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: 'pending' | 'streaming' | 'completed' | 'cancelled' | 'error';
}

/**
 * AI 聊天组件
 */
const AIChat: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [api, contextHolder] = notification.useNotification();

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初始化 WebSocket 连接
  useEffect(() => {
    const initConnection = async () => {
      try {
        // 从 URL 参数获取 session_id
        const sessionIdFromUrl = searchParams.get('session');
        
        // 设置回调函数
        wsClient.setCallbacks({
          onConnect: (sessionId) => {
            console.log('WebSocket 已连接，会话ID:', sessionId);
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
          },
          onGenerationStarted: (data) => {
            console.log('开始生成:', data);
            setIsStreaming(true);
            setCurrentStreamingId(data.message_id?.toString() || null);
          },
          onToken: (data) => {
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id === data.message_id?.toString()) {
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
          onGenerationCompleted: (data) => {
            setIsStreaming(false);
            setCurrentStreamingId(null);
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
            setCurrentStreamingId(null);
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
            setCurrentStreamingId(null);
            api.error({
              message: '生成失败',
              description: data.error || '未知错误'
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
              description: error
            });
          },
          onMessagesDeleted: (data) => {
            // 消息被删除后，更新消息列表
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
            // 消息更新后，刷新消息列表
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
            api.info({
              message: '正在重新生成回复',
              duration: 2
            });
          },
          onRegenerationStarted: (data) => {
            console.log('开始重新生成:', data);
            setIsStreaming(true);
            setCurrentStreamingId(data.message_id?.toString() || null);
            
            // 添加AI消息占位符
            const aiPlaceholder: MessageItem = {
              id: data.message_id?.toString() || `ai-${Date.now()}`,
              role: 'assistant',
              content: '',
              status: 'streaming'
            };
            setMessages(prev => [...prev, aiPlaceholder]);
          },
          onClose: () => {
            setIsConnected(false);
          },
        });

        await wsClient.connect(sessionIdFromUrl || undefined);
      } catch (error) {
        console.error('连接失败:', error);
        api.error({
          message: '连接失败',
          description: '无法连接到服务器，请刷新页面重试'
        });
      }
    };

    initConnection();

    return () => {
      wsClient.disconnect();
    };
  }, [searchParams]);

  /**
   * 发送消息
   */
  const handleSendMessage = (message: string) => {
    if (!message.trim() || !isConnected) {
      return;
    }

    // 先添加用户消息到界面
    const tempUserId = `user-${Date.now()}`;
    const userMessage: MessageItem = {
      id: tempUserId,
      role: 'user',
      content: message,
      status: 'completed'
    };

    setMessages(prev => [...prev, userMessage]);

    // 添加 AI 消息占位符
    const tempAiId = `ai-${Date.now()}`;
    const aiPlaceholder: MessageItem = {
      id: tempAiId,
      role: 'assistant',
      content: '',
      status: 'streaming'
    };

    setMessages(prev => [...prev, aiPlaceholder]);
    setIsStreaming(true);
    setCurrentStreamingId(tempAiId);

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

    const messageId = parseInt(editingMessageId);
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

  /**
   * 渲染消息内容
   */
  const renderMessageContent = (msg: MessageItem) => {
    const isAssistant = msg.role === 'assistant';
    const isUser = msg.role === 'user';
    const isCompleted = msg.status === 'completed';
    
    return (
      <div>
        {/* 消息内容 */}
        {isAssistant ? (
          <div className="markdown-content">
            <ReactMarkdown>{msg.content || '正在思考...'}</ReactMarkdown>
          </div>
        ) : (
          <div>{msg.content}</div>
        )}
        
        {/* 操作按钮 */}
        {isCompleted && (
          <Space size="small" style={{ marginTop: 8 }}>
            {/* 用户消息：编辑按钮 */}
            {isUser && (
              <Tooltip title="编辑消息">
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleStartEdit(msg)}
                />
              </Tooltip>
            )}
            
            {/* AI消息：重新生成按钮 */}
            {isAssistant && !isStreaming && (
              <Tooltip title="重新生成">
                <Button
                  type="text"
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={() => handleRegenerate(msg.id)}
                />
              </Tooltip>
            )}
          </Space>
        )}
      </div>
    );
  };

  // 欢迎提示
  const welcomeExtra = (
    <Prompts
      items={[
        { key: '1', label: '分析 AAPL 的技术指标' },
        { key: '2', label: '查看 TSLA 的最新价格和走势' },
        { key: '3', label: '比较 MSFT 和 GOOGL 的估值' },
        { key: '4', label: '推荐一些科技股' },
        { key: '5', label: '最近有哪些热门股票？' },
        { key: '6', label: '如何分析一只股票的基本面？' }
      ]}
      onItemClick={(info) => {
        handleSendMessage(info.data.label);
      }}
    />
  );

  return (
    <>
      {contextHolder}
      <Flex vertical className="ai-chat-container">
        {messages.length === 0 ? (
          <Welcome
            variant="borderless"
            icon="https://mdn.alipayobjects.com/huamei_iwk9zp/afts/img/A*s5sNRo5LjfQAAAAAAAAAAAAADgCCAQ/fmt.webp"
            title="股票 AI 分析助手"
            description="我可以帮你分析股票、查看实时数据、技术指标和提供投资建议"
            extra={welcomeExtra}
          />
        ) : (
          <div className="messages-container">
            <Bubble.List
              items={messages.map(msg => ({
                key: msg.id,
                role: msg.role,
                content: renderMessageContent(msg),
                status: msg.status
              }))}
            />
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="sender-container">
          <Sender
            placeholder={isConnected ? "输入消息，询问股票相关问题..." : "连接中..."}
            disabled={!isConnected || isStreaming}
            loading={isStreaming}
            onSubmit={handleSendMessage}
            actions={
              isStreaming ? (
                <div onClick={handleCancel} style={{ cursor: 'pointer', padding: '0 8px' }}>
                  <StopOutlined style={{ fontSize: 16, color: '#ff4d4f' }} />
                </div>
              ) : undefined
            }
          />
        </div>
      </Flex>

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

export default AIChat;
