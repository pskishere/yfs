/**
 * 聊天抽屉组件 - 参考 MobileChatPage 的布局设计
 */
import React, { useState, useEffect, useRef } from 'react';
import { Drawer, Button, notification, Tooltip, Empty, Flex, Divider, GetRef } from 'antd';
import { Sender, ThoughtChain, Suggestion, type SenderProps } from '@ant-design/x';
import {
  StopOutlined,
  EditOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  LineChartOutlined,
  InfoCircleOutlined,
  DashboardOutlined,
  HistoryOutlined,
  DollarOutlined,
  DatabaseOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { wsClient } from '../services/websocket';
import { searchStocks } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import StockComponentRenderer from './StockComponentRenderer';
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
  status: 'loading' | 'success' | 'error' | 'pending';
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
}> = ({ message, onEdit, onRegenerate, isStreaming }) => {
  const isUser = message.role === 'user';
  const isCompleted = message.status === 'completed';

  // 快捷指令配置（用于渲染用户消息中的标签）
  const suggestionItems = [
    { label: '价格信息', value: '价格' },
    { label: 'K线图表', value: '图表' },
    { label: '技术指标', value: '指标' },
    { label: '基本面', value: '基本面' },
    { label: '市场行情', value: '行情' },
    { label: '周期分析', value: '周期' },
    { label: '枢轴点', value: '枢轴' },
    { label: '期权链', value: '期权' },
  ];

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
          {/* 消息气泡 */}
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 12,
              background: isUser ? '#e6f7ff' : '#f5f5f5',
              wordBreak: 'break-word',
              flex: isUser ? '0 1 auto' : '1 1 auto',
              maxWidth: '100%', // 确保气泡本身不溢出
              minWidth: 0,      // 允许气泡缩小
              display: 'flex',
              flexDirection: 'column',
              gap: 4
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
                    {(() => {
                      const content = message.content;
                      // 匹配 <stock-analysis symbol="AAPL" module="price" />
                      // 支持两种标签格式: <stock-analysis /> 和 [stock-analysis ]
                      const regex = /(?:<|\[)(?:stock-analysis|股票分析)\s+symbol=["']([^"']+)["']\s+module=["']([^"']+)["']\s*\/?(?:>|\])/gi;
                      const parts = [];
                      let lastIndex = 0;
                      let match;

                      while ((match = regex.exec(content)) !== null) {
                        if (match.index > lastIndex) {
                          parts.push(
                            <ReactMarkdown key={`text-${lastIndex}`} remarkPlugins={[remarkGfm]}>
                              {content.substring(lastIndex, match.index)}
                            </ReactMarkdown>
                          );
                        }

                        parts.push(
                          <StockComponentRenderer
                            key={`stock-${match.index}`}
                            symbol={match[1]}
                            module={match[2]}
                          />
                        );

                        lastIndex = regex.lastIndex;
                      }

                      if (lastIndex < content.length) {
                        parts.push(
                          <ReactMarkdown key={`text-${lastIndex}`} remarkPlugins={[remarkGfm]}>
                            {content.substring(lastIndex)}
                          </ReactMarkdown>
                        );
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
                  const slashIndex = content.indexOf('/');
                  const spaceIndex = content.indexOf(' ');
                  
                  if (slashIndex === 0 && spaceIndex !== -1) {
                    const cmd = content.substring(1, spaceIndex);
                    const rest = content.substring(spaceIndex + 1);
                    const item = suggestionItems.find(i => i.value === cmd);
                    
                    if (item) {
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
                          <span>{rest}</span>
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

        {/* 消息下方的操作按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%', marginTop: 4 }}>
          {/* 用户消息：编辑按钮 */}
          {isUser && isCompleted && onEdit && (
            <Tooltip title="编辑">
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => onEdit(message)}
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
              />
            </Tooltip>
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
  const [stockSuggestions, setStockSuggestions] = useState<any[]>([]);
  const currentStreamingIdRef = useRef<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const senderRef = useRef<GetRef<typeof Sender>>(null);
  const [activeSkill, setActiveSkill] = useState<SenderProps['skill']>(undefined);
  const skipNextChange = useRef(false);
  const [api, contextHolder] = notification.useNotification();

  // 快捷指令配置
  const suggestionItems = [
    {
      label: '价格信息',
      value: '价格',
      icon: <DollarOutlined />,
      extra: '展示当前价格、涨跌幅等',
      skill: {
        value: '价格',
        label: '价格信息',
        icon: <DollarOutlined />,
        closable: false,
      }
    },
    {
      label: 'K线图表',
      value: '图表',
      icon: <LineChartOutlined />,
      extra: '展示交互式 K 线图',
      skill: {
        value: '图表',
        label: 'K线图表',
        icon: <LineChartOutlined />,
        closable: false,
      }
    },
    {
      label: '技术指标',
      value: '指标',
      icon: <DashboardOutlined />,
      extra: '展示 RSI, MACD, KDJ 等',
      skill: {
        value: '指标',
        label: '技术指标',
        icon: <DashboardOutlined />,
        closable: false,
      }
    },
    {
      label: '基本面',
      value: '基本面',
      icon: <InfoCircleOutlined />,
      extra: '展示市值、市盈率、财务等',
      skill: {
        value: '基本面',
        label: '基本面',
        icon: <InfoCircleOutlined />,
        closable: false,
      }
    },
    {
      label: '市场行情',
      value: '行情',
      icon: <BarChartOutlined />,
      extra: '展示成交量、换手率等',
      skill: {
        value: '行情',
        label: '市场行情',
        icon: <BarChartOutlined />,
        closable: false,
      }
    },
    {
      label: '周期分析',
      value: '周期',
      icon: <HistoryOutlined />,
      extra: '展示短中长期趋势分析',
      skill: {
        value: '周期',
        label: '周期分析',
        icon: <HistoryOutlined />,
        closable: false,
      }
    },
    {
      label: '枢轴点',
      value: '枢轴',
      icon: <DatabaseOutlined />,
      extra: '展示支撑位与阻力位',
      skill: {
        value: '枢轴',
        label: '枢轴点',
        icon: <DatabaseOutlined />,
        closable: false,
      }
    },
    {
      label: '期权链',
      value: '期权',
      icon: <DatabaseOutlined />,
      extra: '展示期权行权价与波动率',
      skill: {
        value: '期权',
        label: '期权链',
        icon: <DatabaseOutlined />,
        closable: false,
      }
    },
  ];

  // 辅助函数：判断搜索上下文
  const getSearchContext = (text: string, activeSkill?: any) => {
    // 如果是编辑模式，不显示任何补全建议
    if (activeSkill?.value === 'editing') return { mode: 'none' as const, query: '' };

    // 只有单 / 时，强制为指令模式
    if (text === '/') return { mode: 'instruction' as const, query: '' };
    
    // 如果有标签，则是股票搜索模式
    if (activeSkill) return { mode: 'stock' as const, query: text };

    const lastSlashIndex = text.lastIndexOf('/');
    if (lastSlashIndex === -1) return { mode: 'none' as const, query: '' };
    
    const afterSlash = text.substring(lastSlashIndex + 1);
    const spaceIndex = afterSlash.indexOf(' ');
    
    // 指令后有空格，进入股票搜索模式
    if (spaceIndex !== -1) {
      return { mode: 'stock' as const, query: afterSlash.substring(spaceIndex + 1) };
    }
    
    // 否则还在输入指令
    return { mode: 'instruction' as const, query: afterSlash };
  };

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
    if (!message.trim() && !skill) return;

    // 如果当前处于编辑模式
    if (editingMessageId && activeSkill?.value === 'editing') {
      const messageId = parseInt(editingMessageId);
      if (!isNaN(messageId)) {
        wsClient.editMessage(messageId, message.trim());
        setEditingMessageId(null);
        setActiveSkill(undefined);
        setInputText('');
        senderRef.current?.clear?.();
        return;
      }
    }

    // 如果还没有连接，说明是第一次发送消息（或者是连接断开了）
    if (!isConnected) {
      try {
        setIsStreaming(true); // 显示加载状态
        const newSessionId = await wsClient.connect(sessionId, model);
        setIsConnected(true);
        
        // 如果是新创建的会话，通知父组件
        if (!sessionId && onSessionCreated) {
          onSessionCreated(newSessionId);
        }
      } catch (error) {
        setIsStreaming(false);
        // 错误已经在 wsClient.connect 或 onError 回调中处理
        return;
      }
    }

    const finalSkill = skill || activeSkill;
    const fullMessage = finalSkill ? `/${finalSkill.value} ${message}` : message;

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
    senderRef.current?.clear?.();

    // 发送到服务器
    wsClient.sendMessage(fullMessage);
    setActiveSkill(undefined);
  };

  const handleRegenerate = (messageId?: string) => {
    if (!isConnected || isStreaming) {
      return;
    }

    const numId = messageId ? parseInt(messageId) : undefined;
    wsClient.regenerate(numId);
  };

  const handleStartEdit = (message: MessageItem) => {
    setEditingMessageId(message.id);
    
    // 设置跳过下一次 onChange，防止 Sender 组件在设置 skill 时可能触发的清空行为
    skipNextChange.current = true;
    setInputText(message.content);
    
    setActiveSkill({
      value: 'editing',
      label: '正在编辑消息',
      icon: <EditOutlined />,
      closable: {
        onClose: () => {
          setActiveSkill(undefined);
          setEditingMessageId(null);
          setInputText('');
        },
      },
    } as any);

    // 自动聚焦到输入框
    setTimeout(() => {
      senderRef.current?.focus?.();
    }, 0);
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
        }}
      >
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

        <div
          style={{
            borderTop: '1px solid #f0f0f0',
            padding: '12px 16px',
            paddingBottom: 'calc(12px + env(safe-area-inset-bottom))',
            background: '#fff',
          }}
        >
          <Suggestion
            items={(search) => {
              // 如果正在编辑，不显示任何建议
              if (activeSkill?.value === 'editing') return [];

              // 使用 search 参数作为上下文判断的基础，如果不是字符串（如 true）则回退到 inputText
              const contextText = typeof search === 'string' ? search : inputText;
              const { mode, query } = getSearchContext(contextText, activeSkill);
              
              if (mode === 'stock') {
                // 如果是股票搜索
                if (stockSuggestions.length === 0 && query === '') {
                  // 如果输入为空且没有搜索结果，可以显示“请输入股票代码或名称”或最近搜索（此处暂留空或后续扩展）
                  return [];
                }
                return stockSuggestions.map(s => {
                  const name = s.name || '';
                  // 恢复手动截断，根据用户要求改成截断 19 个字符
                  const displayName = name.length > 19 ? name.substring(0, 19) + '...' : name;
                  return {
                    label: `${s.symbol} - ${displayName}`,
                    value: s.symbol,
                    extra: s.type || s.exchDisp,
                  };
                });
              }

              // 否则是指令搜索
              const instructionQuery = mode === 'instruction' ? query : '';
              if (typeof search !== 'string' || !search) return suggestionItems;
              
              return suggestionItems.filter(item => 
                String(item.label).toLowerCase().includes(instructionQuery.toLowerCase()) ||
                item.value.toLowerCase().includes(instructionQuery.toLowerCase())
              );
            }}
            onSelect={(value) => {
              const { mode } = getSearchContext(inputText, activeSkill);
              
              if (mode === 'stock') {
                // 如果是补全股票代码
                if (activeSkill) {
                  // 在标签模式下，直接替换输入文本为选中的股票代码
                  skipNextChange.current = true;
                  setInputText(value);
                } else {
                  // 在纯文本模式下，保留指令前缀并替换最后的搜索词
                  const newValue = (() => {
                    const lastSlashIndex = inputText.lastIndexOf('/');
                    const afterSlash = inputText.substring(lastSlashIndex + 1);
                    const spaceIndex = afterSlash.indexOf(' ');
                    const base = inputText.substring(0, lastSlashIndex + 1 + spaceIndex + 1);
                    return `${base}${value}`;
                  })();
                  
                  skipNextChange.current = true;
                  setInputText(newValue);
                }
              } else {
                const selectedItem = suggestionItems.find(item => item.value === value);
                if (selectedItem && selectedItem.skill) {
                  // 如果有对应的 skill 配置，则设置为标签样式
                  setActiveSkill({
                    ...selectedItem.skill,
                  });
                  // 选中指令后，强制清空输入框
                  skipNextChange.current = true;
                  setInputText('');
                }
              }
            }}
          >
            {({ onKeyDown, onTrigger }) => (
              <Sender
                ref={senderRef}
                className="chat-drawer-sender"
                skill={activeSkill}
                placeholder={
                  isConnected
                    ? '输入消息，或输入 / 使用快捷指令...'
                    : !sessionId
                    ? '输入消息开始新对话...'
                    : '连接中...'
                }
                value={inputText}
                onChange={async (val) => {
                  // 如果刚刚通过 onSelect 更新了输入框，则跳过本次 onChange
                  if (skipNextChange.current) {
                    skipNextChange.current = false;
                    return;
                  }

                  // 如果按下 Backspace 导致内容为空，且当前有 activeSkill，则取消 activeSkill
                  if (val === '' && activeSkill) {
                    setActiveSkill(undefined);
                  }

                  // 如果已经有选中的技能标签，且输入框内容只是一个斜杠，则忽略该斜杠
                  // 这通常是由于快捷指令触发字符残留导致的
                  if (activeSkill && val === '/') {
                    setInputText('');
                    return;
                  }

                  setInputText(val);
                  
                  const { mode, query } = getSearchContext(val, activeSkill);

                  if (mode === 'stock') {
                    // 进入股票搜索模式
                    try {
                      const res = await searchStocks(query);
                      if (res.success && res.results) {
                        setStockSuggestions(res.results);
                        onTrigger(val);
                      } else {
                        onTrigger(false);
                      }
                    } catch (err) {
                      onTrigger(false);
                    }
                  } else if (mode === 'instruction') {
                    // 进入指令搜索模式
                    const hasMatch = query === '' || suggestionItems.some(item => 
                      String(item.label).toLowerCase().includes(query.toLowerCase()) ||
                      item.value.toLowerCase().includes(query.toLowerCase())
                    );
                    onTrigger(hasMatch ? val : false);
                  } else {
                    onTrigger(false);
                  }
                }}
                onSubmit={handleSendMessage}
                onKeyDown={onKeyDown}
                onPaste={() => {}}
                disabled={!isConnected && !!sessionId}
                loading={isStreaming}
                submitType="enter"
                autoSize={{ minRows: 1, maxRows: 6 }}
                footer={(actionNode: React.ReactNode) => {
                  return (
                    <Flex justify="space-between" align="center">
                      <Flex gap="small" align="center">
                        <div style={{ fontSize: 12, color: '#999' }}>
                          {isConnected ? (
                            <span>按 Enter 发送，输入 / 唤起快捷指令</span>
                          ) : !sessionId ? (
                            <span>按 Enter 发送第一条消息并开始对话</span>
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
            )}
          </Suggestion>
        </div>
      </div>
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
      width={isMobile ? '100%' : 800}
      onClose={onClose}
      open={open}
      styles={{
        header: {
          paddingTop: 'calc(16px + env(safe-area-inset-top))',
        },
        body: {
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
        },
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
