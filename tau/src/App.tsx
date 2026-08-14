/**
 * 主应用组件 - 设置路由
 */
import React, { Suspense, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import { XProvider } from '@ant-design/x';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import antdZhCN from 'antd/locale/zh_CN';
import antdEnUS from 'antd/locale/en_US';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import 'dayjs/locale/en';
import { useTranslation } from 'react-i18next';
import Layout from './components/Layout';
import { ErrorBoundary } from './components/ErrorBoundary';
import './App.css';

const ChatPage = React.lazy(() => import('./pages/Chat'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

const App: React.FC = () => {
  const { i18n } = useTranslation();

  useEffect(() => {
    dayjs.locale(i18n.language === 'en-US' ? 'en' : 'zh-cn');
  }, [i18n.language]);

  const antdLocale = i18n.language === 'en-US' ? antdEnUS : antdZhCN;

  return (
    <QueryClientProvider client={queryClient}>
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
          <ErrorBoundary>
            <Router>
              <Layout>
                <Suspense fallback={<Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 120 }} />}>
                  <Routes>
                    <Route path="/" element={<ChatPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Suspense>
              </Layout>
            </Router>
          </ErrorBoundary>
        </XProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

export default App;
