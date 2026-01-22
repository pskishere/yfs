import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChatPanel } from '../components/ChatDrawer';

interface ChatPageProps {
  model?: string;
}

const ChatPage: React.FC<ChatPageProps> = ({ model }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [currentChatSessionId, setCurrentChatSessionId] = useState<string | undefined>(undefined);

  // 监听 URL 中的 session 参数
  useEffect(() => {
    const sessionId = searchParams.get('session');
    if (sessionId) {
      setCurrentChatSessionId(sessionId);
    } else {
      setCurrentChatSessionId(undefined);
    }
  }, [searchParams]);

  return (
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
          minHeight: 0,
        }}
      >
        <ChatPanel
          active={true}
          sessionId={currentChatSessionId}
          model={model}
          onSessionCreated={(sessionId) => {
            setSearchParams({ session: sessionId });
          }}
        />
      </div>
    </div>
  );
};

export default ChatPage;

