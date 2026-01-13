/**
 * 信号渲染工具 - 将 emoji 转换为 antd icon
 */
import React from 'react';
import {
  RiseOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  CloudOutlined,
} from '@ant-design/icons';

/**
 * 将信号文本中的 emoji 替换为 antd icon
 */
export const renderSignalWithIcon = (signal: string): React.ReactNode => {
  const parts: React.ReactNode[] = [];
  let remainingText = signal;
  let keyIndex = 0;

  // 定义 emoji 到 icon 的映射
  const emojiMap: Array<{ pattern: RegExp; icon: React.ReactElement }> = [
    // 上升趋势图表 (看涨信号) - 红色
    { pattern: /📈/g, icon: <RiseOutlined style={{ color: '#cf1322', marginRight: 4 }} /> },
    // 柱状图 (看跌信号) - 蓝色
    { pattern: /📊/g, icon: <BarChartOutlined style={{ color: '#1890ff', marginRight: 4 }} /> },
    // 绿色圆圈 (看涨/成功)
    { pattern: /🟢/g, icon: <CheckCircleOutlined style={{ color: '#3f8600', marginRight: 4 }} /> },
    // 红色圆圈 (看跌/警告)
    { pattern: /🔴/g, icon: <CloseCircleOutlined style={{ color: '#cf1322', marginRight: 4 }} /> },
    // 黄色警告
    { pattern: /⚠️/g, icon: <WarningOutlined style={{ color: '#faad14', marginRight: 4 }} /> },
    // 闪电 (趋势强度)
    { pattern: /⚡/g, icon: <ThunderboltOutlined style={{ color: '#faad14', marginRight: 4 }} /> },
    // 云 (盘整)
    { pattern: /☁️/g, icon: <CloudOutlined style={{ color: '#8c8c8c', marginRight: 4 }} /> },
    // 灰色圆圈 (中性) - 使用简单的圆点
    { pattern: /⚪|⚫|🔘/g, icon: <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '0', backgroundColor: '#d9d9d9', marginRight: 4, verticalAlign: 'middle' }} /> },
  ];

  // 查找所有 emoji 的位置
  const matches: Array<{ index: number; emoji: string; icon: React.ReactElement }> = [];
  emojiMap.forEach(({ pattern, icon }) => {
    const regex = new RegExp(pattern.source, 'g');
    let match;
    while ((match = regex.exec(remainingText)) !== null) {
      matches.push({
        index: match.index,
        emoji: match[0],
        icon: React.cloneElement(icon, { key: `icon-${keyIndex++}` }),
      });
    }
  });

  // 按位置排序
  matches.sort((a, b) => a.index - b.index);

  // 构建结果
  let lastIndex = 0;
  matches.forEach((match) => {
    // 添加 emoji 之前的文本
    if (match.index > lastIndex) {
      parts.push(remainingText.substring(lastIndex, match.index));
    }
    // 添加 icon
    parts.push(match.icon);
    lastIndex = match.index + match.emoji.length;
  });

  // 添加剩余文本
  if (lastIndex < remainingText.length) {
    parts.push(remainingText.substring(lastIndex));
  }

  // 如果没有匹配到任何 emoji，直接返回原文本
  return parts.length > 0 ? <span>{parts}</span> : signal;
};
