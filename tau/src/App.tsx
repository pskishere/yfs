/**
 * 主应用组件 - 设置路由
 */
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { XProvider } from '@ant-design/x';
import antdZhCN from 'antd/locale/zh_CN';
import antdEnUS from 'antd/locale/en_US';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import 'dayjs/locale/en';
import { useTranslation } from 'react-i18next';
import Layout from './components/Layout';
import ChatPage from './pages/Chat';
import './App.css';

const App: React.FC = () => {
  const [model, setModel] = useState('deepseek-v3.1:671b-cloud');
  const { i18n } = useTranslation();

  // Sync dayjs locale with i18n language
  useEffect(() => {
    dayjs.locale(i18n.language === 'en-US' ? 'en' : 'zh-cn');
  }, [i18n.language]);

  const antdLocale = i18n.language === 'en-US' ? antdEnUS : antdZhCN;

  return (
    <ConfigProvider
      locale={antdLocale}
      theme={{
        token: {
          colorPrimary: '#00b96b',
          borderRadius: 6,
          colorBgLayout: '#f7f8fa',
        },
        components: {
          Button: {
            borderRadius: 6,
            borderRadiusSM: 4,
            borderRadiusLG: 8,
          },
        },
      }}
    >
      <XProvider>
        <Router>
          <Layout model={model} onModelChange={setModel}>
            <Routes>
              <Route path="/" element={<ChatPage model={model} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>
        </Router>
      </XProvider>
    </ConfigProvider>
  );
};

export default App;
