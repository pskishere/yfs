import { useState, useEffect, useRef } from 'react';
import { wsClient } from '../services/websocket';
import type { WebSocketCallbacks } from '../services/websocket';

interface UseChatConnectionOptions {
  active: boolean;
  sessionId?: string;
  model?: string;
  callbacks: Partial<WebSocketCallbacks>;
  onError?: (msg: string) => void;
  onConnectionError?: () => void;
}

export function useChatConnection({
  active,
  sessionId,
  model,
  callbacks,
  onError,
  onConnectionError,
}: UseChatConnectionOptions) {
  const [isConnected, setIsConnected] = useState(false);
  // Keep refs so callbacks/handlers always use latest values without re-triggering the effect
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const onConnectionErrorRef = useRef(onConnectionError);
  onConnectionErrorRef.current = onConnectionError;

  useEffect(() => {
    if (!active) return;

    wsClient.setCallbacks({
      ...callbacksRef.current,
      onConnect: (wsSessionId) => {
        setIsConnected(true);
        callbacksRef.current.onConnect?.(wsSessionId);
      },
      onClose: () => {
        setIsConnected(false);
        callbacksRef.current.onClose?.();
      },
      onError: (error) => {
        onErrorRef.current?.(error);
        callbacksRef.current.onError?.(error);
      },
    });

    if (!sessionId) {
      setIsConnected(false);
      return;
    }

    if (wsClient.getSessionId() !== sessionId) {
      setIsConnected(false);
    }

    wsClient.connect(sessionId, model).catch(() => {
      onConnectionErrorRef.current?.();
    });

    return () => {
      wsClient.disconnect();
    };
  }, [active, sessionId, model]);

  return { isConnected };
}
