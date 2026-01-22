/**
 * 股票组件渲染器 - 用于在聊天气泡中动态加载并显示股票分析模块
 */
import React, { useState, useEffect } from 'react';
import { Spin, Empty, Button, Drawer } from 'antd';
import { LineChartOutlined, FundOutlined, HistoryOutlined } from '@ant-design/icons';
import { analyze, getOptions } from '../services/api';
import type { AnalysisResult, OptionsData } from '../types/index';

// 导入所有股票分析组件
import { ChartSection } from './ChartSection';
import { OptionsTable } from './OptionsTable';
import { CycleAnalysis } from './CycleAnalysis';

interface StockComponentRendererProps {
  symbol: string;
  module: string;
  duration?: string;
  barSize?: string;
}

const StockComponentRenderer: React.FC<StockComponentRendererProps> = ({
  symbol,
  module,
  duration = '5y',
  barSize = '1 day',
}) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [optionsData, setOptionsData] = useState<OptionsData | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!symbol || hasFetched || !drawerOpen) return;
      setLoading(true);
      try {
        // 根据 module 决定请求的模块
        let modules: string[] = [];
        const lowerModule = module.toLowerCase();
        
        if (['chart', '图表', 'k线'].includes(lowerModule)) {
          modules = ['chart'];
        } else if (['cycle', '周期'].includes(lowerModule)) {
          modules = ['cycle'];
        } else if (['technical', '技术', '技术分析'].includes(lowerModule)) {
          modules = ['technical'];
        }

        // 并行获取股票数据、指标信息
        const promises: [Promise<AnalysisResult>, Promise<any> | null] = [
          analyze(symbol, duration, barSize, modules),
          lowerModule === 'options' || lowerModule === '期权' ? getOptions(symbol) : null
        ];

        const [analysisResult, optionsResult] = await Promise.all(promises);

        if (analysisResult) {
          setData(analysisResult);
        }

        if (optionsResult && optionsResult.success && optionsResult.data) {
          setOptionsData(optionsResult.data);
        }
        setHasFetched(true);
      } catch (error) {
        console.error('加载股票组件数据失败:', error);
        // message.error(`加载 ${symbol} 数据失败`);
      } finally {
        setLoading(false);
      }
    };

    if (drawerOpen) {
      fetchData();
    }
  }, [symbol, module, duration, barSize, drawerOpen, hasFetched]);

  const currencySymbol = (data as any)?.currency_symbol || (data?.extra_data as any)?.currency_symbol || '$';

  let content: React.ReactNode = null;
  let title = '';
  let drawerTitle: React.ReactNode = '';
  let icon = null;

  // 根据 module 参数渲染对应组件
  switch (module.toLowerCase()) {
    case 'chart':
    case '图表':
    case 'k线':
      title = `${symbol} K线图表`;
      drawerTitle = title;
      icon = <LineChartOutlined />;
      content = (
        <ChartSection
          analysisResult={data!}
          currentSymbol={symbol}
        />
      );
      break;
    case 'options':
    case '期权':
      title = `${symbol} 期权链`;
      drawerTitle = (
        <span>
          {title}
          {optionsData?.expiration_dates && (
            <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
              共 {optionsData.expiration_dates.length} 个到期日
            </span>
          )}
        </span>
      );
      icon = <FundOutlined />;
      content = optionsData ? (
        <OptionsTable
          data={optionsData}
        />
      ) : null;
      break;
    case 'cycle':
    case '周期':
      title = `${symbol} 周期分析`;
      drawerTitle = (
        <span>
          {title}
          {(data as any)?.indicators?.cycle_summary && (
            <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
              {(data as any).indicators.cycle_summary}
            </span>
          )}
        </span>
      );
      icon = <HistoryOutlined />;
      content = (
        <CycleAnalysis
          analysisResult={data!}
          currencySymbol={currencySymbol}
        />
      );
      break;
    default:
      return <Empty description={`不支持的模块: ${module}`} />;
  }

  return (
    <>
      <Button 
        type="primary" 
        ghost 
        size="small"
        icon={icon} 
        onClick={() => setDrawerOpen(true)}
        style={{ margin: '4px 8px 4px 0' }}
      >
        {title}
      </Button>
      <Drawer
        title={drawerTitle}
        placement="right"
        onClose={() => setDrawerOpen(false)}
        open={drawerOpen}
        destroyOnClose
        styles={{ 
          body: { padding: '0' },
          wrapper: { width: window.innerWidth > 768 ? '85%' : '100%' }
        }}
      >
        <div style={{ padding: '24px' }}>
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', background: '#f9f9f9', borderRadius: '8px', margin: '10px 0' }}>
              <Spin />
              <div style={{ marginTop: 8, color: '#999' }}>正在加载 {symbol} {module} 数据...</div>
            </div>
          ) : (!data && module.toLowerCase() !== 'options' && module.toLowerCase() !== '期权') || (module.toLowerCase() === 'options' && !optionsData && !loading) ? (
            <Empty description={`未能获取 ${symbol} 的数据`} />
          ) : (
            content
          )}
        </div>
      </Drawer>
    </>
  );
};

export default StockComponentRenderer;
