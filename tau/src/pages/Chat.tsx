import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChatPanel } from '../components/ChatDrawer';

const ChatPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [currentChatSessionId, setCurrentChatSessionId] = useState<string | undefined>(undefined);

  useEffect(() => {
    const sessionId = searchParams.get('session');
    setCurrentChatSessionId(sessionId ?? undefined);
  }, [searchParams]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ChatPanel
          active={true}
          sessionId={currentChatSessionId}
          onSessionCreated={(sessionId) => {
            setSearchParams({ session: sessionId });
          }}
        />
      </div>
    </div>
  );
};

export default ChatPage;
