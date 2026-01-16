/**
 * 聊天抽屉组件 - 参考 MobileChatPage 的布局设计
 */
import React, { useState, useEffect, useRef } from 'react';
import { Drawer, Button, notification, Empty, Flex, Divider, GetRef, Dropdown, Tag, type MenuProps } from 'antd';
import { Sender, ThoughtChain, type SenderProps } from '@ant-design/x';
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
  AppstoreOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { wsClient } from '../services/websocket';
import { getHotStocks } from '../services/api';
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
                alignSelf: isUser ? 'flex-end' : 'flex-start',
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
  const [hotStocks, setHotStocks] = useState<string[]>([]);
  const skipNextChange = useRef(false);
  const [api, contextHolder] = notification.useNotification();

  // 获取热门股票
  useEffect(() => {
    const fetchHotStocks = async () => {
      try {
        const res = await getHotStocks(50);
        if (res.success && res.stocks) {
          const options = res.stocks.map((s: any) => s.symbol);
          setHotStocks(options);
        }
      } catch (err) {
        console.error('获取热门股票失败:', err);
      }
    };
    fetchHotStocks();
  }, []);

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
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '获取 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的最新价格信息。' },
      ],
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
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '查看 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
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
      label: '技术指标',
      value: '指标',
      icon: <DashboardOutlined />,
      extra: '展示 RSI, MACD, KDJ 等',
      skill: {
        value: '指标',
        label: '技术指标',
        icon: <DashboardOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '分析 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的技术指标（RSI, MACD 等）。' },
      ],
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
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '查询 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的基本面数据。' },
      ],
    },
    {
      label: '最新新闻',
      value: '新闻',
      icon: <FileTextOutlined />,
      extra: '展示个股最新相关新闻',
      skill: {
        value: '新闻',
        label: '最新新闻',
        icon: <FileTextOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '查看 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的最新相关新闻。' },
      ],
    },
    {
      label: '市场行情',
      value: '行情',
      icon: <BarChartOutlined />,
      extra: '展示 A 股、美股、港股行情',
      skill: {
        value: '行情',
        label: '市场行情',
        icon: <BarChartOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '获取 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的市场行情。' },
      ],
    },
    {
      label: '周期分析',
      value: '周期',
      icon: <HistoryOutlined />,
      extra: '分析股票的时间周期规律',
      skill: {
        value: '周期',
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
            options: hotStocks,
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
      label: '枢轴点',
      value: '枢轴',
      icon: <DatabaseOutlined />,
      extra: '展示支撑位与阻力位',
      skill: {
        value: '枢轴',
        label: '枢轴点',
        icon: <DatabaseOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '计算 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
            placeholder: '股票代码',
            style: { width: 100 },
            showSearch: true,
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 的枢轴点（支撑位与阻力位）。' },
      ],
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
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '查看 ' },
        {
          type: 'select',
          key: 'symbol',
          props: {
            options: hotStocks,
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
      label: '智能选股',
      value: '选股',
      icon: <BarChartOutlined />,
      extra: '通过条件筛选股票',
      skill: {
        value: '选股',
        label: '智能选股',
        icon: <BarChartOutlined />,
        closable: true,
      },
      slotConfig: [
        { type: 'text', value: '根据 ' },
        {
          type: 'select',
          key: 'strategy',
          props: {
            options: ['热门增长', '高股息', '低估值'],
            placeholder: '选股策略',
            style: { width: 100 },
            listHeight: 50,
          },
        },
        { type: 'text', value: ' 策略进行智能选股。' },
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
    if (!message.trim() && !skill && !activeSkill) return;

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

    // 如果处于编辑模式
    if (editingMessageId) {
      const numId = parseInt(editingMessageId);
      if (!isNaN(numId)) {
        wsClient.editMessage(numId, fullMessage);
      }
      setEditingMessageId(null);
      setInputText('');
      senderRef.current?.clear?.();
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
    senderRef.current?.clear?.();

    // 发送到服务器
    wsClient.sendMessage(fullMessage);
    setActiveSkill(undefined);
    setSlotConfig(undefined);
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
    
    const content = message.content;
    const slashIndex = content.indexOf('/');
    const spaceIndex = content.indexOf(' ');
    
    // 检查是否是指令消息
    if (slashIndex === 0 && spaceIndex !== -1) {
      const cmd = content.substring(1, spaceIndex);
      const rest = content.substring(spaceIndex + 1);
      const item = suggestionItems.find(i => i.value === cmd);
      
      if (item) {
        // 设置技能标签，但内容直接作为文本回填
        setActiveSkill({
          ...item.skill,
          closable: {
            onClose: () => {
              setActiveSkill(undefined);
              setSlotConfig(undefined);
            }
          }
        } as any);
        setInputText(rest);
        setTimeout(scrollToBottom, 100);
        return;
      }
    }

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
              console.log('onChange', val);
              
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
            footer={(actionNode: React.ReactNode) => {
              const items: MenuProps['items'] = suggestionItems.map(item => ({
                key: item.value,
                label: item.label,
                icon: item.icon,
              }));

              const handleMenuClick: MenuProps['onClick'] = (info) => {
                const item = suggestionItems.find(i => i.value === info.key);
                if (item) {
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
                    <div style={{ fontSize: 12, color: '#999' }}>
                      {isConnected ? (
                        <span>按 Enter 发送</span>
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
          paddingTop: '16px',
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
