import React, { useState, useEffect } from 'react';
import { Spin, Empty } from 'antd';
import { registry } from '../../../framework/core/registry';
import { analyze, getOptions } from '../service';
import type { AnalysisResult, OptionsData } from '../../../types/index';
import { ChartSection } from './ChartSection';
import { OptionsTable } from './OptionsTable';
import { CycleAnalysis } from './CycleAnalysis';
import NewsSection from './NewsSection';
import IndicatorSection from './IndicatorSection';

interface StockDetailViewProps {
  symbol: string;
  module: string;
  duration?: string;
  barSize?: string;
}

export const StockDetailView: React.FC<StockDetailViewProps> = ({
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
        } else if (['technical', '技术', '技术分析', 'indicators', '指标'].includes(lowerModule)) {
          modules = ['technical'];
        } else if (['news', '新闻'].includes(lowerModule)) {
          modules = ['news'];
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
      // 优先使用 indicators 中的 options_summary
      const currentOptions = (data?.indicators?.options_summary || optionsData) as any;
      const expirations = currentOptions?.expirations || currentOptions?.expiration_dates || [];
      titleInfo = expirations.length > 0 && (
        <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
          共 {expirations.length} 个到期日
        </span>
      );
      content = currentOptions ? (
        <OptionsTable
          data={currentOptions}
        />
      ) : null;
      break;
    case 'technical':
    case '技术':
    case '技术分析':
    case 'indicators':
    case '指标':
      content = (
        <IndicatorSection
          indicators={data?.indicators || {} as any}
        />
      );
      break;
    case 'news':
    case '新闻':
      content = (
        <NewsSection
          newsData={data?.indicators?.news_data || []}
          currentSymbol={symbol}
        />
      );
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
          <div style={{ marginTop: 8, color: '#999' }}>正在加载 {symbol} {registry.getMetadata(module)?.title || module} 数据...</div>
        </div>
      ) : (!data && !['options', '期权', 'news', '新闻', 'technical', '指标'].includes(module.toLowerCase())) || (['options', '期权'].includes(module.toLowerCase()) && !optionsData && !data?.indicators?.options_summary && !loading) ? (
        <Empty description={`未能获取 ${symbol} 的数据`} />
      ) : (
        content
      )}
    </div>
  );
};
