import React, { useState, useEffect } from 'react';
import { Spin, Empty } from 'antd';
import { analyze, getOptions } from '../../../services/api';
import type { AnalysisResult, OptionsData } from '../../../types/index';
import { ChartSection } from './ChartSection';
import { OptionsTable } from './OptionsTable';
import { CycleAnalysis } from './CycleAnalysis';

interface FinancialDetailViewProps {
  symbol: string;
  module: string;
  duration?: string;
  barSize?: string;
}

export const FinancialDetailView: React.FC<FinancialDetailViewProps> = ({
  symbol,
  module,
  duration = '5y',
  barSize = '1 day',
}) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [optionsData, setOptionsData] = useState<OptionsData | null>(null);
  const [hasFetched, setHasFetched] = useState(false);

  // Reset state when symbol or module changes
  useEffect(() => {
    setData(null);
    setOptionsData(null);
    setHasFetched(false);
  }, [symbol, module]);

  useEffect(() => {
    const fetchData = async () => {
      if (!symbol || hasFetched) return;
      setLoading(true);
      try {
        let modules: string[] = [];
        const lowerModule = module.toLowerCase();
        
        if (['chart', '图表', 'k线'].includes(lowerModule)) {
          modules = ['chart'];
        } else if (['cycle', '周期'].includes(lowerModule)) {
          modules = ['cycle'];
        } else if (['technical', '技术', '技术分析'].includes(lowerModule)) {
          modules = ['technical'];
        }

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
        console.error('Failed to load financial data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol, module, duration, barSize, hasFetched]);

  const currencySymbol = (data as any)?.currency_symbol || (data?.extra_data as any)?.currency_symbol || '$';

  let content: React.ReactNode = null;
  let titleInfo: React.ReactNode = null;

  switch (module.toLowerCase()) {
    case 'chart':
    case '图表':
    case 'k线':
      content = (
        <ChartSection
          analysisResult={data!}
          currentSymbol={symbol}
        />
      );
      break;
    case 'options':
    case '期权':
      titleInfo = optionsData?.expiration_dates && (
        <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
          共 {optionsData.expiration_dates.length} 个到期日
        </span>
      );
      content = optionsData ? (
        <OptionsTable
          data={optionsData}
        />
      ) : null;
      break;
    case 'cycle':
    case '周期':
      titleInfo = (data as any)?.indicators?.cycle_summary && (
        <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
          {(data as any).indicators.cycle_summary}
        </span>
      );
      content = (
        <CycleAnalysis
          analysisResult={data!}
          currencySymbol={currencySymbol}
        />
      );
      break;
    default:
      content = <Empty description={`不支持的模块: ${module}`} />;
  }

  return (
    <div style={{ padding: '24px' }}>
      {titleInfo && <div style={{ marginBottom: 16 }}>{titleInfo}</div>}
      
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
  );
};
