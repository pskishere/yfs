/**
 * 主应用组件 - 设置路由
 */
import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { XProvider } from '@ant-design/x';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import ChatPage from './pages/Chat';
import './App.css';

const App: React.FC = () => {
  const [model, setModel] = useState('deepseek-v3.1:671b-cloud');

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
