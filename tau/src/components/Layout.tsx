/**
 * 布局组件 - 无顶栏，直接显示内容
 */
import React, { type ReactNode, useState } from 'react';
import { Layout as AntLayout, Button, Space, Select } from 'antd';
import { MenuOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ChatSessionDrawer from './ChatSessionDrawer';
import './Layout.css';

const { Content } = AntLayout;

interface LayoutProps {
  children: ReactNode;
  model?: string;
  onModelChange?: (model: string) => void;
}

const MODELS = [
  { label: 'DeepSeek V3.2 (Cloud)', value: 'deepseek-v3.2:cloud' },
  { label: 'DeepSeek V3.1 (671B)', value: 'deepseek-v3.1:671b-cloud' },
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'Qwen3 32B', value: 'qwen3:32b' },
];

const getPlatformClass = () => {
  if (typeof navigator === 'undefined') return '';
  
  const classes = [];
  const isTauri = (window as any).__TAURI_INTERNALS__ !== undefined;
  
  if (isTauri) {
    classes.push('platform-tauri');
  } else {
    classes.push('platform-browser');
  }

  const ua = navigator.userAgent || '';
  if (/iPhone|iPad|iPod/.test(ua)) classes.push('platform-ios');
  if (/Android/.test(ua)) classes.push('platform-android');
  
  return classes.join(' ');
};

const Layout: React.FC<LayoutProps> = ({ children, model, onModelChange }) => {
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const platformClass = getPlatformClass();

  return (
    <AntLayout className={`app-layout ${platformClass}`}>
      <div
        className="app-topbar"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #f0f0f0',
          background: '#fff',
          position: 'sticky',
          top: 0,
          zIndex: 10,
          width: '100%',
        }}
      >
        <Space size="small">
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setSessionDrawerOpen(true)}
          />
        </Space>
        
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <Select
            value={model}
            onChange={onModelChange}
            options={MODELS}
            variant="borderless"
            style={{ minWidth: 160, fontWeight: 500 }}
            popupMatchSelectWidth={false}
          />
        </div>

        <Space size="small" style={{ width: 32 }} />
      </div>

      <Content className="app-content">
        {children}
      </Content>

      {/* 全局会话列表抽屉 */}
      <ChatSessionDrawer
        open={sessionDrawerOpen}
        onClose={() => setSessionDrawerOpen(false)}
        onSelectSession={(sessionId) => {
          setSessionDrawerOpen(false);
          // 如果不在对话页，跳转到对话页并带上会话 ID
          if (sessionId) {
            navigate(`/?session=${sessionId}`);
          } else {
            navigate('/');
          }
        }}
      />
    </AntLayout>
  );
};

export default Layout;
