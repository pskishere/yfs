/**
 * 组件渲染器 - 用于在聊天气泡中动态加载并显示分析模块
 * 
 * 优化：仅作为触发器，实际内容在全局 ComponentDrawer 中渲染
 */
import React from 'react';
import { Button, Empty } from 'antd';
import { LineChartOutlined, FundOutlined, HistoryOutlined } from '@ant-design/icons';

interface ComponentRendererProps {
  symbol: string;
  module: string;
  duration?: string;
  barSize?: string;
  onOpen: (symbol: string, module: string) => void;
}

const ComponentRenderer: React.FC<ComponentRendererProps> = ({
  symbol,
  module,
  onOpen,
}) => {
  let title = '';
  let icon = null;

  // 根据 module 参数渲染对应组件
  switch (module.toLowerCase()) {
    case 'chart':
    case '图表':
    case 'k线':
      title = `${symbol} K线图表`;
      icon = <LineChartOutlined />;
      break;
    case 'options':
    case '期权':
      title = `${symbol} 期权链`;
      icon = <FundOutlined />;
      break;
    case 'cycle':
    case '周期':
      title = `${symbol} 周期分析`;
      icon = <HistoryOutlined />;
      break;
    default:
      return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`不支持的模块: ${module}`} />;
  }

  return (
    <div style={{ margin: '8px 0' }}>
      <Button 
        type="primary" 
        ghost 
        size="small"
        icon={icon} 
        onClick={() => onOpen(symbol, module)}
      >
        {title}
      </Button>
    </div>
  );
};

export default ComponentRenderer;
