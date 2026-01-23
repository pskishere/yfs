import React from 'react';
import { Button, Empty } from 'antd';
import { AppstoreOutlined } from '@ant-design/icons';
import { registry } from '../framework/core/registry';

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
  // Check if module is registered
  const Component = registry.getComponent(module);
  const metadata = registry.getMetadata(module);

  if (!Component) {
     return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`不支持的模块: ${module}`} />;
  }
  
  // Use metadata if available, otherwise fallback
  const title = metadata?.title ? `${symbol} ${metadata.title}` : `${symbol} ${module}`;
  const icon = metadata?.icon || <AppstoreOutlined />;

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
