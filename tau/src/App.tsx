/**
 * 主应用组件 - 设置路由
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import MainPage from './pages/Main';
import './App.css';

const App: React.FC = () => {
  return (
    <ConfigProvider 
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#00b96b', // 青绿色
          borderRadius: 6, // 默认圆角
          colorBgLayout: '#f7f8fa', // 页面背景带一点点灰
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
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<MainPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </Router>
    </ConfigProvider>
  );
};

export default App;
