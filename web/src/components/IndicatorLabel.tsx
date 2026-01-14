/**
 * 带知识讲解的指标标签组件
 */
import React, { useState, useEffect } from 'react';
import { Space, Drawer, Typography } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import type { IndicatorInfo } from '../types/index';

const { Text, Title } = Typography;

interface IndicatorLabelProps {
  label: string;
  indicatorKey: string;
  indicatorInfoMap: Record<string, IndicatorInfo>;
}

/**
 * 检测是否为移动端
 */
const useIsMobile = (): boolean => {
  const [isMobile, setIsMobile] = useState<boolean>(
    typeof window !== 'undefined' && window.innerWidth <= 768
  );

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
};

/**
 * 创建指标知识讲解的Popover内容
 */
const createKnowledgeContent = (info: IndicatorInfo, isMobile: boolean): React.ReactNode => {
  const maxWidth = isMobile ? 'calc(100vw - 32px)' : 400;
  
  return (
    <div style={{ 
      maxWidth, 
      fontSize: 13, 
      paddingTop: 0,
      wordWrap: 'break-word',
      overflowWrap: 'break-word'
    }}>
      <Title level={5} style={{ marginTop: 0, marginBottom: 0, fontSize: 14 }}>
        {info.name}
      </Title>
      <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
        <strong>说明：</strong>{info.description}
      </Text>
      {info.calculation && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>计算方法：</strong>{info.calculation}
        </Text>
      )}
      {info.reference_range && Object.keys(info.reference_range).length > 0 && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>参考范围：</strong>
          <ul style={{ marginTop: 4, marginBottom: 0, paddingLeft: 20 }}>
            {Object.entries(info.reference_range).map(([key, value]) => (
              <li key={key} style={{ marginBottom: 4 }}>{value}</li>
            ))}
          </ul>
        </Text>
      )}
      {info.interpretation && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>解读：</strong>{info.interpretation}
        </Text>
      )}
      {info.usage && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>使用方法：</strong>{info.usage}
        </Text>
      )}
    </div>
  );
};

/**
 * 指标标签组件
 */
export const IndicatorLabel: React.FC<IndicatorLabelProps> = ({ label, indicatorKey, indicatorInfoMap }) => {
  const info = indicatorInfoMap[indicatorKey];
  const isMobile = useIsMobile();
  const [open, setOpen] = useState<boolean>(false);
  
  if (!info) {
    return <span>{label}</span>;
  }

  return (
    <Space>
      <span>{label}</span>
        <QuestionCircleOutlined
          style={{
            color: '#00b96b',
            cursor: 'pointer',
            fontSize: 12,
          }}
        onClick={() => setOpen(true)}
        />
      <Drawer
        title={info.name}
        placement="left"
        open={open}
        onClose={() => setOpen(false)}
        size={isMobile ? 'large' : 420}
        destroyOnClose
      >
        {createKnowledgeContent(info, isMobile)}
      </Drawer>
    </Space>
  );
};
