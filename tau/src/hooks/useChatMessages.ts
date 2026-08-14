import { useState, useRef } from 'react';
import type { WebSocketCallbacks } from '../services/websocket';

export interface ThoughtItem {
  key: string;
  title: string;
  content?: string;
  description?: string;
  status: 'loading' | 'success' | 'error' | 'pending' | 'streaming';
}

export interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: 'pending' | 'streaming' | 'completed' | 'cancelled' | 'error';
  thoughts?: ThoughtItem[];
}

function formatMessages(rawMessages: any[]): MessageItem[] {
  return rawMessages.map((msg: any) => ({
    id: msg.id?.toString() || `msg-${Date.now()}`,
    role: msg.role,
    content: msg.content || '',
    status: msg.status || 'completed',
    thoughts: msg.thoughts || [],
  }));
}

export function useChatMessages(onGenerationError?: (error: string) => void) {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const currentStreamingIdRef = useRef<string | null>(null);
  const onErrorRef = useRef(onGenerationError);
  onErrorRef.current = onGenerationError;

  const messageCallbacks: Partial<WebSocketCallbacks> = {
    onHistory: (historyMessages) => setMessages(formatMessages(historyMessages)),

    onMessageCreated: (data) => {
      const userServerId = data.user_message_id?.toString();
      const aiServerId = data.ai_message_id?.toString();
      if (!userServerId && !aiServerId) return;
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.role === 'user' && msg.id.startsWith('user-') && userServerId)
            return { ...msg, id: userServerId };
          if (msg.id === currentStreamingIdRef.current && aiServerId) {
            currentStreamingIdRef.current = aiServerId;
            return { ...msg, id: aiServerId };
          }
          return msg;
        })
      );
    },

    onGenerationStarted: (data) => {
      setIsStreaming(true);
      const serverId = data.message_id?.toString();
      if (!serverId) return;
      setMessages((prev) => {
        const exists = prev.some((msg) => msg.id === serverId);
        if (exists) {
          return prev.map((msg) =>
            msg.id === currentStreamingIdRef.current ? { ...msg, id: serverId } : msg
          );
        }
        return [...prev, { id: serverId, role: 'assistant' as const, content: '', status: 'streaming' as const }];
      });
      currentStreamingIdRef.current = serverId;
    },

    onToken: (data) => {
      const targetId = data.message_id?.toString() || currentStreamingIdRef.current || '';
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === targetId
            ? { ...msg, content: msg.content + data.token, status: 'streaming' as const }
            : msg
        )
      );
    },

    onThought: (data) => {
      const targetId = data.message_id?.toString() || currentStreamingIdRef.current || '';
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== targetId) return msg;
          const thoughts = [...(msg.thoughts || [])];
          const key = data.tool || 'reasoning';
          const isReasoning = key === 'reasoning' || key.startsWith('reasoning_');
          const index = thoughts.findIndex((t) => t.key === key);
          if (index > -1) {
            const existing = thoughts[index];
            thoughts[index] = {
              ...existing,
              status: data.status,
              content: isReasoning ? (existing.content || '') + (data.thought || '') : existing.content,
              title: !isReasoning ? data.thought : existing.title,
            };
          } else {
            thoughts.push({
              key,
              title: isReasoning ? '思考过程' : data.thought,
              content: isReasoning ? data.thought : undefined,
              status: data.status,
            });
          }
          return { ...msg, thoughts, status: 'streaming' as const };
        })
      );
    },

    onGenerationCompleted: (data) => {
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === data.message_id?.toString()
            ? { ...msg, content: data.message, status: 'completed' as const }
            : msg
        )
      );
    },

    onGenerationCancelled: (data) => {
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === data.message_id?.toString()
            ? { ...msg, status: 'cancelled' as const }
            : msg
        )
      );
    },

    onGenerationError: (data) => {
      setIsStreaming(false);
      onErrorRef.current?.(data.error || '未知错误');
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === data.message_id?.toString()
            ? { ...msg, status: 'error' as const, content: msg.content || '生成失败' }
            : msg
        )
      );
    },

    onMessagesDeleted: (data) => {
      if (data.messages) setMessages(formatMessages(data.messages));
    },

    onMessagesUpdated: (data) => {
      if (data.messages) setMessages(formatMessages(data.messages));
    },

    onRegenerationStarted: (data) => {
      setIsStreaming(true);
      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id?.toString() || `ai-${Date.now()}`,
          role: 'assistant' as const,
          content: '',
          status: 'streaming' as const,
        },
      ]);
    },
  };

  return { messages, setMessages, isStreaming, setIsStreaming, currentStreamingIdRef, messageCallbacks };
}
