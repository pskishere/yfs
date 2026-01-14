/**
 * WebSocket 服务 - 处理与后端的 WebSocket 连接
 * 参考 llgo 和 glrn 项目的实现
 */

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  status?: 'pending' | 'streaming' | 'completed' | 'cancelled' | 'error';
  timestamp?: string;
  error_message?: string;
}

export type MessageHandler = (message: any) => void;

export interface WebSocketCallbacks {
  onConnect?: (sessionId: string) => void;
  onHistory?: (messages: any[]) => void;
  onMessageCreated?: (data: any) => void;
  onToken?: (data: any) => void;
  onThought?: (data: any) => void;
  onGenerationStarted?: (data: any) => void;
  onGenerationCompleted?: (data: any) => void;
  onGenerationCancelled?: (data: any) => void;
  onGenerationError?: (data: any) => void;
  onMessagesDeleted?: (data: any) => void;
  onMessagesUpdated?: (data: any) => void;
  onEditStarted?: (data: any) => void;
  onRegenerationStarted?: (data: any) => void;
  onError?: (error: string) => void;
  onClose?: () => void;
}

/**
 * WebSocket 客户端类
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private model: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: MessageHandler[] = [];
  private callbacks: WebSocketCallbacks = {};
  private isManualClose = false;

  /**
   * 连接到 WebSocket 服务器
   */
  connect(sessionId?: string, model?: string): Promise<string> {
    return new Promise((resolve, reject) => {
      try {
        this.isManualClose = false;
        this.sessionId = sessionId || null;
        this.model = model || null;
        const wsUrl = this.getWebSocketUrl(sessionId, model);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket 连接成功');
          this.reconnectAttempts = 0;
        };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // 处理连接消息
          if (data.type === 'connection') {
            this.sessionId = data.session_id;
            resolve(data.session_id);
          }
          
          // 处理所有消息
          this.handleMessage(data);
        } catch (error) {
          console.error('解析消息失败:', error);
        }
      };

        this.ws.onerror = (error) => {
          console.error('WebSocket 错误:', error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('WebSocket 连接关闭');
          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 获取 WebSocket URL
   */
  private getWebSocketUrl(sessionId?: string, model?: string): string {
    const envWsUrl = import.meta.env.VITE_WS_URL;
    const isHttps = window.location.protocol === 'https:';
    
    let baseUrl: string;
    
    // 如果在浏览器环境中运行（非 Tauri）且 hostname 不是 localhost，
    // 我们应该优先使用当前域名，这样可以支持 ngrok 等代理
    const isTauri = (window as any).__TAURI_INTERNALS__ !== undefined;
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    if (!isTauri && !isLocalhost) {
      // 浏览器环境且非本地访问，使用当前域名
      const protocol = isHttps ? 'wss:' : 'ws:';
      baseUrl = `${protocol}//${window.location.host}`;
    } else if (envWsUrl) {
      baseUrl = envWsUrl;
      // 如果页面是 HTTPS，强制将 ws:// 升级为 wss://
      if (isHttps && baseUrl.startsWith('ws://')) {
        baseUrl = baseUrl.replace('ws://', 'wss://');
      }
    } else {
      const protocol = isHttps ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      const port = window.location.port;
      
      let hostWithPort = port ? `${host}:${port}` : host;
      
      if (host === 'localhost' || host === 'tauri.localhost' || host === '0.0.0.0') {
        hostWithPort = `${host}:8086`;
      }
      
      baseUrl = `${protocol}//${hostWithPort}`;
    }
    
    let path = sessionId ? `ws/stock-chat/${sessionId}/` : 'ws/stock-chat/';
    const params = new URLSearchParams();
    if (model) {
      params.append('model', model);
    }
    
    const queryString = params.toString();
    if (queryString) {
      path += `?${queryString}`;
    }
    
    // 确保 baseUrl 不以 / 结尾，path 不以 / 开头
    const url = `${baseUrl.replace(/\/$/, '')}/${path}`;
    console.log('WebSocket URL:', url);
    return url;
  }

  /**
   * 尝试重新连接
   */
  private attemptReconnect() {
    this.reconnectAttempts++;
    console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    setTimeout(() => {
      this.connect(this.sessionId || undefined, this.model || undefined);
    }, this.reconnectDelay);
  }

  /**
   * 发送消息
   */
  sendMessage(message: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'message',
        message
      }));
    } else {
      console.error('WebSocket 未连接');
    }
  }

  /**
   * 取消当前生成
   */
  cancelGeneration() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'cancel'
      }));
    }
  }

  /**
   * 获取历史记录
   */
  getHistory(limit = 50) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'get_history',
        limit
      }));
    }
  }

  /**
   * 设置回调函数
   */
  setCallbacks(callbacks: WebSocketCallbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * 添加消息处理器（兼容旧接口）
   */
  onMessage(handler: MessageHandler) {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
    };
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: any) {
    const messageType = data.type;

    // 通知所有消息处理器
    this.messageHandlers.forEach(handler => handler(data));

    // 调用特定的回调函数
    switch (messageType) {
      case 'connection':
        if (this.callbacks.onConnect) {
          this.callbacks.onConnect(data.session_id);
        }
        break;

      case 'history':
        if (this.callbacks.onHistory) {
          this.callbacks.onHistory(data.messages || []);
        }
        break;

      case 'message_created':
        if (this.callbacks.onMessageCreated) {
          this.callbacks.onMessageCreated(data);
        }
        break;

      case 'generation_started':
        if (this.callbacks.onGenerationStarted) {
          this.callbacks.onGenerationStarted(data);
        }
        break;

      case 'token':
        if (this.callbacks.onToken) {
          this.callbacks.onToken(data);
        }
        break;

      case 'thought':
        if (this.callbacks.onThought) {
          this.callbacks.onThought(data);
        }
        break;

      case 'generation_completed':
        if (this.callbacks.onGenerationCompleted) {
          this.callbacks.onGenerationCompleted(data);
        }
        break;

      case 'generation_cancelled':
        if (this.callbacks.onGenerationCancelled) {
          this.callbacks.onGenerationCancelled(data);
        }
        break;

      case 'generation_error':
        if (this.callbacks.onGenerationError) {
          this.callbacks.onGenerationError(data);
        }
        break;

      case 'messages_deleted':
        if (this.callbacks.onMessagesDeleted) {
          this.callbacks.onMessagesDeleted(data);
        }
        break;

      case 'messages_updated':
        if (this.callbacks.onMessagesUpdated) {
          this.callbacks.onMessagesUpdated(data);
        }
        break;

      case 'edit_started':
        if (this.callbacks.onEditStarted) {
          this.callbacks.onEditStarted(data);
        }
        break;

      case 'regeneration_started':
        if (this.callbacks.onRegenerationStarted) {
          this.callbacks.onRegenerationStarted(data);
        }
        break;

      case 'error':
        if (this.callbacks.onError) {
          this.callbacks.onError(data.message || '未知错误');
        }
        break;

      default:
        console.log('未知消息类型:', messageType, data);
    }
  }

  /**
   * 重新生成消息
   */
  regenerate(messageId?: number) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'regenerate',
        message_id: messageId
      }));
    }
  }

  /**
   * 编辑消息
   */
  editMessage(messageId: number, content: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'edit_message',
        message_id: messageId,
        content
      }));
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isManualClose = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 获取连接状态
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * 获取会话 ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * 切换会话（断开当前连接并连接到新会话）
   */
  async switchSession(sessionId: string, model?: string): Promise<void> {
    this.disconnect();
    await this.connect(sessionId, model);
  }
}

export const wsClient = new WebSocketClient();
