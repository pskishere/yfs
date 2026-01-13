/**
 * AI 聊天页面
 */
import React from 'react';
import AIChat from '../components/AIChat';

/**
 * AI 聊天页面组件
 */
const AIChatPage: React.FC = () => {
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AIChat />
    </div>
  );
};

export default AIChatPage;
