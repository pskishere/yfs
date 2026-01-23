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
  private connectionPromise: Promise<string> | null = null;


  /**
   * 连接到 WebSocket 服务器
   */
  async connect(sessionId?: string, model?: string, namespace: string = 'stock'): Promise<string> {
    // 如果已经连接到相同的 sessionId 和 model，直接返回
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.sessionId === (sessionId || null) && this.model === (model || null)) {
      console.log('WebSocket 已经连接到相同会话:', this.sessionId);
      return Promise.resolve(this.sessionId!);
    }

    // 如果正在连接中，返回当前的 Promise
    if (this.connectionPromise) {
      console.log('WebSocket 正在连接中，等待连接完成...');
      return this.connectionPromise;
    }

    if (!sessionId) {
      console.error('连接失败: 未提供 SessionID');
      return Promise.reject(new Error('SessionID is required for WebSocket connection'));
    }

    const targetSessionId = sessionId;

    this.connectionPromise = new Promise((resolve, reject) => {
      try {
        this.isManualClose = false;
        this.sessionId = targetSessionId || null;
        this.model = model || null;
        const wsUrl = this.getWebSocketUrl(targetSessionId, model, namespace);
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
              this.connectionPromise = null; // 连接成功，清除 Promise
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
          this.connectionPromise = null; // 错误，清除 Promise
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('WebSocket 连接关闭');
          this.connectionPromise = null; // 关闭，清除 Promise
          
          if (this.callbacks.onClose) {
            this.callbacks.onClose();
          }

          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        this.connectionPromise = null;
        reject(error);
      }
    });

    return this.connectionPromise;
  }

  /**
   * 获取 WebSocket URL
   */
  private getWebSocketUrl(sessionId?: string, model?: string, namespace: string = 'stock'): string {
    const envWsUrl = import.meta.env.VITE_WS_URL;
    const isHttps = window.location.protocol === 'https:';
    const isTauri = (window as any).__TAURI_INTERNALS__ !== undefined;
    const hostname = window.location.hostname;
    const ua = navigator.userAgent || '';
    const isAndroid = /Android/.test(ua);
    const isLocalHost =
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '0.0.0.0' ||
      hostname === 'tauri.localhost';
    
    if (envWsUrl && (isTauri || isLocalHost)) {
      let base = envWsUrl;
      if (isAndroid && (base.includes('localhost') || base.includes('127.0.0.1'))) {
        base = base.replace('localhost', '10.0.2.2').replace('127.0.0.1', '10.0.2.2');
      }
      if (isHttps && base.startsWith('ws://')) {
        base = base.replace('ws://', 'wss://');
      }
      return this.buildWebSocketUrl(base, sessionId, namespace, model);
    }

    // 2. Tauri 环境下，不能用相对路径，回退到本机 Nginx 8086
    if (isTauri) {
      const protocol = isHttps ? 'wss:' : 'ws:';
      const host = isAndroid ? '10.0.2.2' : 'localhost';
      const base = `${protocol}//${host}:8086`;
      return this.buildWebSocketUrl(base, sessionId, namespace, model);
    }

    // 3. 浏览器环境：始终使用当前站点（通常由 Nginx 代理）
    const protocol = isHttps ? 'wss:' : 'ws:';
    const baseUrl = `${protocol}//${window.location.host}`;
    return this.buildWebSocketUrl(baseUrl, sessionId, namespace, model);
  }

  /**
   * 构建完整 WebSocket URL
   */
  private buildWebSocketUrl(baseUrl: string, sessionId?: string, namespace: string = 'stock', model?: string): string {
    
    // 新版后端要求必须有 session_id，且路径格式为 ws/chat/<namespace>/<session_id>/
    if (!sessionId) {
      console.warn('WebSocket URL 构建警告: 缺少 session_id，可能会导致连接失败');
    }

    let path = `ws/chat/${namespace}/${sessionId || 'unknown'}/`;
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
    this.connectionPromise = null;
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
