/**
 * 股票组件渲染器 - 用于在聊天气泡中动态加载并显示股票分析模块
 */
import React, { useState, useEffect } from 'react';
import { Spin, Empty } from 'antd';
import { analyze, getIndicatorInfo, getOptions } from '../services/api';
import type { AnalysisResult, IndicatorInfo, OptionsData } from '../types/index';

// 导入所有股票分析组件
import { PriceInfo } from './PriceInfo';
import { TechnicalIndicators } from './TechnicalIndicators';
import { ChartSection } from './ChartSection';
import { FundamentalData } from './FundamentalData';
import { MarketData } from './MarketData';
import { OptionsTable } from './OptionsTable';
import { CycleAnalysis } from './CycleAnalysis';
import { PivotPoints } from './PivotPoints';
import { IndicatorLabel } from './IndicatorLabel';

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
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [indicatorInfoMap, setIndicatorInfoMap] = useState<Record<string, IndicatorInfo>>({});
  const [optionsData, setOptionsData] = useState<OptionsData | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!symbol) return;
      setLoading(true);
      try {
        // 并行获取股票数据、指标信息
        const promises: [Promise<AnalysisResult>, Promise<any>, Promise<any> | null] = [
          analyze(symbol, duration, barSize),
          getIndicatorInfo(),
          module.toLowerCase() === 'options' || module.toLowerCase() === '期权' ? getOptions(symbol) : null
        ];

        const [analysisResult, infoResult, optionsResult] = await Promise.all(promises);

        if (analysisResult) {
          setData(analysisResult);
        }

        if (infoResult && infoResult.success && infoResult.data) {
          const infoMap: Record<string, IndicatorInfo> = {};
          infoResult.data.forEach((info: IndicatorInfo) => {
            infoMap[info.key] = info;
          });
          setIndicatorInfoMap(infoMap);
        }

        if (optionsResult && optionsResult.success && optionsResult.data) {
          setOptionsData(optionsResult.data);
        }
      } catch (error) {
        console.error('加载股票组件数据失败:', error);
        // message.error(`加载 ${symbol} 数据失败`);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol, module, duration, barSize]);

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', background: '#f9f9f9', borderRadius: '8px', margin: '10px 0' }}>
        <Spin tip={`正在加载 ${symbol} ${module} 数据...`} />
      </div>
    );
  }

  if (!data && module.toLowerCase() !== 'options' && module.toLowerCase() !== '期权') {
    return <Empty description={`未能获取 ${symbol} 的数据`} />;
  }

  // 辅助函数：创建指标标签
  const createIndicatorLabel = (label: string, indicatorKey: string) => (
    <IndicatorLabel
      label={label}
      indicatorKey={indicatorKey}
      indicatorInfoMap={indicatorInfoMap}
    />
  );

  const currencySymbol = (data as any)?.currency_symbol || (data?.extra_data as any)?.currency_symbol || '$';
  const stockName = data?.name || '';

  // 根据 module 参数渲染对应组件
  switch (module.toLowerCase()) {
    case 'price':
    case '价格':
      return (
        <div className="stock-module-bubble">
          <PriceInfo
            analysisResult={data!}
            currentSymbol={symbol}
            stockName={stockName}
            currencySymbol={currencySymbol}
            createIndicatorLabel={createIndicatorLabel}
          />
        </div>
      );
    case 'indicators':
    case '指标':
    case '技术指标':
      return (
        <div className="stock-module-bubble">
          <TechnicalIndicators
            analysisResult={data!}
            currencySymbol={currencySymbol}
            createIndicatorLabel={createIndicatorLabel}
          />
        </div>
      );
    case 'chart':
    case '图表':
    case 'k线':
      return (
        <div className="stock-module-bubble">
          <ChartSection
            analysisResult={data!}
            currentSymbol={symbol}
          />
        </div>
      );
    case 'fundamental':
    case '基本面':
      return (
        <div className="stock-module-bubble">
          <FundamentalData
            analysisResult={data!}
            currencySymbol={currencySymbol}
            createIndicatorLabel={createIndicatorLabel}
          />
        </div>
      );
    case 'news':
    case '新闻':
      return (
        <div className="stock-module-bubble">
          <NewsData
            analysisResult={data!}
          />
        </div>
      );
    case 'market':
    case '市场':
    case '行情':
      return (
        <div className="stock-module-bubble">
          <MarketData
            analysisResult={data!}
            currencySymbol={currencySymbol}
            createIndicatorLabel={createIndicatorLabel}
          />
        </div>
      );
    case 'options':
    case '期权':
      if (!optionsData) return <Empty description={`未能获取 ${symbol} 的期权数据`} />;
      return (
        <div className="stock-module-bubble">
          <OptionsTable
            data={optionsData}
            createIndicatorLabel={createIndicatorLabel}
          />
        </div>
      );
    case 'cycle':
    case '周期':
      return (
        <div className="stock-module-bubble">
          <CycleAnalysis
            analysisResult={data!}
            currencySymbol={currencySymbol}
            createIndicatorLabel={createIndicatorLabel}
          />
        </div>
      );
    case 'pivot':
    case '枢轴点':
      return (
        <div className="stock-module-bubble">
          <PivotPoints
            analysisResult={data!}
            currencySymbol={currencySymbol}
            createIndicatorLabel={createIndicatorLabel}
          />
        </div>
      );
    default:
      return <Empty description={`不支持的模块: ${module}`} />;
  }
};

export default StockComponentRenderer;
