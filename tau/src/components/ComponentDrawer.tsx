import React from 'react';
import { Drawer, Empty } from 'antd';
import { registry } from '../framework/core/registry';

interface ComponentDrawerProps {
  open: boolean;
  onClose: () => void;
  symbol: string;
  module: string;
  duration?: string;
  barSize?: string;
}

const ComponentDrawer: React.FC<ComponentDrawerProps> = ({
  open,
  onClose,
  symbol,
  module,
  duration,
  barSize,
}) => {
  const Component = registry.getComponent(module);
  const metadata = registry.getMetadata(module);

  const title = metadata?.title ? (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {metadata.icon}
      <span>{symbol} - {metadata.title}</span>
    </div>
  ) : `${symbol} - ${module}`;

  return (
    <Drawer
      title={title}
      placement="right"
      onClose={onClose}
      open={open}
      destroyOnClose
      styles={{ 
        body: { padding: '0' },
        wrapper: { width: typeof window !== 'undefined' && window.innerWidth > 768 ? '85%' : '100%' }
      }}
    >
      {Component ? (
        <Component
          symbol={symbol}
          module={module}
          duration={duration}
          barSize={barSize}
        />
      ) : (
        <div style={{ padding: 24 }}>
          <Empty description={`Module not found: ${module}`} />
        </div>
      )}
    </Drawer>
  );
};

export default ComponentDrawer;
