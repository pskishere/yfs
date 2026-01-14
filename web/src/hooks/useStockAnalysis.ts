/**
 * 股票分析自定义 Hook
 */
import { useState, useRef, useEffect } from 'react';
import { message } from 'antd';
import type { AnalysisResult, HotStock, IndicatorInfo, OptionsData } from '../types/index';
import {
  analyze,
  aiAnalyze,
  getHotStocks,
  getIndicatorInfo,
  refreshAnalyze,
  getAnalysisStatus,
  deleteStock,
  getOptions,
} from '../services/api';

export interface StockOption {
  value: string;
  label: React.ReactNode;
  'data-search-text'?: string;
}

/**
 * 股票分析 Hook
 */
export const useStockAnalysis = () => {
  // 分析相关状态
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [aiAnalysisDrawerVisible, setAiAnalysisDrawerVisible] = useState<boolean>(false);
  const [currentSymbol, setCurrentSymbol] = useState<string>('');
  const [aiStatus, setAiStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');
  const [aiStatusMsg, setAiStatusMsg] = useState<string>('点击AI分析');

  // 热门股票和指标信息
  const [hotStocks, setHotStocks] = useState<HotStock[]>([]);
  const [stockOptions, setStockOptions] = useState<StockOption[]>([]);
  const [indicatorInfoMap, setIndicatorInfoMap] = useState<Record<string, IndicatorInfo>>({});
  const [optionsData, setOptionsData] = useState<OptionsData | null>(null);
  const [optionsLoading, setOptionsLoading] = useState<boolean>(false);

  /**
   * 获取期权数据
   */
  const loadOptions = async (symbol: string) => {
    if (!symbol) return;
    setOptionsLoading(true);
    try {
      const result = await getOptions(symbol);
      if (result && result.success && result.data) {
        setOptionsData(result.data);
      } else {
        setOptionsData(null);
      }
    } catch (error) {
      console.error('获取期权数据失败:', error);
      setOptionsData(null);
    } finally {
      setOptionsLoading(false);
    }
  };

  // 定时器与轮询引用
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const aiPollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const aiPollTokenRef = useRef<number>(0);

  /**
   * 停止 AI 轮询
   */
  const stopAiPolling = () => {
    aiPollTokenRef.current += 1;
    if (aiPollTimerRef.current) {
      clearTimeout(aiPollTimerRef.current);
      aiPollTimerRef.current = null;
    }
  };

  /**
   * AI分析 - 使用轮询方式获取结果
   */
  const runAiAnalysis = async (
    symbol: string,
    duration: string,
    barSize: string,
    model: string,
    baseResult?: AnalysisResult | null
  ): Promise<void> => {
    if (!symbol) return;
    stopAiPolling();
    const pollToken = aiPollTokenRef.current;
    setAiStatus('running');
    setAiStatusMsg('AI分析中...');
    
    try {
      const aiResult = await aiAnalyze(symbol, duration, barSize, model);
      
      // 如果立即返回成功结果
      if (aiResult && aiResult.success && aiResult.ai_analysis) {
        const updatedResult = {
          ...(baseResult || analysisResult),
          ai_analysis: aiResult.ai_analysis,
          model: aiResult.model,
          ai_available: aiResult.ai_available,
        } as AnalysisResult;
        setAnalysisResult(updatedResult);
        setAiAnalysisResult(updatedResult);
        setAiAnalysisDrawerVisible(true);
        setAiStatus('success');
        setAiStatusMsg('AI分析完成');
        message.success('AI分析完成');
        return;
      }
      
      // 如果是进行中状态，开始轮询
      if (aiResult?.status === 'running' || (aiResult as any)?.status === 'running') {
        setAiStatusMsg('AI分析进行中，等待结果...');
        
        let pollCount = 0;
        const maxPolls = 60;
        const pollInterval = 5000;
        
        const pollForResult = async (): Promise<void> => {
          if (pollToken !== aiPollTokenRef.current) return;
          try {
            const statusResult = await getAnalysisStatus(symbol, duration, barSize);
            
            if (statusResult && statusResult.success && statusResult.ai_analysis) {
              const updatedResult = {
                ...(baseResult || analysisResult),
                ai_analysis: statusResult.ai_analysis,
                model: statusResult.model,
                ai_available: statusResult.ai_available,
              } as AnalysisResult;
              setAnalysisResult(updatedResult);
              setAiAnalysisResult(updatedResult);
              setAiAnalysisDrawerVisible(true);
              setAiStatus('success');
              setAiStatusMsg('AI分析完成');
              message.success('AI分析完成');
              return;
            }
            
            pollCount++;
            if (pollCount < maxPolls) {
              aiPollTimerRef.current = setTimeout(() => {
                if (pollToken !== aiPollTokenRef.current) return;
                pollForResult();
              }, pollInterval);
            } else {
              setAiStatus('error');
              setAiStatusMsg('AI分析超时，请稍后重试');
              message.warning('AI分析超时，请稍后重试');
            }
          } catch (pollError: any) {
            setAiStatus('error');
            setAiStatusMsg(pollError?.message || 'AI分析失败');
            message.warning(pollError?.message || 'AI分析失败');
          }
        };
        
        aiPollTimerRef.current = setTimeout(() => {
          if (pollToken !== aiPollTokenRef.current) return;
          pollForResult();
        }, 2000);
        return;
      }
      
      // 其他错误情况
      if (aiResult?.message) {
        setAiStatus('error');
        setAiStatusMsg(aiResult.message);
        message.warning(aiResult.message);
      } else {
        setAiStatus('error');
        setAiStatusMsg('AI分析不可用');
      }
    } catch (e: any) {
      if (e?.response?.status === 202) {
        setAiStatusMsg('AI分析已开始，等待结果...');
        let pollCount = 0;
        const maxPolls = 60;
        const pollInterval = 5000;
        
        const pollForResult = async (): Promise<void> => {
          if (pollToken !== aiPollTokenRef.current) return;
          try {
            const statusResult = await getAnalysisStatus(symbol, duration, barSize);
            if (statusResult && statusResult.success && statusResult.ai_analysis) {
              const updatedResult = {
                ...(baseResult || analysisResult),
                ai_analysis: statusResult.ai_analysis,
                model: statusResult.model,
                ai_available: statusResult.ai_available,
              } as AnalysisResult;
              setAnalysisResult(updatedResult);
              setAiAnalysisResult(updatedResult);
              setAiAnalysisDrawerVisible(true);
              setAiStatus('success');
              setAiStatusMsg('AI分析完成');
              message.success('AI分析完成');
              return;
            }
            pollCount++;
            if (pollCount < maxPolls) {
              aiPollTimerRef.current = setTimeout(() => {
                if (pollToken !== aiPollTokenRef.current) return;
                pollForResult();
              }, pollInterval);
            } else {
              setAiStatus('error');
              setAiStatusMsg('AI分析超时，请稍后重试');
              message.warning('AI分析超时，请稍后重试');
            }
          } catch (pollError: any) {
            setAiStatus('error');
            setAiStatusMsg(pollError?.message || 'AI分析失败');
            message.warning(pollError?.message || 'AI分析失败');
          }
        };
        aiPollTimerRef.current = setTimeout(() => {
          if (pollToken !== aiPollTokenRef.current) return;
          pollForResult();
        }, 2000);
      } else {
        setAiStatus('error');
        setAiStatusMsg(e?.message || 'AI分析失败');
        message.warning(e?.message || 'AI分析失败，但数据已成功获取');
      }
    }
  };

  /**
   * 执行分析
   */
  const handleAnalyze = async (symbol: string, duration: string = '5y', barSize: string = '1 day'): Promise<void> => {
    if (!symbol) {
      message.error('请输入股票代码');
      return;
    }

    stopAiPolling();
    setAnalysisLoading(true);
    setAnalysisResult(null);
    setAiAnalysisResult(null);
    setAiStatus('idle');
    setAiStatusMsg('点击AI分析');

    let dataResult: any = null;
    const pollStatus = async (
      sym: string,
      dur: string,
      bar: string,
      maxAttempts: number = 10,
      intervalMs: number = 1500
    ) => {
      for (let i = 0; i < maxAttempts; i++) {
        try {
          const statusRes = await getAnalysisStatus(sym, dur, bar);
          if (statusRes && statusRes.success) return statusRes;
        } catch (e: any) {
          // 忽略单次错误，继续轮询
        }
        await new Promise((resolve) => setTimeout(resolve, intervalMs));
      }
      throw new Error('分析任务超时，请稍后重试');
    };

    try {
      console.log('开始获取数据:', symbol, duration, barSize);
      dataResult = await analyze(symbol, duration, barSize);

      if (typeof dataResult === 'string') {
        try {
          dataResult = JSON.parse(dataResult);
        } catch (e) {
          throw new Error('无法解析服务器返回的数据');
        }
      }

      if (!dataResult || !dataResult.success) {
        if (
          dataResult &&
          ['pending', 'running'].includes(String(dataResult.status || '').toLowerCase())
        ) {
          message.info('分析任务正在执行，稍后自动获取结果...');
          dataResult = await pollStatus(symbol, duration, barSize);
        } else {
          const errorMsg = dataResult?.message || '分析失败';
          message.error(errorMsg, 5);
          return;
        }
      }

      setAnalysisResult(dataResult);
      setCurrentSymbol(symbol);
      setAnalysisLoading(false);
      // 异步加载期权数据，不阻塞主分析结果
      loadOptions(symbol);
    } catch (error: any) {
      console.error('异常错误:', error);
      message.error(error.message || '分析失败');
      setAnalysisLoading(false);
    }
  };

  /**
   * 刷新分析
   */
  const handleRefreshAnalyze = async (symbol: string, duration: string, barSize: string): Promise<void> => {
    if (!symbol) {
      message.warning('请先进行一次分析');
      return;
    }

    stopAiPolling();
    setAnalysisLoading(true);
    setAnalysisResult(null);
    setAiAnalysisResult(null);
    setAiStatus('idle');
    setAiStatusMsg('点击AI分析');

    try {
      const result = await refreshAnalyze(symbol, duration, barSize);

      if (result && result.success) {
        setAnalysisResult(result);
        setAnalysisLoading(false);
        // 异步加载期权数据
        loadOptions(symbol);
      } else {
        setAnalysisLoading(false);
        let errorMsg = result?.message || '刷新失败';
        if (result?.error_code === 200) {
          errorMsg = `股票代码 "${symbol}" 不存在或无权限查询，请检查代码是否正确`;
        } else if (result?.error_code) {
          errorMsg = `错误[${result.error_code}]: ${result.message}`;
        }
        message.error(errorMsg, 5);
      }
    } catch (error: any) {
      setAnalysisLoading(false);
      message.error(error.message || '刷新失败');
    }
  };

  /**
   * 删除股票缓存
   */
  const handleDeleteStock = async (symbol: string): Promise<void> => {
    const messageKey = `delete-${symbol}`;
    message.loading({ content: `正在删除 ${symbol}`, key: messageKey, duration: 0 });
    try {
      const result = await deleteStock(symbol);
      if (!result.success) {
        message.error(result.message || '删除失败');
        message.destroy(messageKey);
        return;
      }
      setHotStocks((prev) => prev.filter((item) => item.symbol !== symbol));
      setStockOptions((prev) => prev.filter((item) => item.value !== symbol));
      if (currentSymbol === symbol) {
        setCurrentSymbol('');
        setAnalysisResult(null);
        setAiAnalysisResult(null);
      }
      message.success({ content: `已删除 ${symbol}`, key: messageKey, duration: 1.5 });
    } catch (error: any) {
      message.destroy(messageKey);
      message.error(error.message || '删除失败');
    }
  };

  /**
   * 加载热门股票列表
   */
  const loadHotStocks = async (renderOption?: (stock: HotStock) => React.ReactNode): Promise<void> => {
    try {
      const result = await getHotStocks(30);
      if (result.success && result.stocks) {
        setHotStocks(result.stocks);
        if (renderOption) {
          const options = result.stocks.map((stock: HotStock) => {
            const labelText = `${stock.symbol} - ${stock.name || stock.symbol}`;
            return {
              value: stock.symbol,
              label: renderOption(stock),
              'data-search-text': labelText.toUpperCase(),
            };
          });
          setStockOptions(options);
        }
      }
    } catch (error: any) {
      console.error('加载热门股票失败:', error);
    }
  };

  /**
   * 防抖刷新热门股票列表
   */
  const debouncedRefreshHotStocks = (renderOption?: (stock: HotStock) => React.ReactNode): void => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    refreshTimerRef.current = setTimeout(() => loadHotStocks(renderOption), 300);
  };

  /**
   * 加载技术指标解释信息
   */
  const loadIndicatorInfo = async (): Promise<void> => {
    try {
      const result = await getIndicatorInfo();
      if (result.success && result.indicators) {
        setIndicatorInfoMap(result.indicators);
      }
    } catch (error: any) {
      console.error('加载指标解释失败:', error);
    }
  };

  // 清理定时器
  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
      if (aiPollTimerRef.current) {
        clearTimeout(aiPollTimerRef.current);
      }
    };
  }, []);

  return {
    // 状态
    analysisResult,
    aiAnalysisResult,
    analysisLoading,
    aiAnalysisDrawerVisible,
    currentSymbol,
    aiStatus,
    aiStatusMsg,
    hotStocks,
    stockOptions,
    indicatorInfoMap,
    
    // 设置状态的方法
    setAnalysisResult,
    setAiAnalysisDrawerVisible,
    setStockOptions,
    setCurrentSymbol,
    
    // 业务方法
    runAiAnalysis,
    handleAnalyze,
    handleRefreshAnalyze,
    handleDeleteStock,
    loadHotStocks,
    debouncedRefreshHotStocks,
    loadIndicatorInfo,
    stopAiPolling,
    optionsData,
    optionsLoading,
  };
};
