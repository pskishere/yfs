/**
 * 聊天抽屉组件 - 参考 MobileChatPage 的布局设计
 */
import React, { useState, useEffect, useRef } from 'react';
import { Drawer, Button, notification, Empty, Flex, GetRef, Dropdown, Tag, type MenuProps, type GetProp, Badge } from 'antd';
import { Sender, ThoughtChain, type SenderProps, Attachments, type AttachmentsProps } from '@ant-design/x';
import {
  StopOutlined,
  EditOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  LineChartOutlined,
  HistoryOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  ReadOutlined,
  FundOutlined,
  ThunderboltOutlined,
  CloudUploadOutlined,
  FileImageOutlined,
  FileWordOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { wsClient } from '../services/websocket';
import { createChatSession, uploadFile } from '../services/api';
import { getSubscriptions } from '../domains/stock/service';
import { registry } from '../framework/core/registry';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ComponentRenderer from './ComponentRenderer';
import ComponentDrawer from './ComponentDrawer';
import './ChatDrawer.css';

interface ChatDrawerProps {
  open: boolean;
  onClose: () => void;
  sessionId?: string;
  model?: string; // 当前选中的 AI 模型
  onSessionCreated?: (sessionId: string) => void;
}

interface ThoughtItem {
  key: string;
  title: string;
  status: 'loading' | 'success' | 'error' | 'pending' | 'streaming';
}

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: 'pending' | 'streaming' | 'completed' | 'cancelled' | 'error';
  thoughts?: ThoughtItem[];
}

interface ChatPanelProps {
  active: boolean;
  sessionId?: string;
  model?: string;
  onSessionCreated?: (sessionId: string) => void;
}

const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState<boolean>(
    typeof window !== 'undefined' && window.innerWidth <= 768
  );

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
};

/**
 * 消息气泡组件
 */
const MessageBubble: React.FC<{
  message: MessageItem;
  onEdit?: (message: MessageItem) => void;
  onRegenerate?: (messageId: string) => void;
  isStreaming?: boolean;
  onOpenComponentDrawer?: (symbol: string, module: string) => void;
}> = ({ message, onEdit, onRegenerate, isStreaming, onOpenComponentDrawer }) => {
  const isUser = message.role === 'user';
  const isCompleted = message.status === 'completed';

  // 快捷指令配置（用于渲染用户消息中的标签）
  const suggestionItems = registry.getSuggestions();

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 16,
        gap: 8,
      }}
    >
      <div style={{ 
        maxWidth: isUser ? '75%' : '100%', 
        width: isUser ? 'auto' : '100%', 
        display: 'flex', 
        alignItems: isUser ? 'flex-end' : 'flex-start', 
        gap: 8, 
        flexDirection: 'column',
        minWidth: 0 // 防止 flex 子元素溢出
      }}>
        <div style={{ display: 'flex', width: '100%', justifyContent: isUser ? 'flex-end' : 'flex-start', alignItems: 'flex-end', gap: 8 }}>
          <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 8 }}>
            {/* 思维链展示 - 移到气泡外 */}
            {message.role === 'assistant' && message.thoughts && message.thoughts.length > 0 && (
              <div style={{ marginBottom: 4, width: '100%' }}>
                <ThoughtChain 
                  items={message.thoughts.map(t => {
                    const isLoading = t.status !== 'success' && t.status !== 'error';
                    return {
                      key: t.key,
                      title: t.title || (isLoading ? '正在处理...' : ''),
                      status: isLoading ? 'loading' : (t.status as any),
                      icon: isLoading ? <LoadingOutlined spin /> : 
                             t.status === 'success' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : undefined
                    };
                  })} 
                />
              </div>
            )}
            
            {/* 消息气泡 */}
            <div
              style={{
                padding: '8px 12px',
                borderRadius: 12,
                background: isUser ? '#e6f7ff' : '#f5f5f5',
                wordBreak: 'break-word',
                alignSelf: isUser ? 'flex-end' : 'stretch',
                width: isUser ? 'auto' : '100%',
                maxWidth: '100%',
                minWidth: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 4
              }}
            >
              {message.role === 'assistant' ? (
                <div className="markdown-content">
                  {(message.status === 'streaming' || message.status === 'pending') && !message.content ? (
                    <div className="thinking-dots">
                      <span className="thinking-dot"></span>
                      <span className="thinking-dot"></span>
                      <span className="thinking-dot"></span>
                    </div>
                  ) : (
                    <>
                      {(() => {
                        const content = message.content;
                        const regex = /(?:<|\[)(?:stock-analysis|股票分析)\s+symbol=["']([^"']+)["']\s+module=["']([^"']+)["']\s*\/?(?:>|\])/gi;
                        const parts = [];
                        let lastIndex = 0;
                        let match;

                        while ((match = regex.exec(content)) !== null) {
                          if (match.index > lastIndex) {
                            const text = content.substring(lastIndex, match.index).trim();
                            if (text && text !== '```' && text !== '```markdown') {
                              parts.push(
                                <ReactMarkdown key={`text-${lastIndex}`} remarkPlugins={[remarkGfm]}>
                                  {text}
                                </ReactMarkdown>
                              );
                            }
                          }

                          parts.push(
                            <ComponentRenderer
                              key={`stock-${match.index}`}
                              symbol={match[1]}
                              module={match[2]}
                              onOpen={onOpenComponentDrawer || (() => {})}
                            />
                          );

                          lastIndex = regex.lastIndex;
                        }

                        if (lastIndex < content.length) {
                          const text = content.substring(lastIndex).trim();
                          if (text && text !== '```') {
                            parts.push(
                              <ReactMarkdown key={`text-${lastIndex}`} remarkPlugins={[remarkGfm]}>
                                {text}
                              </ReactMarkdown>
                            );
                          }
                        }

                        return parts.length > 0 ? parts : (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                        );
                      })()}
                      {message.status === 'streaming' && message.content && (
                        <span className="streaming-cursor"></span>
                      )}
                    </>
                  )}
                </div>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
                  {(() => {
                    const content = message.content;
                // 简单的关键字匹配来显示标签，不依赖严格的指令格式
                for (const item of suggestionItems) {
                  if (content.includes(item.label) || content.includes(item.value)) {
                    return (
                      <>
                        <span style={{ 
                          background: '#f6ffed', 
                          border: '1px solid #b7eb8f', 
                          color: '#389e0d',
                          padding: '0 8px',
                          borderRadius: 4,
                          fontSize: 12,
                          height: 22,
                          lineHeight: '20px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          flexShrink: 0
                        }}>
                          {item.label}
                        </span>
                        {/* 去除指令前缀，如 "/期权链 " */}
                        <span>{content.replace(new RegExp(`^/?${item.value}\\s*`), '')}</span>
                      </>
                    );
                  }
                }
                return content;
                  })()}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 消息下方的操作按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%', marginTop: 4 }}>
          {/* 用户消息：编辑按钮 */}
          {isUser && isCompleted && onEdit && (
            <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => onEdit(message)}
              />
          )}

          {/* AI消息：重新生成按钮 */}
          {!isUser && isCompleted && onRegenerate && !isStreaming && (
            <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => onRegenerate(message.id)}
              />
          )}
        </div>
      </div>
    </div>
  );
};

const ChatPanel: React.FC<ChatPanelProps> = ({
  active,
  sessionId,
  model,
  onSessionCreated,
}) => {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const currentStreamingIdRef = useRef<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const senderRef = useRef<GetRef<typeof Sender>>(null);
  const [activeSkill, setActiveSkill] = useState<SenderProps['skill']>(undefined);
  const [slotConfig, setSlotConfig] = useState<SenderProps['slotConfig']>(undefined);
  const [subscriptions, setSubscriptions] = useState<string[]>([]);
  const [attachments, setAttachments] = useState<GetProp<AttachmentsProps, 'items'>>([]);
  const [openAttachments, setOpenAttachments] = useState(false);
  const attachmentsRef = useRef<GetRef<typeof Attachments>>(null);
  const skipNextChange = useRef(false);
  const [api, contextHolder] = notification.useNotification();
  
  // 组件详情抽屉状态
  const [drawerState, setDrawerState] = useState<{
    open: boolean;
    symbol: string;
    module: string;
  }>({ open: false, symbol: '', module: '' });

  const handleOpenComponentDrawer = (symbol: string, module: string) => {
    setDrawerState({ open: true, symbol, module });
  };

  // 获取订阅股票
  const fetchSubscriptions = async () => {
    try {
      const res = await getSubscriptions();
      if (res.success && res.stocks) {
        const options = res.stocks.map((s: any) => s.symbol);
        setSubscriptions(options);
      }
    } catch (err) {
      console.error('获取订阅股票失败:', err);
    }
  };

  useEffect(() => {
    fetchSubscriptions();
  }, []);

  // 当 subscriptions 更新时，如果当前有激活的技能，更新其 slotConfig 以反映最新的股票列表
  useEffect(() => {
    if (activeSkill && activeSkill.value) {
      const item = commandSuggestions.find(i => i.value === activeSkill.value);
      if (item) {
        setSlotConfig(item.slotConfig as any);
      }
    }
  }, [subscriptions]); // 依赖 subscriptions 更新


  // 股票下拉选项
  const stockOptions = (Array.isArray(subscriptions) ? subscriptions : [])
    .filter(s => typeof s === 'string');

  // 快捷指令配置
  const commandSuggestions = [
    {
      label: 'K线图表',
      value: 'K线图表',
      icon: <LineChartOutlined />,
      extra: '展示交互式 K 线图',
      skill: {
        value: 'K线图表',
        label: 'K线图表',
        icon: <LineChartOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '查看 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: stockOptions,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的 K 线图表。' },
      ],
    },
    {
      label: '新闻资讯',
      value: '新闻资讯',
      icon: <ReadOutlined />,
      extra: '查询股票最新新闻资讯',
      skill: {
        value: '新闻资讯',
        label: '新闻资讯',
        icon: <ReadOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '查看 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: stockOptions,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的最新新闻。' },
      ],
    },
    {
      label: '技术指标',
      value: '技术指标',
      icon: <ThunderboltOutlined />,
      extra: '分析股票各项技术指标',
      skill: {
        value: '技术指标',
        label: '技术指标',
        icon: <ThunderboltOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '分析 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: stockOptions,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的技术指标。' },
      ],
    },
    {
      label: '周期分析',
      value: '周期分析',
      icon: <HistoryOutlined />,
      extra: '分析股票的时间周期规律',
      skill: {
        value: '周期分析',
        label: '周期分析',
        icon: <HistoryOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '对 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: stockOptions,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 进行周期性规律分析。' },
      ],
    },
    {
      label: '期权链',
      value: '期权链',
      icon: <DatabaseOutlined />,
      extra: '展示期权行权价与波动率',
      skill: {
        value: '期权链',
        label: '期权链',
        icon: <DatabaseOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '查看 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: stockOptions,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的期权链信息。' },
      ],
    },
    {
      label: '基本面',
      value: '基本面',
      icon: <FundOutlined />,
      extra: '分析股票基本面数据',
      skill: {
        value: '基本面',
        label: '基本面',
        icon: <FundOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '分析 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: stockOptions,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的基本面数据。' },
      ],
    },
  ];

  /**
   * 自动滚动到底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!active) {
      return;
    }

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
          thoughts: msg.thoughts || [],
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
            thoughts: msg.thoughts || [],
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
            thoughts: msg.thoughts || [],
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

    // 如果没有 sessionId，说明是新会话，我们推迟到发送第一条消息时再连接
    if (!sessionId) {
      setMessages([]);
      setIsConnected(false);
      return;
    }

    const initConnection = async () => {
      try {
        // 只有在切换到一个不同的、非空的会话时，才清空消息列表
        // 如果是从 undefined 变更为当前正在连接的会话，则不清空（因为 handleSendMessage 已经添加了消息）
        if (wsClient.getSessionId() !== sessionId) {
          setMessages([]);
          setIsConnected(false);
        }

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
      // 如果当前是从新会话（undefined）升级到真实会话，且连接已经建立，则不要断开
      // 否则在发送第一条消息后，sessionId 变更会导致连接被异常断开
      const currentWsSessionId = wsClient.getSessionId();
      if (active && sessionId === undefined && currentWsSessionId !== null) {
        return;
      }
      wsClient.disconnect();
    };
  }, [active, sessionId, model]);

  const handleSendMessage = async (message: string, _event?: any, skill?: any) => {
    // 如果有附件，将附件信息添加到消息中
    let finalMessage = message;
    if (attachments.length > 0) {
      const attachmentText = attachments.map(item => {
        // @ts-ignore
        return `[Attachment: ${item.name}](${item.url})`;
      }).join('\n');
      finalMessage = `${message}\n\n${attachmentText}`.trim();
    }

    if (!finalMessage.trim() && !skill && !activeSkill) return;

    // 如果还没有连接，说明是第一次发送消息（或者是连接断开了）
    if (!isConnected || !wsClient.isConnected()) {
      try {
        setIsStreaming(true); // 显示加载状态
        
        let targetSessionId = sessionId;
        
        // 如果没有 sessionId，先创建会话
        if (!targetSessionId) {
          try {
            const session = await createChatSession(model);
            targetSessionId = session.session_id;
            // 通知父组件更新 session_id
            if (onSessionCreated) {
              onSessionCreated(targetSessionId);
            }
          } catch (error) {
            console.error('创建会话失败:', error);
            throw error;
          }
        }
        
        await wsClient.connect(targetSessionId, model);
        setIsConnected(true);
      } catch (error) {
        setIsStreaming(false);
        // 错误已经在 wsClient.connect 或 onError 回调中处理
        return;
      }
    }

    const finalSkill = skill || activeSkill;
    const fullMessage = finalSkill ? `/${finalSkill.value} ${finalMessage}` : finalMessage;

    // 如果处于编辑模式
    if (editingMessageId) {
      const numId = parseInt(editingMessageId);
      if (!isNaN(numId)) {
        wsClient.editMessage(numId, fullMessage);
      }
      setEditingMessageId(null);
      setInputText('');
      setAttachments([]);
      setOpenAttachments(false);
      setActiveSkill(undefined);
      setSlotConfig(undefined);
      return;
    }

    const userMessage: MessageItem = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: fullMessage,
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
    setAttachments([]);
    setOpenAttachments(false);

    // 发送到服务器
    wsClient.sendMessage(fullMessage);
    setActiveSkill(undefined);
    setSlotConfig(undefined);
  };

  // 简化版文件处理
  const handleUploadChange: AttachmentsProps['onChange'] = async ({ file }) => {
    if (file.status === 'removed') {
        setAttachments(prev => prev.filter(item => item.uid !== file.uid));
        return;
    }
    
    // 添加新文件占位
    if (!attachments.some(item => item.uid === file.uid)) {
        // 确保有文件对象
        const fileObj = file.originFileObj || (file as unknown as File);
        if (!fileObj) {
            console.error('No file object found', file);
            return;
        }

        setAttachments(prev => [...prev, {
            uid: file.uid,
            name: file.name,
            status: 'uploading',
        }]);
        
        try {
            console.log('Uploading file:', fileObj);
            const result = await uploadFile(fileObj as File);
            setAttachments(prev => prev.map(item => {
                if (item.uid === file.uid) {
                    return {
                        ...item,
                        status: 'done',
                        url: result.url,
                        // @ts-ignore
                        path: result.path,
                    };
                }
                return item;
            }));
        } catch (error) {
             console.error('Upload failed:', error);
             setAttachments(prev => prev.map(item => {
                if (item.uid === file.uid) {
                    return {
                        ...item,
                        status: 'error',
                    };
                }
                return item;
            }));
        }
    }
  };

  // 自动打开附件面板当有附件时
  useEffect(() => {
    if (attachments.length > 0) {
      setOpenAttachments(true);
    }
  }, [attachments.length]);

  const acceptItem = [
    {
      key: 'image',
      label: (
        <Flex gap="small">
          <FileImageOutlined />
          <span>图片</span>
        </Flex>
      ),
    },
    {
      key: 'docs',
      label: (
        <Flex gap="small">
          <FileWordOutlined />
          <span>文档</span>
        </Flex>
      ),
    },
    {
        key: 'all',
        label: (
            <Flex gap="small">
                <LinkOutlined />
                <span>所有文件</span>
            </Flex>
        )
    }
  ];

  const selectFile = ({ key }: { key: string }) => {
    attachmentsRef?.current?.select({
      accept: key === 'image' ? '.png,.jpg,.jpeg,.gif,.webp' : 
              key === 'docs' ? '.doc,.docx,.pdf,.txt,.md,.csv,.xlsx' : undefined,
      multiple: true,
    });
  };

  const senderHeader = (
    <Sender.Header
      title="附件"
      open={openAttachments}
      onOpenChange={setOpenAttachments}
      forceRender
      styles={{
        content: {
          padding: 0,
        },
      }}
    >
      <Attachments
        ref={attachmentsRef}
        multiple
        beforeUpload={() => false} // 手动上传
        items={attachments}
        onChange={handleUploadChange}
        placeholder={(type) =>
          type === 'drop'
            ? {
                title: 'Drop file here',
              }
            : {
                icon: <CloudUploadOutlined />,
                title: '上传文件',
                description: '点击或拖拽文件到此处上传',
              }
        }
        getDropContainer={() => senderRef.current?.nativeElement}
      />
    </Sender.Header>
  );

  const handleRegenerate = (messageId?: string) => {
    if (!isConnected || isStreaming) {
      return;
    }

    const numId = messageId ? parseInt(messageId) : undefined;
    wsClient.regenerate(numId);
  };

  const handleStartEdit = (message: MessageItem) => {
    setEditingMessageId(message.id);
    
    const content = message.content;
    
    // 尝试解析指令格式 /指令 参数
    const commandMatch = content.match(/^\/(\S+)\s+(.*)$/);
    if (commandMatch) {
      const commandValue = commandMatch[1];
      const restMessage = commandMatch[2];
      
      const command = commandSuggestions.find(c => c.value === commandValue);
      if (command) {
        // 找到了对应的指令
        
        // 尝试解析参数
        // 假设 slotConfig 结构是 [Text, Select(key=symbol), Text]
        let symbol = '';
        if (command.slotConfig && command.slotConfig.length === 3) {
          const prefix = command.slotConfig[0].value as string;
          const suffix = command.slotConfig[2].value as string;
          
          if (restMessage.startsWith(prefix) && restMessage.endsWith(suffix)) {
            symbol = restMessage.substring(prefix.length, restMessage.length - suffix.length);
          }
        }
        
        if (symbol) {
          // 设置激活的 Skill
          setActiveSkill({
            ...command.skill,
            closable: {
              onClose: () => {
                setActiveSkill(undefined);
                setSlotConfig(undefined);
              }
            }
          } as any);
          
          // 克隆 slotConfig 并设置默认值
          const newSlotConfig = JSON.parse(JSON.stringify(command.slotConfig));
          if (newSlotConfig[1] && newSlotConfig[1].props) {
            newSlotConfig[1].props.defaultValue = symbol;
            newSlotConfig[1].props.value = symbol; // 尝试同时设置 value
          }
          
          setSlotConfig(newSlotConfig);
          setInputText(''); // 清空纯文本输入
          skipNextChange.current = true;
          
          // 滚动到底部
          setTimeout(scrollToBottom, 100);
          return;
        }
      }
    }

    // 如果无法解析为结构化指令，则回退到普通文本编辑
    setInputText(content);
    // 滚动到底部以确保输入框可见
    setTimeout(scrollToBottom, 100);
  };

  const handleCancelEdit = () => {
    setEditingMessageId(null);
    setInputText('');
    setActiveSkill(undefined);
    setSlotConfig(undefined);
  };

  const handleCancel = () => {
    wsClient.cancelGeneration();
  };

  return (
    <>
      {contextHolder}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          position: 'relative',
        }}
      >
        <div
          className="no-scrollbar"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            paddingBottom: 'calc(140px + var(--sab, 0px))',
            background: '#fafafa',
          }}
        >
          {messages.length === 0 ? (
            <Empty
              description="开始对话吧"
              style={{ marginTop: 60 }}
              styles={{ image: { height: 80 } }}
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
                  onOpenComponentDrawer={handleOpenComponentDrawer}
                />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            zIndex: 100,
            borderTop: '1px solid #f0f0f0',
            padding: '12px 16px',
            paddingBottom: 'calc(12px + var(--sab, 0px))',
            paddingLeft: 'calc(16px + var(--sal, 0px))',
            paddingRight: 'calc(16px + var(--sar, 0px))',
            background: '#fff',
          }}
        >
          {editingMessageId && (
            <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'flex-end' }}>
              <Tag 
                color="blue" 
                closable 
                onClose={(e) => {
                  e.preventDefault();
                  handleCancelEdit();
                }}
                style={{ cursor: 'pointer' }}
              >
                取消编辑
              </Tag>
            </div>
          )}
          <Sender
            ref={senderRef}
            className="chat-drawer-sender"
            skill={activeSkill}
            placeholder={
              isConnected
                ? '输入消息...'
                : !sessionId
                ? '输入消息开始新对话...'
                : '连接中...'
            }
            value={inputText}
            onChange={(val) => {
              // 如果刚刚通过 onSelect 更新了输入框，则跳过本次 onChange
              if (skipNextChange.current) {
                skipNextChange.current = false;
                return;
              }

              // 如果按下 Backspace 导致内容为空，且当前有 activeSkill，则取消 activeSkill
              if (val === '') {
                if (activeSkill) setActiveSkill(undefined);
              }

              // 如果已经有选中的技能标签，且输入框内容只是一个斜杠，则忽略该斜杠
              if (activeSkill && val === '/') {
                setInputText('');
                return;
              }

              setInputText(val);
            }}
            onSubmit={handleSendMessage}
            onPaste={() => {}}
            disabled={!isConnected && !!sessionId}
            loading={isStreaming}
            submitType="enter"
            autoSize={{ minRows: 1, maxRows: 6 }}
            slotConfig={slotConfig}
            header={senderHeader}
            footer={(actionNode: React.ReactNode) => {
              const items: MenuProps['items'] = commandSuggestions.map(item => ({
                key: item.value,
                label: item.label,
                icon: item.icon,
              }));

              const handleMenuClick: MenuProps['onClick'] = (info) => {
                const item = commandSuggestions.find(i => i.value === info.key);
                if (item) {
                  // 选中指令时刷新股票列表
                  fetchSubscriptions();
                  
                  setActiveSkill({
                    ...item.skill,
                    closable: {
                      onClose: () => {
                        setActiveSkill(undefined);
                        setSlotConfig(undefined);
                      }
                    }
                  } as any);
                  setSlotConfig(item.slotConfig as any);
                  setInputText('');
                  skipNextChange.current = true;
                }
              };

              return (
                <Flex justify="space-between" align="center">
                  <Flex gap="small" align="center">
                    <Dropdown 
                      menu={{ 
                        items, 
                        onClick: handleMenuClick,
                        selectable: true,
                        selectedKeys: activeSkill?.value ? [activeSkill.value] : [],
                      }}
                      trigger={['click']}
                    >
                      <Button 
                          type="text" 
                          icon={<AppstoreOutlined />}
                          style={{ 
                            color: '#1677ff',
                            backgroundColor: '#e6f4ff'
                          }}
                        />
                    </Dropdown>
                    <Dropdown 
                      menu={{ items: acceptItem, onClick: selectFile }}
                      placement="topLeft"
                      trigger={['click']}
                    >
                      <Button 
                        type="text" 
                        icon={
                          <Badge dot={attachments.length > 0 && !openAttachments}>
                            <LinkOutlined />
                          </Badge>
                        }
                      />
                    </Dropdown>
                    <div style={{ fontSize: 12, color: '#999' }}>
                      {!isConnected && sessionId && <span>连接中...</span>}
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
                      <div style={{ width: 1, height: 14, background: 'rgba(0, 0, 0, 0.06)', margin: '0 8px' }} />
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
      </div>
      
      <ComponentDrawer
        open={drawerState.open}
        onClose={() => setDrawerState(prev => ({ ...prev, open: false }))}
        symbol={drawerState.symbol}
        module={drawerState.module}
      />
    </>
  );
};

const ChatDrawer: React.FC<ChatDrawerProps> = ({
  open,
  onClose,
  sessionId,
  model,
  onSessionCreated,
}) => {
  const isMobile = useIsMobile();

  return (
    <Drawer
      placement="right"
      onClose={onClose}
      open={open}
      styles={{
        header: {
          paddingTop: '16px',
        },
        body: {
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
        },
        wrapper: {
          width: isMobile ? '100%' : 800
        }
      }}
    >
      <ChatPanel
        active={open}
        sessionId={sessionId}
        model={model}
        onSessionCreated={onSessionCreated}
      />
    </Drawer>
  );
};

export default ChatDrawer;
export { ChatPanel };
