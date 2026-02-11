/**
 * 股票实时数据 WebSocket 服务
 */

export interface StockPriceUpdate {
  symbol: string;
  price: number;
  change?: number;
  change_pct?: number;
  time?: number;
}

export type StockMessageHandler = (message: any) => void;

export interface StockWebSocketCallbacks {
  onConnect?: () => void;
  onSubscribed?: (data: { symbols: string[], initial_data?: StockPriceUpdate[] }) => void;
  onUnsubscribed?: (symbols: string[]) => void;
  onPriceUpdate?: (update: StockPriceUpdate) => void;
  onError?: (error: string) => void;
  onClose?: () => void;
}

export class StockWebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private callbacks: StockWebSocketCallbacks = {};
  private isManualClose = false;
  private subscribedSymbols: string[] = [];

  constructor(callbacks: StockWebSocketCallbacks = {}) {
    this.callbacks = callbacks;
  }

  /**
   * 获取 WebSocket URL
   */
  private getWebSocketUrl(): string {
    const envWsUrl = import.meta.env.VITE_WS_URL;
    const isHttps = window.location.protocol === 'https:';
    const isTauri = (window as any).__TAURI_INTERNALS__ !== undefined;
    const hostname = window.location.hostname;
    const isLocalHost =
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '0.0.0.0' ||
      hostname === 'tauri.localhost';
    
    let base = '';
    if (envWsUrl && (isTauri || isLocalHost)) {
      base = envWsUrl;
      if (isHttps && base.startsWith('ws://')) {
        base = base.replace('ws://', 'wss://');
      }
    } else if (isTauri) {
      const protocol = isHttps ? 'wss:' : 'ws:';
      base = `${protocol}//localhost:8086`;
    } else {
      const protocol = isHttps ? 'wss:' : 'ws:';
      base = `${protocol}//${window.location.host}`;
    }

    return `${base.replace(/\/$/, '')}/ws/stock/`;
  }

  /**
   * 连接到 WebSocket 服务器
   */
  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.isManualClose = false;
      const wsUrl = this.getWebSocketUrl();
      console.log('Connecting to Stock WebSocket:', wsUrl);
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('Stock WebSocket connected');
        this.reconnectAttempts = 0;
        if (this.callbacks.onConnect) {
          this.callbacks.onConnect();
        }
        
        // 自动重连后重新订阅
        if (this.subscribedSymbols.length > 0) {
          this.subscribe(this.subscribedSymbols);
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (e) {
          console.error('Error parsing stock websocket message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('Stock WebSocket error:', error);
        if (this.callbacks.onError) {
          this.callbacks.onError('WebSocket connection error');
        }
      };

      this.ws.onclose = () => {
        console.log('Stock WebSocket closed');
        if (this.callbacks.onClose) {
          this.callbacks.onClose();
        }

        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
          setTimeout(() => this.connect(), this.reconnectDelay);
        }
      };
    } catch (e) {
      console.error('Failed to connect to Stock WebSocket:', e);
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: any) {
    switch (data.type) {
      case 'subscribed':
        this.subscribedSymbols = data.symbols;
        if (this.callbacks.onSubscribed) {
          this.callbacks.onSubscribed(data);
        }
        break;
      case 'unsubscribed':
        this.subscribedSymbols = data.symbols;
        if (this.callbacks.onUnsubscribed) {
          this.callbacks.onUnsubscribed(data.symbols);
        }
        break;
      case 'price_update':
        if (this.callbacks.onPriceUpdate) {
          this.callbacks.onPriceUpdate(data.data);
        }
        break;
      case 'error':
        if (this.callbacks.onError) {
          this.callbacks.onError(data.message);
        }
        break;
    }
  }

  /**
   * 订阅股票
   */
  subscribe(symbols: string | string[]) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const symbolsList = Array.isArray(symbols) ? symbols : [symbols];
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: symbolsList
      }));
    } else {
      console.warn('Cannot subscribe: WebSocket not connected');
    }
  }

  /**
   * 取消订阅股票
   */
  unsubscribe(symbols: string | string[]) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const symbolsList = Array.isArray(symbols) ? symbols : [symbols];
      this.ws.send(JSON.stringify({
        action: 'unsubscribe',
        symbols: symbolsList
      }));
    }
  }

  /**
   * 关闭连接
   */
  close() {
    this.isManualClose = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
