/**
 * 布局组件 - 无顶栏，直接显示内容
 */
import React, { type ReactNode, useState, useEffect } from 'react';
import { Layout as AntLayout, Button, Select } from 'antd';
import { MenuOutlined, LineChartOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ChatSessionDrawer from './ChatSessionDrawer';
import StockLiveDrawer from '../domains/stock/components/StockLiveDrawer';
import { getAiModels } from '../services/api';
import './Layout.css';

const { Content } = AntLayout;

interface LayoutProps {
  children: ReactNode;
  model?: string;
  onModelChange?: (model: string) => void;
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

const Layout: React.FC<LayoutProps> = ({ children, model, onModelChange }) => {
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const [stockDrawerOpen, setStockDrawerOpen] = useState(false);
  const [modelOptions, setModelOptions] = useState<{label: string, value: string}[]>([]);
  const navigate = useNavigate();
  const platformClass = getPlatformClass();

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const models = await getAiModels();
        if (models && models.length > 0) {
          const options = models.map(m => ({
            label: m.name,
            value: m.id
          }));
          setModelOptions(options);
          
          // 如果当前没有选中模型，或者选中的模型不在列表里，默认选中第一个
          // 注意：这里需要检查 onModelChange 是否存在
          if (onModelChange) {
            const currentModelExists = options.some(opt => opt.value === model);
            if (!currentModelExists && options.length > 0) {
              onModelChange(options[0].value);
            }
          }
        }
      } catch (error) {
        console.error('获取模型列表失败:', error);
        // 失败时使用默认列表作为兜底
        setModelOptions([
          { label: 'DeepSeek V3.1 (671B)', value: 'deepseek-v3.1:671b-cloud' },
        ]);
      }
    };
    
    fetchModels();
  }, []); // 空依赖数组，只在组件挂载时执行一次

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
          // 移除 inline padding，统一由 Layout.css 处理安全区域
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
            onChange={onModelChange}
            options={modelOptions}
            variant="borderless"
            style={{ minWidth: 160, fontWeight: 500 }}
            popupMatchSelectWidth={false}
          />
        </div>

        <div style={{ width: 40, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            type="text"
            icon={<LineChartOutlined />}
            onClick={() => setStockDrawerOpen(true)}
          />
        </div>
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
      <StockLiveDrawer
        open={stockDrawerOpen}
        onClose={() => setStockDrawerOpen(false)}
      />
    </AntLayout>
  );
};

export default Layout;
