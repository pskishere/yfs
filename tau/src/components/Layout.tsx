/**
 * 布局组件 - 无顶栏，直接显示内容
 */
import React, { type ReactNode, useState, useEffect } from 'react';
import { Layout as AntLayout, Button, Select } from 'antd';
import { MenuOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import ChatSessionDrawer from './ChatSessionDrawer';
import { getAiModels } from '../services/api';
import { useAppStore } from '../store/appStore';
import './Layout.css';

const { Content } = AntLayout;

interface LayoutProps {
  children: ReactNode;
}

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

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const platformClass = getPlatformClass();
  const { i18n } = useTranslation();
  const isEnglish = i18n.language === 'en-US';
  const toggleLanguage = () => i18n.changeLanguage(isEnglish ? 'zh-CN' : 'en-US');

  const { model, setModel } = useAppStore();

  const { data: modelOptions = [] } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const models = await getAiModels();
      return models.map(m => ({ label: m.name, value: m.id }));
    },
    placeholderData: [{ label: 'DeepSeek V3.1 (671B)', value: 'deepseek-v3.1:671b-cloud' }],
  });

  // 若当前 model 不在列表里，自动选第一个
  useEffect(() => {
    if (modelOptions.length > 0 && !modelOptions.some(o => o.value === model)) {
      setModel(modelOptions[0].value);
    }
  }, [modelOptions, model, setModel]);

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
        <div style={{ width: 40 }}>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setSessionDrawerOpen(true)}
          />
        </div>

        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <Select
            value={model}
            onChange={setModel}
            options={modelOptions}
            variant="borderless"
            style={{ minWidth: 160, fontWeight: 500 }}
            popupMatchSelectWidth={false}
          />
        </div>

        <div style={{ width: 40, display: 'flex', justifyContent: 'center' }}>
          <Button
            type="text"
            size="small"
            onClick={toggleLanguage}
            style={{ fontSize: 11, color: '#888', padding: '0 4px', minWidth: 0 }}
          >
            {isEnglish ? '中' : 'EN'}
          </Button>
        </div>
      </div>

      <Content className="app-content">
        {children}
      </Content>

      <ChatSessionDrawer
        open={sessionDrawerOpen}
        onClose={() => setSessionDrawerOpen(false)}
        onSelectSession={(sessionId) => {
          setSessionDrawerOpen(false);
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
