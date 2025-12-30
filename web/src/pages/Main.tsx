/**
 * 主页面 - 股票分析功能
 */
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import {
  Table,
  Button,
  Space,
  Tag,
  Form,
  Input,
  InputNumber,
  Select,
  AutoComplete,
  Descriptions,
  Spin,
  message,
  Drawer,
  Tabs,
  Collapse,
  Pagination,
  Modal,
  Popover,
  Menu,
} from 'antd';
import {
  InboxOutlined,
  ReloadOutlined,
  DollarOutlined,
  ShoppingOutlined,
  BarChartOutlined,
  RobotOutlined,
  RiseOutlined,
  FallOutlined,
  RightOutlined,
  ShareAltOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  MoneyCollectOutlined,
  ThunderboltOutlined,
  CloudOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  MenuOutlined,
  TeamOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import {
  getPositions,
  buy,
  sell,
  getOrders,
  cancelOrder,
  analyze,
  aiAnalyze,
  getHotStocks,
  getIndicatorInfo,
  refreshAnalyze,
  getAnalysisStatus,
  deleteStock,
} from '../services/api';
import type {
  Position,
  Order,
  AnalysisResult,
  HotStock,
  IndicatorInfo,
} from '../types/index';
import TradingViewChart from '../components/TradingViewChart';
import { IndicatorLabel } from '../components/IndicatorLabel';
import { FinancialTable } from '../components/FinancialTable';
import { getPositionColumns, getOrderColumns } from '../config/tableColumns';
import { formatValue, formatLargeNumber, getRSIStatus, statusMaps, translateRating, translateAction, formatDateTime } from '../utils/formatters';
import './Main.css';

// TabPane 已在 Ant Design v6 中移除，使用 items prop 代替

interface StockOption {
  value: string;
  label: React.ReactNode;
  'data-search-text'?: string;
}

/**
 * 将信号文本中的 emoji 替换为 antd icon
 */
const renderSignalWithIcon = (signal: string): React.ReactNode => {
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

const MainPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // 持仓相关状态
  const [positions, setPositions] = useState<Position[]>([]);
  const [positionsLoading, setPositionsLoading] = useState<boolean>(false);

  // 交易订单相关状态
  const [tradeForm] = Form.useForm();
  const [orders, setOrders] = useState<Order[]>([]);
  const [tradeLoading, setTradeLoading] = useState<boolean>(false);
  const [orderLoading, setOrderLoading] = useState<boolean>(false);
  const [tradeDrawerVisible, setTradeDrawerVisible] = useState<boolean>(false);
  const [tradeDrawerTab, setTradeDrawerTab] = useState<string>('trade-form');

  // 分析相关状态
  const [analyzeForm] = Form.useForm();
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [aiAnalysisDrawerVisible, setAiAnalysisDrawerVisible] = useState<boolean>(false);
  const [currentSymbol, setCurrentSymbol] = useState<string>('');
  const [aiStatus, setAiStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');
  const [aiStatusMsg, setAiStatusMsg] = useState<string>('点击AI分析');

  const aiStatusColorMap: Record<typeof aiStatus, 'default' | 'processing' | 'success' | 'error'> = {
    idle: 'default',
    running: 'processing',
    success: 'success',
    error: 'error',
  };

  const currencySymbol = useMemo(() => {
    if (!analysisResult) return '$';
    return (
      (analysisResult as any)?.currency_symbol ||
      (analysisResult as any)?.currencySymbol ||
      (analysisResult.extra_data as any)?.currency_symbol ||
      (analysisResult.extra_data as any)?.currencySymbol ||
      '$'
    );
  }, [analysisResult]);

  const stockName = useMemo(() => {
    if (!analysisResult) return '';
    return (
      (analysisResult as any)?.stock_name ||
      (analysisResult.extra_data as any)?.stock_name ||
      ''
    );
  }, [analysisResult]);

  const formatCurrency = (value?: number, decimals: number = 2) =>
    `${currencySymbol}${formatValue(value ?? 0, decimals)}`;

  const stopAiPolling = () => {
    aiPollTokenRef.current += 1;
    if (aiPollTimerRef.current) {
      clearTimeout(aiPollTimerRef.current);
      aiPollTimerRef.current = null;
    }
  };

  // 热门股票相关状态（仅用于刷新下拉列表，不单独展示）
  const [, setHotStocks] = useState<HotStock[]>([]);
  
  // 新闻分页状态
  const [newsPage, setNewsPage] = useState<number>(1);
  const [stockOptions, setStockOptions] = useState<StockOption[]>([]);

  // 定时器与轮询引用
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const aiPollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const aiPollTokenRef = useRef<number>(0);
  // 标记是否已从 URL 加载过
  const hasLoadedFromUrlRef = useRef<boolean>(false);

  // 技术指标解释信息
  const [indicatorInfoMap, setIndicatorInfoMap] = useState<Record<string, IndicatorInfo>>({});
  const [cyclePeriodPageSize, setCyclePeriodPageSize] = useState<number>(10);
  const [cyclePeriodCurrent, setCyclePeriodCurrent] = useState<number>(1);
  const [yearlyCyclePageSize, setYearlyCyclePageSize] = useState<number>(10);
  const [yearlyCycleCurrent, setYearlyCycleCurrent] = useState<number>(1);
  const [monthlyCyclePageSize, setMonthlyCyclePageSize] = useState<number>(10);
  const [monthlyCycleCurrent, setMonthlyCycleCurrent] = useState<number>(1);
  const [pageNavigatorVisible, setPageNavigatorVisible] = useState<boolean>(false);

  // 响应式状态：检测是否为移动端
  const [isMobile, setIsMobile] = useState<boolean>(typeof window !== 'undefined' && window.innerWidth <= 768);

  /**
   * 跳转到页面指定模块
   */
  const scrollToSection = (sectionId: string) => {
    // 先关闭菜单
    setPageNavigatorVisible(false);
    
    // 延迟执行，确保菜单关闭动画完成和DOM更新
    setTimeout(() => {
      // 尝试多种方式查找元素
      let element = document.getElementById(sectionId);
      
      // 如果直接查找失败，尝试通过 querySelector
      if (!element) {
        element = document.querySelector(`#${sectionId}`) as HTMLElement;
      }
      
      if (element) {
        // 计算偏移量，考虑固定头部
        const headerOffset = 80;
        const rect = element.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const elementTop = rect.top + scrollTop;
        const offsetPosition = elementTop - headerOffset;

        // 使用 window.scrollTo 方法，更精确控制位置
        window.scrollTo({
          top: Math.max(0, offsetPosition),
          behavior: 'smooth',
        });
        
        // 备用方案：如果平滑滚动失败，使用 scrollIntoView
        setTimeout(() => {
          const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
          const targetScrollTop = elementTop - headerOffset;
          // 如果滚动距离超过10px，说明可能没有滚动到位，使用 scrollIntoView
          if (Math.abs(currentScrollTop - targetScrollTop) > 10) {
            element.scrollIntoView({
              behavior: 'smooth',
              block: 'start',
            });
            // 再次调整偏移
            setTimeout(() => {
              window.scrollTo({
                top: Math.max(0, elementTop - headerOffset),
                behavior: 'smooth',
              });
            }, 100);
          }
        }, 300);
      } else {
        console.warn(`未找到元素: ${sectionId}`);
        // 尝试查找所有可能的元素
        const allElements = document.querySelectorAll(`[id*="${sectionId}"]`);
        if (allElements.length > 0) {
          console.log('找到的相关元素:', allElements);
          const firstElement = allElements[0] as HTMLElement;
          const headerOffset = 80;
          const rect = firstElement.getBoundingClientRect();
          const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
          const elementTop = rect.top + scrollTop;
          const offsetPosition = elementTop - headerOffset;
          window.scrollTo({
            top: Math.max(0, offsetPosition),
            behavior: 'smooth',
          });
        }
      }
    }, 200);
  };

  /**
   * 加载持仓数据
   */
  const loadPositions = async (): Promise<void> => {
    setPositionsLoading(true);
    try {
      const result = await getPositions();
      if (result.success) {
        setPositions(result.data || []);
      } else {
        message.error(result.message || '查询失败');
      }
    } catch (err: any) {
      message.error(err.message);
    } finally {
      setPositionsLoading(false);
    }
  };

  /**
   * 加载订单列表
   */
  const loadOrders = async (): Promise<void> => {
    setOrderLoading(true);
    try {
      const result = await getOrders();
      if (result.success) {
        setOrders(result.data || []);
      } else {
        message.error(result.message || '查询失败');
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setOrderLoading(false);
    }
  };

  /**
   * 提交订单
   */
  const handleTradeSubmit = async (values: any): Promise<void> => {
    setTradeLoading(true);
    try {
      const { symbol, action, quantity, orderType, limitPrice } = values;
      const price = orderType === 'LMT' ? limitPrice : null;

      const result = action === 'BUY'
        ? await buy(symbol, quantity, price)
        : await sell(symbol, quantity, price);

      if (result.success) {
        const orderTypeText = orderType === 'LMT' ? '限价' : '市价';
        const actionText = action === 'BUY' ? '买单' : '卖单';
        message.success(`${actionText}已提交: #${result.order_id} (${orderTypeText})`);
        tradeForm.resetFields();
        await loadOrders();
        await loadPositions();
      } else {
        message.error(result.message || '提交失败');
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setTradeLoading(false);
    }
  };

  /**
   * 撤销订单
   */
  const handleCancelOrder = async (orderId: number): Promise<void> => {
    try {
      const result = await cancelOrder(orderId);
      if (result.success) {
        message.success('订单已撤销');
        await loadOrders();
        await loadPositions();
      } else {
        message.error(result.message || '撤销失败');
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  /**
   * AI分析 - 使用轮询方式获取结果，避免超时
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
        const maxPolls = 60; // 最多轮询 60 次（5分钟）
        const pollInterval = 5000; // 每 5 秒轮询一次
        
        const pollForResult = async (): Promise<void> => {
          if (pollToken !== aiPollTokenRef.current) return;
          try {
            const statusResult = await getAnalysisStatus(symbol, duration, barSize);
            
            if (statusResult && statusResult.success && statusResult.ai_analysis) {
              // AI 分析完成
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
            
            // 继续轮询
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
        
        // 延迟 2 秒后开始第一次轮询
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
      // 处理 202 状态码或其他错误
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
   * 执行分析 - 使用合并后的接口，一次请求同时获取技术分析和AI分析
   */
  const handleAnalyze = async (values: any): Promise<void> => {
    if (!values || !values.symbol) {
      message.error('请输入股票代码');
      return;
    }

    stopAiPolling();
    setAnalysisLoading(true);
      setAnalysisResult(null);
      setAiAnalysisResult(null);
      setAiStatus('idle');
      setAiStatusMsg('点击AI分析');
      setNewsPage(1); // 重置新闻页码

    let dataResult: any = null;
    const pollStatus = async (
      symbol: string,
      duration: string,
      barSize: string,
      maxAttempts: number = 10,
      intervalMs: number = 1500
    ) => {
      for (let i = 0; i < maxAttempts; i++) {
        try {
          const statusRes = await getAnalysisStatus(symbol, duration, barSize);
          if (statusRes && statusRes.success) return statusRes;
        } catch (e: any) {
          // 忽略单次错误，继续轮询
        }
        await new Promise((resolve) => setTimeout(resolve, intervalMs));
      }
      throw new Error('分析任务超时，请稍后重试');
    };

    // 第一步：获取数据并保存到数据库（只在此阶段显示 loading）
    try {
      const { symbol, duration, barSize } = values;
      const durationValue = duration || '5y';
      const barSizeValue = barSize || '1 day';

      console.log('开始获取数据:', symbol, durationValue, barSizeValue);
      dataResult = await analyze(symbol, durationValue, barSizeValue);

      if (typeof dataResult === 'string') {
        try {
          dataResult = JSON.parse(dataResult);
        } catch (e) {
          throw new Error('无法解析服务器返回的数据');
        }
      }

      if (!dataResult || !dataResult.success) {
        // 处理排队中的情况
        if (
          dataResult &&
          ['pending', 'running'].includes(String(dataResult.status || '').toLowerCase())
        ) {
          message.info('分析任务正在执行，稍后自动获取结果...');
          dataResult = await pollStatus(symbol, durationValue, barSizeValue);
        } else {
          const errorMsg = dataResult?.message || '分析失败';
          message.error(errorMsg, 5);
          return;
        }
      }

      setAnalysisResult(dataResult);
      setCurrentSymbol(symbol);
      // 更新 URL 参数
      updateUrlParams(symbol);
      // 数据阶段结束，关闭 loading
      setAnalysisLoading(false);
      // 开始分析时不自动触发AI分析，需要用户手动点击AI分析按钮
    } catch (error: any) {
      console.error('异常错误:', error);
      message.error(error.message || '分析失败');
      setAnalysisLoading(false);
    }
  };

  /**
   * 刷新分析 - 强制重新获取数据，不使用缓存
   */
  const handleRefreshAnalyze = async (): Promise<void> => {
    if (!currentSymbol) {
      message.warning('请先进行一次分析');
      return;
    }

    stopAiPolling();
    const formValues = analyzeForm.getFieldsValue();
    const duration = formValues.duration || '5y';
    const barSize = formValues.barSize || '1 day';

    setAnalysisLoading(true);
    setAnalysisResult(null);
    setAiAnalysisResult(null);
    setAiStatus('idle');
    setAiStatusMsg('点击AI分析');

    // 第一步：刷新数据（只在此阶段显示 loading）
    try {
      const result = await refreshAnalyze(currentSymbol, duration, barSize);

      if (result && result.success) {
        setAnalysisResult(result);
        setAnalysisLoading(false);
        // 刷新时不自动触发AI分析，需要用户手动点击AI分析按钮
      } else {
        setAnalysisLoading(false);
        let errorMsg = result?.message || '刷新失败';
        if (result?.error_code === 200) {
          errorMsg = `股票代码 "${currentSymbol}" 不存在或无权限查询，请检查代码是否正确`;
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
   * 删除股票缓存并刷新下拉选项
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
   * 构建带删除按钮的下拉项
   */
  const renderStockOption = (stock: HotStock): React.ReactNode => {
    const labelText = `${stock.symbol} - ${stock.name || stock.symbol}`;
    const handleConfirm = (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      Modal.confirm({
        title: `确认删除 ${stock.symbol} 吗？`,
        okText: '确认',
        cancelText: '取消',
        centered: true,
        onOk: () => handleDeleteStock(stock.symbol),
      });
    };
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          width: '100%',
        }}
      >
        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {labelText}
        </span>
        <Button
          type="link"
          danger
          size="small"
          icon={<DeleteOutlined />}
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleConfirm}
          aria-label={`删除 ${stock.symbol}`}
          style={{ width: 28, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        />
      </div>
    );
  };

  /**
   * 加载热门股票列表
   */
  const loadHotStocks = async (): Promise<void> => {
    try {
      const result = await getHotStocks(30);
      if (result.success && result.stocks) {
        setHotStocks(result.stocks);
        const options = result.stocks.map((stock: HotStock) => {
          const labelText = `${stock.symbol} - ${stock.name || stock.symbol}`;
          return {
            value: stock.symbol,
            label: renderStockOption(stock),
            // 使用自定义属性名避免 React 警告
            'data-search-text': labelText.toUpperCase(),
          };
        });
        setStockOptions(options);
      }
    } catch (error: any) {
      console.error('加载热门股票失败:', error);
      // 失败时不影响使用，只是没有下拉提示
    }
  };

  /**
   * 防抖刷新热门股票列表
   */
  const debouncedRefreshHotStocks = (): void => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    refreshTimerRef.current = setTimeout(() => loadHotStocks(), 300);
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

  /**
   * 创建带知识讲解的指标标签
   */
  const createIndicatorLabel = (label: string, indicatorKey: string): React.ReactNode => {
    return <IndicatorLabel label={label} indicatorKey={indicatorKey} indicatorInfoMap={indicatorInfoMap} />;
  };

  /**
   * 更新 URL 参数（不触发页面刷新）
   */
  const updateUrlParams = (symbol: string): void => {
    const params = new URLSearchParams();
    params.set('symbol', symbol);
    setSearchParams(params, { replace: true });
  };

  /**
   * 分享功能 - 复制带参数的 URL 到剪贴板
   */
  const handleShare = async (): Promise<void> => {
    if (!currentSymbol) {
      message.warning('请先进行一次分析');
      return;
    }
    
    const params = new URLSearchParams();
    params.set('symbol', currentSymbol);
    
    const shareUrl = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    
    try {
      await navigator.clipboard.writeText(shareUrl);
      message.success('分享链接已复制到剪贴板');
    } catch (err) {
      // 降级方案：使用传统方法
      const textArea = document.createElement('textarea');
      textArea.value = shareUrl;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        message.success('分享链接已复制到剪贴板');
      } catch (e) {
        message.error('复制失败，请手动复制链接');
      }
      document.body.removeChild(textArea);
    }
  };

  useEffect(() => {
    loadHotStocks();
    loadIndicatorInfo();

    const handleResize = () => {
      const width = window.innerWidth;
      setIsMobile(width <= 768);
      
      if (width <= 768) {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
          viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover');
        }
      }
    };
    
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  /**
   * 从 URL 参数自动加载分析（仅在首次加载时执行一次）
   */
  useEffect(() => {
    if (hasLoadedFromUrlRef.current) return;
    stopAiPolling();
    
    const symbolFromUrl = searchParams.get('symbol');
    if (symbolFromUrl) {
      hasLoadedFromUrlRef.current = true;
      
      analyzeForm.setFieldsValue({
        symbol: symbolFromUrl.toUpperCase(),
      });
      
      setTimeout(() => {
        handleAnalyze({
          symbol: symbolFromUrl.toUpperCase(),
        });
      }, 100);
    }
  }, []);

  /**
   * 获取趋势标签
   */
  const getTrendTag = (direction: string | undefined): React.ReactNode => {
    const config = direction && statusMaps.trend[direction as keyof typeof statusMaps.trend]
      ? statusMaps.trend[direction as keyof typeof statusMaps.trend]
      : { color: 'default', text: direction || '未知' };
    
    const icon = direction === 'up' ? <RiseOutlined /> :
                 direction === 'down' ? <FallOutlined /> :
                 direction === 'neutral' ? <RightOutlined /> : null;
    
    return (
      <Tag color={config.color}>
        {icon} {config.text}
      </Tag>
    );
  };

  const positionColumns = getPositionColumns(currencySymbol);
  const orderColumns = getOrderColumns(handleCancelOrder);

  return (
    <div className="main-page">
      {/* 固定顶部区域：持仓和股票输入框 */}
      <div className="fixed-top">
        <Space orientation="vertical" style={{ width: '100%' }} size="large">
          {/* 持仓部分 - 已隐藏 */}
          {false && (
            <Collapse
              ghost
              items={[
                {
                  key: 'positions',
                  label: (
                    <span style={{ fontSize: 16, fontWeight: 500 }}>
                      <InboxOutlined style={{ marginRight: 8 }} />
                      持仓 ({positions.length})
                    </span>
                  ),
                  extra: (
                    <Space onClick={(e) => e.stopPropagation()}>
                      <Button
                        type="primary"
                        icon={<DollarOutlined />}
                        onClick={() => {
                          setTradeDrawerVisible(true);
                          setTradeDrawerTab('trade-form');
                        }}
                      >
                        交易
                      </Button>
                      <Button
                        icon={<ReloadOutlined />}
                        onClick={loadPositions}
                        loading={positionsLoading}
                      >
                        刷新
                      </Button>
                    </Space>
                  ),
                  children: (
                    <Table
                      columns={positionColumns}
                      dataSource={positions}
                      rowKey={(record) => record.symbol || `pos-${Math.random().toString(36).substr(2, 9)}`}
                      loading={positionsLoading}
                      pagination={{ pageSize: 5 }}
                      locale={{ emptyText: '暂无持仓' }}
                      size="small"
                    />
                  ),
                },
              ]}
            />
          )}

          {/* 股票输入框 */}
          <div>
            <Form
              form={analyzeForm}
              layout="inline"
              onFinish={handleAnalyze}
              initialValues={{
                duration: '5y',
                barSize: '1 day',
                model: 'deepseek-v3.2:cloud',
              }}
              style={{ marginBottom: 0, width: '100%', display: 'flex', gap: '8px' }}
            >
              <Form.Item
                name="symbol"
                rules={[{ required: true, message: '请输入股票代码' }]}
                style={{ marginBottom: 0, flex: 1, minWidth: 0 }}
              >
                <AutoComplete
                  options={stockOptions}
                  placeholder="股票代号，例如: AAPL"
                  style={{ width: '100%' }}
                  filterOption={(inputValue, option) => {
                    const upper = inputValue.toUpperCase();
                    const opt = option as any;
                    const valueText = (opt?.value || '').toUpperCase();
                    const search = opt?.['data-search-text'] || valueText;
                    return search.includes(upper);
                  }}
                  onSelect={(value) => {
                    analyzeForm.setFieldsValue({ symbol: value });
                  }}
                  onChange={(value) => {
                    analyzeForm.setFieldsValue({ symbol: value.toUpperCase() });
                    // 每次输入时防抖刷新热门股票列表
                    debouncedRefreshHotStocks();
                  }}
                  onFocus={() => {
                    // 获得焦点时立即刷新一次列表
                    loadHotStocks();
                  }}
                />
              </Form.Item>
              <Form.Item
                name="model"
                style={{ marginBottom: 0, flex: 1, minWidth: 0 }}
                tooltip="选择 AI 分析模型"
              >
                <Select
                  placeholder="AI 模型"
                  style={{ width: '100%' }}
                  options={[
                    { label: 'Gemini 3 Flash Preview', value: 'gemini-3-flash-preview:cloud' },
                    { label: 'Qwen3 Next 80B', value: 'qwen3-next:80b-cloud' },
                    { label: 'GPT-OSS 20B', value: 'gpt-oss:20b' },
                    { label: 'GPT-OSS 120B', value: 'gpt-oss:120b-cloud' },
                    { label: 'DeepSeek V3.2', value: 'deepseek-v3.2:cloud' },
                    { label: 'DeepSeek V3.1', value: 'deepseek-v3.1:671b-cloud' },
                  ]}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0, flex: isMobile ? '0 0 auto' : 1, minWidth: 0 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={analysisLoading}
                  icon={isMobile ? <BarChartOutlined /> : null}
                  style={isMobile ? { minWidth: 48, height: 32 } : { width: '100%' }}
                >
                  {isMobile ? '' : '开始分析'}
                </Button>
              </Form.Item>
            </Form>
          </div>
        </Space>
      </div>

      {/* 分析结果区域 */}
      <div style={{ padding: '0 16px', background: '#fff' }} className="analysis-content">

        {analysisLoading && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large">
              <div style={{ padding: '20px 0' }}>
                <div>分析中，请稍候...</div>
              </div>
            </Spin>
          </div>
        )}

        {(analysisResult || aiAnalysisResult) && !analysisLoading && (
          <div style={{ marginTop: 24 }}>
            <Space orientation="vertical" style={{ width: '100%' }} size="middle">
              {/* 技术分析 */}
              {analysisResult && analysisResult.indicators && (
                <div>
                  {/* 价格概览 */}
                  <div>
                    {/* 操作按钮区域 */}
                    <Space style={{ marginBottom: 16 }}>
                          <Button
                            type="default"
                            icon={<ReloadOutlined />}
                            onClick={handleRefreshAnalyze}
                            loading={analysisLoading}
                          >
                        刷新
                          </Button>
                          <Button
                            type="default"
                            icon={<RobotOutlined />}
                            disabled={!currentSymbol || aiStatus === 'running' || !analysisResult}
                            onClick={() => {
                              const formValues = analyzeForm.getFieldsValue();
                              const duration = formValues.duration || '5y';
                              const barSize = formValues.barSize || '1 day';
                              const model = formValues.model || 'deepseek-v3.2:cloud';
                              console.log('手动触发AI分析，使用模型:', model);
                              runAiAnalysis(currentSymbol, duration, barSize, model, analysisResult);
                            }}
                          >
                            AI分析
                          </Button>
                          <Button
                            type="default"
                            icon={<ShareAltOutlined />}
                            onClick={handleShare}
                            disabled={!currentSymbol}
                          >
                            分享
                          </Button>
                          <Tag color={aiStatusColorMap[aiStatus]}>{aiStatusMsg}</Tag>
                    </Space>
                    
                    <div id="section-price-info">
                    <Descriptions
                      title={
                        <span>
                          <BarChartOutlined style={{ marginRight: 8 }} />
                          价格信息
                          {currentSymbol && (
                            <span style={{ marginLeft: 8, color: '#595959', fontWeight: 500 }}>
                              {currentSymbol} {stockName ? `(${stockName})` : ''}
                            </span>
                          )}
                        </span>
                      }
                      bordered
                      column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                      size="small"
                      layout="vertical"
                      items={(() => {
                        const items = [
                        {
                          label: '当前价格',
                            
                          children: (
                              <span style={{ fontSize: 16, fontWeight: 600 }}>
                              {formatCurrency(analysisResult.indicators.current_price)}
                            </span>
                          ),
                        },
                        {
                          label: '价格变化',
                            
                          children: (
                            <Space>
                              {(analysisResult.indicators.price_change_pct ?? 0) >= 0 ? (
                                <RiseOutlined style={{ color: '#3f8600' }} />
                              ) : (
                                <FallOutlined style={{ color: '#cf1322' }} />
                              )}
                              <span style={{
                                  fontSize: 14,
                                fontWeight: 600,
                                color: (analysisResult.indicators.price_change_pct ?? 0) >= 0 ? '#3f8600' : '#cf1322',
                              }}>
                                {formatValue(analysisResult.indicators.price_change_pct)}%
                              </span>
                            </Space>
                          ),
                        },
                        {
                          label: '数据点数',
                            
                          children: `${analysisResult.indicators.data_points || 0}条数据`,
                        },
                        {
                          label: '趋势方向',
                            
                          children: getTrendTag(analysisResult.indicators.trend_direction),
                        },
                        ];

                        // 添加移动平均线
                        const maItems = [5, 10, 20, 50]
                              .map((period) => {
                                const key = `ma${period}`;
                                const value = analysisResult.indicators[key];
                                if (value === undefined) return null as any;
                                const currentPrice = analysisResult.indicators.current_price || 0;
                                const diff = ((currentPrice - value) / value * 100);
                                return {
                              label: createIndicatorLabel(`MA${period}`, 'ma'),
                              
                                  children: (
                                    <Space>
                                      <span style={{
                                        fontSize: 16,
                                        fontWeight: 600,
                                        color: diff >= 0 ? '#3f8600' : '#cf1322',
                                      }}>
                                        {formatCurrency(value)}
                                      </span>
                                      <span style={{
                                        fontSize: 14,
                                        color: diff >= 0 ? '#3f8600' : '#cf1322',
                                      }}>
                                        ({diff >= 0 ? '+' : ''}{diff.toFixed(1)}%)
                                      </span>
                                    </Space>
                                  ),
                                };
                              })
                          .filter(item => item !== null);
                        
                        return [...items, ...maItems];
                      })()}
                    />
                    </div>
                  </div>

                  {/* K线图 */}
                  {currentSymbol && (
                    <div id="section-chart" style={{ marginTop: 24, overflowX: 'auto' }}>
                      <div style={{
                        fontSize: '16px',
                        fontWeight: 500,
                        marginBottom: '16px',
                        display: 'flex',
                        alignItems: 'center',
                      }}>
                        <BarChartOutlined style={{ marginRight: 8 }} />
                        K线图
                      </div>
                      <div style={{ minWidth: '100%', width: '100%' }}>
                        <TradingViewChart
                          symbol={currentSymbol}
                          height={isMobile ? 300 : 500}
                          theme="light"
                          indicators={analysisResult?.indicators}
                          candles={analysisResult?.candles}
                        />
                      </div>
                    </div>
                  )}

                  {/* 技术指标 */}
                  <div id="section-indicators">
                  <Collapse
                    ghost
                    defaultActiveKey={[]}
                    items={[{
                      key: 'indicators',
                      label: (
                        <span>
                          <BarChartOutlined style={{ marginRight: 8 }} />
                          技术指标
                        </span>
                      ),
                      children: (
                        <Descriptions
                          bordered
                          column={{ xxl: 4, xl: 3, lg: 3, md: 2, sm: 1, xs: 1 }}
                          size="small"
                          layout="vertical"
                          items={(() => {
                            const items = [];
                            const indicators = analysisResult.indicators;

                            if (indicators.rsi !== undefined) {
                              items.push({
                                label: createIndicatorLabel('RSI(14)', 'rsi'),
                                children: (
                                  <Space>
                                    <span style={{ fontSize: 14, fontWeight: 600 }}>
                                      {formatValue(indicators.rsi, 1)}
                                    </span>
                                    <Tag color={getRSIStatus(indicators.rsi).color}>
                                      {getRSIStatus(indicators.rsi).text}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.macd !== undefined) {
                              items.push({
                                label: createIndicatorLabel('MACD', 'macd'),
                                children: (
                                  <Space>
                                    <span>{formatValue(indicators.macd, 3)}</span>
                                    {indicators.macd !== undefined && indicators.macd_signal !== undefined && indicators.macd > indicators.macd_signal ? (
                                      <Tag color="success">金叉</Tag>
                                    ) : (
                                      <Tag color="error">死叉</Tag>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.macd_signal !== undefined) {
                              items.push({
                                label: createIndicatorLabel('MACD信号线', 'macd'),
                                
                                children: formatValue(indicators.macd_signal, 3),
                              });
                            }

                            if (indicators.macd_histogram !== undefined) {
                              items.push({
                                label: createIndicatorLabel('MACD柱状图', 'macd'),
                                
                                children: formatValue(indicators.macd_histogram, 3),
                              });
                            }

                            if (indicators.bb_upper) {
                              items.push({
                                label: createIndicatorLabel('布林带上轨', 'bb'),
                                
                                children: formatCurrency(indicators.bb_upper),
                              });
                            }

                            if (indicators.bb_middle) {
                              items.push({
                                label: createIndicatorLabel('布林带中轨', 'bb'),
                                
                                children: formatCurrency(indicators.bb_middle),
                              });
                            }

                            if (indicators.bb_lower) {
                              items.push({
                                label: createIndicatorLabel('布林带下轨', 'bb'),
                                
                                children: formatCurrency(indicators.bb_lower),
                              });
                            }

                            if (indicators.volume_ratio !== undefined) {
                              items.push({
                                label: createIndicatorLabel('成交量比率', 'volume_ratio'),
                                
                                children: (
                                  <Space>
                                    <span style={{ fontSize: 14, fontWeight: 600 }}>
                                      {formatValue(indicators.volume_ratio, 2)}x
                                    </span>
                                    {indicators.volume_ratio > 1.5 ? (
                                      <Tag color="orange">放量</Tag>
                                    ) : indicators.volume_ratio < 0.7 ? (
                                      <Tag color="default">缩量</Tag>
                                    ) : (
                                      <Tag color="success">正常</Tag>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.volatility_20 !== undefined) {
                              items.push({
                                label: createIndicatorLabel('波动率', 'volatility'),
                                
                                children: (
                                  <Space>
                                    <span>{formatValue(indicators.volatility_20)}%</span>
                                    {indicators.volatility_20 > 5 ? (
                                      <Tag color="error">极高</Tag>
                                    ) : indicators.volatility_20 > 3 ? (
                                      <Tag color="warning">高</Tag>
                                    ) : indicators.volatility_20 > 2 ? (
                                      <Tag color="default">中</Tag>
                                    ) : (
                                      <Tag color="success">低</Tag>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.atr !== undefined) {
                              items.push({
                                label: createIndicatorLabel('ATR', 'atr'),
                                
                                children: `${formatCurrency(indicators.atr)} (${formatValue(indicators.atr_percent, 1)}%)`,
                              });
                            }

                            if (indicators.kdj_k !== undefined) {
                              items.push({
                                label: createIndicatorLabel('KDJ', 'kdj'),
                                
                                children: (
                                  <Space orientation="vertical" size="small" style={{ width: '100%' }}>
                                    <div>
                                      K={formatValue(indicators.kdj_k, 1)} D={formatValue(indicators.kdj_d, 1)} J={formatValue(indicators.kdj_j, 1)}
                                    </div>
                                    <Space>
                                      {indicators.kdj_j !== undefined && indicators.kdj_j < 20 ? (
                                        <Tag color="success">超卖</Tag>
                                      ) : indicators.kdj_j !== undefined && indicators.kdj_j > 80 ? (
                                        <Tag color="error">超买</Tag>
                                      ) : (
                                        <Tag color="default">中性</Tag>
                                      )}
                                      {indicators.kdj_k !== undefined && indicators.kdj_d !== undefined && indicators.kdj_k > indicators.kdj_d ? (
                                        <Tag color="success">多头</Tag>
                                      ) : (
                                        <Tag color="error">空头</Tag>
                                      )}
                                    </Space>
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.williams_r !== undefined) {
                              items.push({
                                label: createIndicatorLabel('威廉%R', 'williams_r'),
                                
                                children: (
                                  <Space>
                                    <span>{formatValue(indicators.williams_r, 1)}</span>
                                    <Tag
                                      color={
                                        indicators.williams_r < -80 ? 'success' :
                                          indicators.williams_r > -20 ? 'error' : 'default'
                                      }
                                    >
                                      {indicators.williams_r < -80 ? '超卖' :
                                        indicators.williams_r > -20 ? '超买' : '中性'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // CCI顺势指标
                            if (indicators.cci !== undefined) {
                              items.push({
                                label: createIndicatorLabel('CCI', 'cci'),
                                
                                children: (
                                  <Space>
                                    <span style={{ fontSize: 14, fontWeight: 600 }}>{formatValue(indicators.cci, 1)}</span>
                                    <Tag
                                      color={
                                        indicators.cci_signal === 'overbought' ? 'error' :
                                          indicators.cci_signal === 'oversold' ? 'success' : 'default'
                                      }
                                    >
                                      {indicators.cci_signal === 'overbought' ? '超买(>100)' :
                                        indicators.cci_signal === 'oversold' ? '超卖(<-100)' : '中性'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // ADX趋势强度指标
                            if (indicators.adx !== undefined) {
                              items.push({
                                label: createIndicatorLabel('ADX', 'adx'),
                                
                                children: (
                                  <Space orientation="vertical" size="small" style={{ width: '100%' }}>
                                    <div>
                                      <span style={{ fontSize: 14, fontWeight: 600 }}>{formatValue(indicators.adx, 1)}</span>
                                      <Tag
                                        color={
                                          indicators.adx > 40 ? 'success' :
                                            indicators.adx > 25 ? 'default' : 'warning'
                                        }
                                        style={{ marginLeft: 8 }}
                                      >
                                        {indicators.adx > 40 ? '强趋势' :
                                          indicators.adx > 25 ? '中趋势' :
                                            indicators.adx > 20 ? '弱趋势' : '无趋势'}
                                      </Tag>
                                    </div>
                                    {indicators.plus_di !== undefined && indicators.minus_di !== undefined && (
                                      <div>
                                        <span>+DI={formatValue(indicators.plus_di, 1)} -DI={formatValue(indicators.minus_di, 1)}</span>
                                        <Tag color={indicators.plus_di > indicators.minus_di ? 'success' : 'error'} style={{ marginLeft: 8 }}>
                                          {indicators.plus_di > indicators.minus_di ? '多头' : '空头'}
                                        </Tag>
                                      </div>
                                    )}
                                  </Space>
                                ),
                              });
                            }


                            // SAR抛物线转向指标
                            if (indicators.sar !== undefined) {
                              items.push({
                                label: createIndicatorLabel('SAR', 'sar'),
                                
                                children: (
                                  <Space>
                                    <span style={{ fontSize: 14, fontWeight: 600 }}>{formatCurrency(indicators.sar)}</span>
                                    <Tag
                                      color={
                                        indicators.sar_signal === 'bullish' ? 'success' :
                                          indicators.sar_signal === 'bearish' ? 'error' : 'default'
                                      }
                                    >
                                      {indicators.sar_signal === 'bullish' ? '看涨' :
                                        indicators.sar_signal === 'bearish' ? '看跌' : '中性'}
                                    </Tag>
                                    {indicators.sar_distance_pct !== undefined && (
                                      <span style={{ fontSize: 14 }}>
                                        (距离{Math.abs(indicators.sar_distance_pct).toFixed(1)}%)
                                      </span>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            // Ichimoku Cloud
                            if (indicators.ichimoku_tenkan_sen !== undefined) {
                              items.push({
                                label: createIndicatorLabel('一目均衡表', 'ichimoku'),
                                
                                children: (
                                  <Space orientation="vertical" size="small" style={{ width: '100%' }}>
                                    <Space>
                                      <Tag
                                        color={
                                          indicators.ichimoku_status === 'above_cloud' ? 'success' :
                                            indicators.ichimoku_status === 'below_cloud' ? 'error' : 'default'
                                        }
                                      >
                                        {indicators.ichimoku_status === 'above_cloud' ? '云上(看涨)' :
                                          indicators.ichimoku_status === 'below_cloud' ? '云下(看跌)' : '云中(盘整)'}
                                      </Tag>
                                      {indicators.ichimoku_tk_cross === 'bullish' && <Tag color="success">金叉</Tag>}
                                      {indicators.ichimoku_tk_cross === 'bearish' && <Tag color="error">死叉</Tag>}
                                    </Space>
                                    <div style={{ fontSize: 12 }}>
                                    转折: {formatCurrency(indicators.ichimoku_tenkan_sen)} 基准: {formatCurrency(indicators.ichimoku_kijun_sen)}
                                    </div>
                                    <div style={{ fontSize: 12 }}>
                                    云层: {formatCurrency(indicators.ichimoku_cloud_bottom ?? Math.min(indicators.ichimoku_senkou_span_a || 0, indicators.ichimoku_senkou_span_b || 0))} - {formatCurrency(indicators.ichimoku_cloud_top ?? Math.max(indicators.ichimoku_senkou_span_a || 0, indicators.ichimoku_senkou_span_b || 0))}
                                    </div>
                                  </Space>
                                ),
                              });
                            }

                            // SuperTrend
                            if (indicators.supertrend !== undefined) {
                              items.push({
                                label: createIndicatorLabel('SuperTrend', 'supertrend'),
                                
                                children: (
                                  <Space>
                                  <span style={{ fontSize: 16, fontWeight: 600 }}>{formatCurrency(indicators.supertrend)}</span>
                                    <Tag color={indicators.supertrend_direction === 'up' ? 'success' : 'error'}>
                                      {indicators.supertrend_direction === 'up' ? '看涨支撑' : '看跌阻力'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // StochRSI
                            if (indicators.stoch_rsi_k !== undefined) {
                              items.push({
                                label: createIndicatorLabel('StochRSI', 'stoch_rsi'),
                                
                                children: (
                                  <Space>
                                    <span>K: {formatValue(indicators.stoch_rsi_k, 1)}</span>
                                    <span>D: {formatValue(indicators.stoch_rsi_d, 1)}</span>
                                    <Tag
                                      color={
                                        indicators.stoch_rsi_status === 'oversold' ? 'success' :
                                          indicators.stoch_rsi_status === 'overbought' ? 'error' : 'default'
                                      }
                                    >
                                      {indicators.stoch_rsi_status === 'oversold' ? '超卖' :
                                        indicators.stoch_rsi_status === 'overbought' ? '超买' : '中性'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // Volume Profile
                            if (indicators.vp_poc !== undefined) {
                              items.push({
                                label: createIndicatorLabel('筹码分布', 'volume_profile'),
                                
                                children: (
                                  <Space orientation="vertical" size="small">
                                    <Space>
                                      <span>POC: {formatCurrency(indicators.vp_poc)}</span>
                                      <Tag
                                        color={
                                          indicators.vp_status === 'above_va' ? 'success' :
                                            indicators.vp_status === 'below_va' ? 'error' : 'default'
                                        }
                                      >
                                        {indicators.vp_status === 'above_va' ? '上方失衡(看涨)' :
                                          indicators.vp_status === 'below_va' ? '下方失衡(看跌)' : '价值区平衡'}
                                      </Tag>
                                    </Space>
                                    <span style={{ fontSize: 12 }}>
                                      价值区: {formatCurrency(indicators.vp_val)} - {formatCurrency(indicators.vp_vah)}
                                    </span>
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.obv_trend) {
                              items.push({
                                label: createIndicatorLabel('OBV趋势', 'obv'),
                                
                                children: indicators.obv_trend === 'up' ? (
                                  (indicators.price_change_pct ?? 0) > 0 ? (
                                    <Tag color="success">量价齐升</Tag>
                                  ) : (
                                    <Tag color="warning">量价背离(可能见底)</Tag>
                                  )
                                ) : indicators.obv_trend === 'down' ? (
                                  (indicators.price_change_pct ?? 0) < 0 ? (
                                    <Tag color="error">量价齐跌</Tag>
                                  ) : (
                                    <Tag color="warning">量价背离(可能见顶)</Tag>
                                  )
                                ) : (
                                  <Tag color="default">平稳</Tag>
                                ),
                              });
                            }

                            if (indicators.trend_strength !== undefined) {
                              items.push({
                                label: createIndicatorLabel('趋势强度', 'trend_strength'),
                                
                                children: (
                                  <Space>
                                    {getTrendTag(indicators.trend_direction)}
                                    <span style={{ fontSize: 14, fontWeight: 600 }}>
                                      {formatValue(indicators.trend_strength, 0)}%
                                    </span>
                                    {indicators.trend_strength > 50 ? (
                                      <Tag color="success">强</Tag>
                                    ) : indicators.trend_strength > 25 ? (
                                      <Tag color="default">中</Tag>
                                    ) : (
                                      <Tag color="warning">弱</Tag>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            if ((indicators.consecutive_up_days ?? 0) > 0 || (indicators.consecutive_down_days ?? 0) > 0) {
                              items.push({
                                label: '连续涨跌',
                                
                                children: (
                                  <Space>
                                    {(indicators.consecutive_up_days ?? 0) > 0 ? (
                                      <>
                                        <RiseOutlined style={{ color: '#3f8600' }} />
                                        <span>连续{indicators.consecutive_up_days}天上涨</span>
                                        {(indicators.consecutive_up_days ?? 0) >= 5 && (
                                          <Tag color="warning">注意</Tag>
                                        )}
                                      </>
                                    ) : (
                                      <>
                                        <FallOutlined style={{ color: '#cf1322' }} />
                                        <span>连续{indicators.consecutive_down_days}天下跌</span>
                                        {(indicators.consecutive_down_days ?? 0) >= 5 && (
                                          <Tag color="success">关注</Tag>
                                        )}
                                      </>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            return items;
                          })()}
                        />
                      ),
                    }]}
                    style={{ marginTop: 0 }}
                  />






                  {/* 周期分析 - 详细版 */}
                  {(analysisResult.indicators.dominant_cycle !== undefined || analysisResult.indicators.avg_cycle_length !== undefined) && (
                    <div id="section-cycle">
                    <Collapse
                      ghost
                      defaultActiveKey={['cycle']}
                      items={[{
                        key: 'cycle',
                        label: (
                          <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            {createIndicatorLabel('周期分析', 'cycle')}
                            {analysisResult.indicators.cycle_summary && (
                              <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
                                {analysisResult.indicators.cycle_summary}
                              </span>
                            )}
                          </span>
                        ),
                        children: (
                          <div>
                            {(() => {
                              const indicators = analysisResult.indicators;
                              return (
                                <>
                            <Descriptions
                              bordered
                              column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                              size="small"
                              layout="horizontal"
                              items={(() => {
                                const items = [];

                                // 平均周期
                                if (indicators.avg_cycle_length !== undefined) {
                                  items.push({
                                    label: '平均周期',
                                    
                                    children: (
                                      <span style={{ fontSize: 14, fontWeight: 500 }}>
                                        {indicators.avg_cycle_length.toFixed(1)}天
                                      </span>
                                    ),
                                  });
                                }

                                // 周期稳定性评估
                                if (indicators.cycle_stability) {
                                  items.push({
                                    label: '周期稳定性',
                                    
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        <Tag
                                          color={
                                            indicators.cycle_stability === 'high' ? 'success' :
                                              indicators.cycle_stability === 'medium' ? 'default' :
                                                indicators.cycle_stability === 'low' ? 'warning' : 'error'
                                          }
                                          style={{ fontSize: 12 }}
                                        >
                                          {indicators.cycle_stability === 'high' ? '非常稳定' :
                                            indicators.cycle_stability === 'medium' ? '较为稳定' :
                                              indicators.cycle_stability === 'low' ? '不够稳定' : '不稳定'}
                                        </Tag>
                                        {indicators.cycle_stability_desc && (
                                          <span style={{ fontSize: 11, color: '#999' }}>
                                            {indicators.cycle_stability_desc}
                                          </span>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 横盘判断或当前阶段（互斥显示）
                                if (indicators.sideways_market !== undefined) {
                                  if (indicators.sideways_market) {
                                    // 如果是横盘，显示横盘信息
                                    items.push({
                                      label: '市场状态',
                                      
                                      children: (
                                        <Space size="small" direction="vertical" style={{ width: '100%' }}>
                                          <Tag
                                            color="orange"
                                            style={{ fontSize: 12 }}
                                          >
                                            横盘
                                          </Tag>
                                          {indicators.sideways_strength !== undefined && (
                                            <span style={{ fontSize: 11, color: '#999' }}>
                                              强度: {(indicators.sideways_strength * 100).toFixed(0)}%
                                            </span>
                                          )}
                                          {indicators.sideways_amplitude_20 !== undefined && (
                                            <div style={{ fontSize: 11, color: '#666' }}>
                                              20日振幅: {indicators.sideways_amplitude_20.toFixed(2)}%
                                            </div>
                                          )}
                                          {indicators.sideways_price_change_pct !== undefined && (
                                            <div style={{ fontSize: 11, color: '#666' }}>
                                              20日价格变化: {indicators.sideways_price_change_pct.toFixed(2)}%
                                            </div>
                                          )}
                                          {indicators.sideways_price_range_pct !== undefined && (
                                            <div style={{ fontSize: 11, color: '#666' }}>
                                              波动范围: {indicators.sideways_price_range_pct.toFixed(2)}%
                                            </div>
                                          )}
                                          {indicators.sideways_reasons && indicators.sideways_reasons.length > 0 && (
                                            <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                                              <div style={{ fontWeight: 500, marginBottom: 4 }}>判断依据:</div>
                                              {indicators.sideways_reasons.map((reason, idx) => (
                                                <div key={idx} style={{ marginLeft: 8 }}>• {reason}</div>
                                              ))}
                                            </div>
                                          )}
                                        </Space>
                                      ),
                                    });
                                  } else if (indicators.cycle_phase) {
                                    // 如果不是横盘，显示上涨或下跌阶段
                                    items.push({
                                      label: '市场状态',
                                      
                                      children: (
                                        <Space size="small" orientation="vertical">
                                          <Tag
                                            color={
                                              indicators.cycle_phase === 'early_rise' ? 'success' :
                                                indicators.cycle_phase === 'mid_rise' ? 'default' :
                                                  indicators.cycle_phase === 'late_rise' ? 'warning' : 'error'
                                            }
                                            style={{ fontSize: 12 }}
                                          >
                                            {indicators.cycle_phase === 'early_rise' ? '早期上涨' :
                                              indicators.cycle_phase === 'mid_rise' ? '中期上涨' :
                                                indicators.cycle_phase === 'late_rise' ? '后期上涨' : '下跌'}
                                          </Tag>
                                          {indicators.cycle_phase_desc && (
                                            <span style={{ fontSize: 11, color: '#999' }}>
                                              {indicators.cycle_phase_desc}
                                            </span>
                                          )}
                                          {indicators.cycle_position !== undefined && (
                                            <div style={{ fontSize: 11, color: '#999' }}>
                                              周期进度: {(indicators.cycle_position * 100).toFixed(0)}%
                                              {indicators.days_from_last_trough !== undefined && (
                                                <span style={{ marginLeft: 4 }}>
                                                  (距低点{indicators.days_from_last_trough}天)
                                                </span>
                                              )}
                                            </div>
                                          )}
                                          {indicators.cycle_suggestion && (
                                            <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                                              {indicators.cycle_suggestion}
                                            </div>
                                          )}
                                        </Space>
                                      ),
                                    });
                                  }
                                } else if (indicators.cycle_phase) {
                                  // 如果没有横盘判断但有阶段信息，也显示阶段
                                  items.push({
                                    label: '市场状态',
                                    
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        <Tag
                                          color={
                                            indicators.cycle_phase === 'early_rise' ? 'success' :
                                              indicators.cycle_phase === 'mid_rise' ? 'default' :
                                                indicators.cycle_phase === 'late_rise' ? 'warning' : 'error'
                                          }
                                          style={{ fontSize: 12 }}
                                        >
                                          {indicators.cycle_phase === 'early_rise' ? '早期上涨' :
                                            indicators.cycle_phase === 'mid_rise' ? '中期上涨' :
                                              indicators.cycle_phase === 'late_rise' ? '后期上涨' : '下跌'}
                                        </Tag>
                                        {indicators.cycle_phase_desc && (
                                          <span style={{ fontSize: 11, color: '#999' }}>
                                            {indicators.cycle_phase_desc}
                                          </span>
                                        )}
                                        {indicators.cycle_position !== undefined && (
                                          <div style={{ fontSize: 11, color: '#999' }}>
                                            周期进度: {(indicators.cycle_position * 100).toFixed(0)}%
                                            {indicators.days_from_last_trough !== undefined && (
                                              <span style={{ marginLeft: 4 }}>
                                                (距低点{indicators.days_from_last_trough}天)
                                              </span>
                                            )}
                                          </div>
                                        )}
                                        {indicators.cycle_suggestion && (
                                          <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                                            {indicators.cycle_suggestion}
                                          </div>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 多周期检测
                                if (indicators.short_cycles || indicators.medium_cycles || indicators.long_cycles) {
                                  items.push({
                                    label: '多周期检测',
                                    span: 3,
                                    children: (
                                      <Space orientation="vertical" size="small" style={{ width: '100%' }}>
                                        {indicators.short_cycles && indicators.short_cycles.length > 0 && (
                                          <div>
                                            <span style={{ fontSize: 13, fontWeight: 500 }}>短周期: </span>
                                            {indicators.short_cycles.map((cycle, idx) => (
                                              <Tag key={idx} style={{ marginRight: 4 }}>
                                                {cycle}天
                                              </Tag>
                                            ))}
                                            {indicators.short_cycle_strength !== undefined && (
                                              <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                                                强度: {(indicators.short_cycle_strength * 100).toFixed(0)}%
                                              </span>
                                            )}
                                          </div>
                                        )}
                                        {indicators.medium_cycles && indicators.medium_cycles.length > 0 && (
                                          <div>
                                            <span style={{ fontSize: 13, fontWeight: 500 }}>中周期: </span>
                                            {indicators.medium_cycles.map((cycle, idx) => (
                                              <Tag key={idx} color="blue" style={{ marginRight: 4 }}>
                                                {cycle}天
                                              </Tag>
                                            ))}
                                            {indicators.medium_cycle_strength !== undefined && (
                                              <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                                                强度: {(indicators.medium_cycle_strength * 100).toFixed(0)}%
                                              </span>
                                            )}
                                          </div>
                                        )}
                                        {indicators.long_cycles && indicators.long_cycles.length > 0 && (
                                          <div>
                                            <span style={{ fontSize: 13, fontWeight: 500 }}>长周期: </span>
                                            {indicators.long_cycles.map((cycle, idx) => (
                                              <Tag key={idx} color="purple" style={{ marginRight: 4 }}>
                                                {cycle}天
                                              </Tag>
                                            ))}
                                            {indicators.long_cycle_strength !== undefined && (
                                              <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                                                强度: {(indicators.long_cycle_strength * 100).toFixed(0)}%
                                              </span>
                                            )}
                                          </div>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 周期振幅
                                if (indicators.avg_cycle_amplitude !== undefined) {
                                  items.push({
                                    label: '周期振幅',
                                    
                                    children: (
                                      <Space orientation="vertical" size="small">
                                        <span style={{ fontSize: 14, fontWeight: 500 }}>
                                          平均: {indicators.avg_cycle_amplitude.toFixed(2)}%
                                        </span>
                                        {indicators.max_cycle_amplitude !== undefined && indicators.min_cycle_amplitude !== undefined && (
                                          <span style={{ fontSize: 12, color: '#999' }}>
                                            范围: {indicators.min_cycle_amplitude.toFixed(2)}% - {indicators.max_cycle_amplitude.toFixed(2)}%
                                          </span>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 统计信息
                                if (indicators.peak_count !== undefined || indicators.trough_count !== undefined) {
                                  items.push({
                                    label: '统计信息',
                                    
                                    children: (
                                      <Space orientation="vertical" size="small">
                                        <span style={{ fontSize: 13 }}>
                                          高点: <strong>{indicators.peak_count || 0}</strong>个
                                        </span>
                                        <span style={{ fontSize: 13 }}>
                                          低点: <strong>{indicators.trough_count || 0}</strong>个
                                        </span>
                                        {indicators.avg_peak_period !== undefined && (
                                          <span style={{ fontSize: 12, color: '#999' }}>
                                            高点平均周期: {indicators.avg_peak_period.toFixed(1)}天
                                          </span>
                                        )}
                                        {indicators.avg_trough_period !== undefined && (
                                          <span style={{ fontSize: 12, color: '#999' }}>
                                            低点平均周期: {indicators.avg_trough_period.toFixed(1)}天
                                          </span>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                return items;
                              })()}
                            />
                            
                            {/* 周期时间段表格 */}
                            {indicators.cycle_periods && indicators.cycle_periods.length > 0 ? (
                              <div style={{ marginTop: 16 }}>
                                <Tabs
                                  defaultActiveKey="cycle-periods"
                                  items={[
                                    {
                                      key: 'cycle-periods',
                                      label: `周期时间段 (${indicators.cycle_periods.length})`,
                                      children: (
                                        <div style={{ overflowX: 'auto', width: '100%' }}>
                                          <Table
                                            dataSource={indicators.cycle_periods.slice().reverse()}
                                            columns={[
                                    {
                                      title: '周期类型',
                                      key: 'cycle_type',
                                        width: 100,
                                        fixed: 'left' as const,
                                      align: 'center' as const,
                                      render: (_: any, record: any) => {
                                        const isRise = record.cycle_type === 'rise';
                                        const isSideways = record.cycle_type === 'sideways';
                                        const isDecline = record.cycle_type === 'decline';
                                        
                                        let tagColor = 'default';
                                        if (isRise) tagColor = 'success';
                                        else if (isDecline) tagColor = 'error';
                                        else if (isSideways) tagColor = 'warning';
                                        
                                        return (
                                          <Tag
                                            color={tagColor}
                                            style={{ fontSize: 12, fontWeight: 500 }}
                                          >
                                            {record.cycle_type_desc || (isRise ? '上涨' : isDecline ? '下跌' : '横盘')}
                                          </Tag>
                                        );
                                      },
                                    },
                                    {
                                      title: '起始日期',
                                      key: 'start_time',
                                      width: 120,
                                      render: (_: any, record: any) => {
                                        const timeStr = record.start_time;
                                        if (timeStr) {
                                          return timeStr.split('T')[0].split(' ')[0];
                                        }
                                        if (analysisResult.candles && record.start_index < analysisResult.candles.length) {
                                          const candle = analysisResult.candles[record.start_index];
                                          if (candle && candle.time) {
                                            return candle.time.split('T')[0].split(' ')[0];
                                          }
                                        }
                                        return '-';
                                      },
                                    },
                                    {
                                      title: '起始价格',
                                      key: 'start_price',
                                      width: 120,
                                      render: (_: any, record: any) => {
                                        const isRise = record.cycle_type === 'rise';
                                        const isSideways = record.cycle_type === 'sideways';
                                        const isDecline = record.cycle_type === 'decline';
                                        
                                        // 横盘周期：根据振幅方向判断起始价格
                                        // 振幅为正：从低点到高点，起始价格是低点
                                        // 振幅为负：从高点到低点，起始价格是高点
                                        let startPrice;
                                        if (isSideways) {
                                          const amplitude = record.amplitude || 0;
                                          startPrice = amplitude >= 0 ? record.low_price : record.high_price;
                                        } else if (isRise) {
                                          startPrice = record.low_price;
                                        } else {
                                          startPrice = record.high_price;
                                        }
                                        
                                        let color = isRise ? '#3f8600' : isDecline ? '#cf1322' : '#faad14';
                                        return (
                                          <span style={{ 
                                            fontWeight: 500, 
                                            color: color
                                          }}>
                                            {formatCurrency(startPrice)}
                                          </span>
                                        );
                                      },
                                    },
                                    {
                                      title: '结束日期',
                                      key: 'end_time',
                                      width: 120,
                                      render: (_: any, record: any) => {
                                        const timeStr = record.end_time;
                                        if (timeStr) {
                                          return timeStr.split('T')[0].split(' ')[0];
                                        }
                                        if (analysisResult.candles && record.end_index < analysisResult.candles.length) {
                                          const candle = analysisResult.candles[record.end_index];
                                          if (candle && candle.time) {
                                            return candle.time.split('T')[0].split(' ')[0];
                                          }
                                        }
                                        return '-';
                                      },
                                    },
                                    {
                                      title: '结束价格',
                                      key: 'end_price',
                                      width: 120,
                                      render: (_: any, record: any) => {
                                        const isRise = record.cycle_type === 'rise';
                                        const isSideways = record.cycle_type === 'sideways';
                                        const isDecline = record.cycle_type === 'decline';
                                        
                                        // 横盘周期：根据振幅方向判断结束价格
                                        // 振幅为正：从低点到高点，结束价格是高点
                                        // 振幅为负：从高点到低点，结束价格是低点
                                        let endPrice;
                                        if (isSideways) {
                                          const amplitude = record.amplitude || 0;
                                          endPrice = amplitude >= 0 ? record.high_price : record.low_price;
                                        } else if (isRise) {
                                          endPrice = record.high_price;
                                        } else {
                                          endPrice = record.low_price;
                                        }
                                        
                                        const color = isRise ? '#cf1322' : isDecline ? '#3f8600' : '#faad14';
                                        return (
                                          <span style={{ 
                                            fontWeight: 500, 
                                            color: color
                                          }}>
                                            {formatCurrency(endPrice)}
                                          </span>
                                        );
                                      },
                                    },
                                    {
                                      title: '持续天数',
                                      dataIndex: 'duration',
                                      key: 'duration',
                                      width: 80,
                                      align: 'center' as const,
                                      render: (val: number) => `${val}天`,
                                    },
                                    {
                                      title: '振幅',
                                      key: 'amplitude',
                                      width: 100,
                                      align: 'right' as const,
                                      render: (_: any, record: any) => {
                                        const isRise = record.cycle_type === 'rise';
                                        const isSideways = record.cycle_type === 'sideways';
                                        const isDecline = record.cycle_type === 'decline';
                                        // 使用记录中的振幅，如果没有则计算
                                        let amplitude = record.amplitude;
                                        if (amplitude === undefined) {
                                          const startPrice = isRise ? record.low_price : isDecline ? record.high_price : (record.low_price || record.high_price);
                                          const endPrice = isRise ? record.high_price : isDecline ? record.low_price : (record.high_price || record.low_price);
                                          amplitude = ((endPrice - startPrice) / startPrice) * 100;
                                        }
                                        // 横盘周期振幅也保持正负方向，不取绝对值
                                        // 上涨周期振幅为正数，下跌周期振幅为负数
                                        let color = '#faad14'; // 默认横盘颜色
                                        if (!isSideways) {
                                          color = amplitude >= 0 ? '#cf1322' : '#3f8600';
                                        } else {
                                          // 横盘周期根据振幅方向选择颜色
                                          color = amplitude >= 0 ? '#faad14' : '#fa8c16'; // 正数用橙色，负数用深橙色
                                        }
                                        return (
                                          <span style={{ 
                                            fontSize: 12, 
                                            color: color
                                          }}>
                                            {amplitude >= 0 ? '+' : ''}{amplitude.toFixed(2)}%
                                          </span>
                                        );
                                      },
                                    },
                                  ]}
                                  pagination={{
                                    current: cyclePeriodCurrent,
                                    pageSize: cyclePeriodPageSize,
                                    showSizeChanger: true,
                                    showQuickJumper: true,
                                    showTotal: (total) => `共 ${total} 个周期`,
                                    pageSizeOptions: ['10', '20', '30', '50'],
                                    onChange: (page, pageSize) => {
                                      setCyclePeriodCurrent(page);
                                      setCyclePeriodPageSize(pageSize);
                                    },
                                    onShowSizeChange: (_current, size) => {
                                      setCyclePeriodCurrent(1); // 切换每页数量时重置到第一页
                                      setCyclePeriodPageSize(size);
                                    },
                                    locale: {
                                      items_per_page: '条/页',
                                      jump_to: '跳至',
                                      page: '页',
                                    },
                                  }}
                                  size="small"
                                  style={{ fontSize: 12 }}
                                  scroll={{ x: 'max-content' }}
                                  rowKey={(record) => `period-${record.period_index || record.id || Math.random().toString()}`}
                                            />
                                          </div>
                                        ),
                                    },
                                    indicators.yearly_cycles && indicators.yearly_cycles.length > 0 ? {
                                      key: 'yearly-cycles',
                                      label: `年周期 (${indicators.yearly_cycles.length})`,
                                      children: (
                                        <div style={{ overflowX: 'auto', width: '100%' }}>
                                          <Table
                                            dataSource={indicators.yearly_cycles.slice().reverse()}
                                            columns={[
                                              {
                                                title: '年份',
                                                dataIndex: 'year',
                                                key: 'year',
                                                width: 80,
                                                fixed: 'left' as const,
                                                align: 'center' as const,
                                                render: (year: number) => `${year}年`,
                                              },
                                              {
                                                title: '第一天',
                                                key: 'first_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.first_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '第一天收盘价',
                                                key: 'first_close',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => formatCurrency(record.first_close),
                                              },
                                              {
                                                title: '最后一天',
                                                key: 'last_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.last_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '最后一天收盘价',
                                                key: 'last_close',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => formatCurrency(record.last_close),
                                              },
                                              {
                                                title: '周期涨幅',
                                                key: 'first_to_last_change',
                                                width: 150,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => {
                                                  const change = record.first_to_last_change || 0;
                                                  const color = change >= 0 ? '#cf1322' : '#3f8600';
                                                  return (
                                                    <span style={{ color, fontWeight: 500 }}>
                                                      {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                                                    </span>
                                                  );
                                                },
                                              },
                                              {
                                                title: '最低价',
                                                key: 'min_low',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => record.min_low ? formatCurrency(record.min_low) : '-',
                                              },
                                              {
                                                title: '最低价日期',
                                                key: 'min_low_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.min_low_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '最高价',
                                                key: 'max_high',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => record.max_high ? formatCurrency(record.max_high) : '-',
                                              },
                                              {
                                                title: '最高价日期',
                                                key: 'max_high_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.max_high_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '最低到最高涨幅',
                                                key: 'low_to_high_change',
                                                width: 150,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => {
                                                  const change = record.low_to_high_change || 0;
                                                  const color = '#cf1322';
                                                  return (
                                                    <span style={{ color, fontWeight: 500 }}>
                                                      {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                                                    </span>
                                                  );
                                                },
                                              },
                                              {
                                                title: '交易日数',
                                                dataIndex: 'trading_days',
                                                key: 'trading_days',
                                                width: 100,
                                                align: 'center' as const,
                                                render: (days: number) => `${days}天`,
                                              },
                                            ]}
                                            pagination={{
                                              current: yearlyCycleCurrent,
                                              pageSize: yearlyCyclePageSize,
                                              showSizeChanger: true,
                                              showQuickJumper: true,
                                              showTotal: (total) => `共 ${total} 个年度`,
                                              pageSizeOptions: ['10', '20', '30', '50'],
                                              onChange: (page, pageSize) => {
                                                setYearlyCycleCurrent(page);
                                                setYearlyCyclePageSize(pageSize);
                                              },
                                              onShowSizeChange: (_current, size) => {
                                                setYearlyCycleCurrent(1);
                                                setYearlyCyclePageSize(size);
                                              },
                                              locale: {
                                                items_per_page: '条/页',
                                                jump_to: '跳至',
                                                page: '页',
                                              },
                                            }}
                                            size="small"
                                            style={{ fontSize: 12 }}
                                            scroll={{ x: 'max-content' }}
                                            rowKey={(record) => `yearly-${record.year}`}
                                          />
                                        </div>
                                      ),
                                    } : null,
                                    indicators.monthly_cycles && indicators.monthly_cycles.length > 0 ? {
                                      key: 'monthly-cycles',
                                      label: `月周期 (${indicators.monthly_cycles.length})`,
                                      children: (
                                        <div style={{ overflowX: 'auto', width: '100%' }}>
                                          <Table
                                            dataSource={indicators.monthly_cycles.slice().reverse()}
                                            columns={[
                                              {
                                                title: '月份',
                                                key: 'year_month',
                                                width: 100,
                                                fixed: 'left' as const,
                                                align: 'center' as const,
                                                render: (_: any, record: any) => `${record.year}年${record.month}月`,
                                              },
                                              {
                                                title: '第一天',
                                                key: 'first_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.first_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '第一天收盘价',
                                                key: 'first_close',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => formatCurrency(record.first_close),
                                              },
                                              {
                                                title: '最后一天',
                                                key: 'last_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.last_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '最后一天收盘价',
                                                key: 'last_close',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => formatCurrency(record.last_close),
                                              },
                                              {
                                                title: '周期涨幅',
                                                key: 'first_to_last_change',
                                                width: 150,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => {
                                                  const change = record.first_to_last_change || 0;
                                                  const color = change >= 0 ? '#cf1322' : '#3f8600';
                                                  return (
                                                    <span style={{ color, fontWeight: 500 }}>
                                                      {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                                                    </span>
                                                  );
                                                },
                                              },
                                              {
                                                title: '最低价',
                                                key: 'min_low',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => record.min_low ? formatCurrency(record.min_low) : '-',
                                              },
                                              {
                                                title: '最低价日期',
                                                key: 'min_low_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.min_low_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '最高价',
                                                key: 'max_high',
                                                width: 120,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => record.max_high ? formatCurrency(record.max_high) : '-',
                                              },
                                              {
                                                title: '最高价日期',
                                                key: 'max_high_date',
                                                width: 120,
                                                render: (_: any, record: any) => {
                                                  const dateStr = record.max_high_date;
                                                  if (dateStr) {
                                                    return dateStr.split('T')[0].split(' ')[0];
                                                  }
                                                  return '-';
                                                },
                                              },
                                              {
                                                title: '最低到最高涨幅',
                                                key: 'low_to_high_change',
                                                width: 150,
                                                align: 'right' as const,
                                                render: (_: any, record: any) => {
                                                  const change = record.low_to_high_change || 0;
                                                  const color = '#cf1322';
                                                  return (
                                                    <span style={{ color, fontWeight: 500 }}>
                                                      {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                                                    </span>
                                                  );
                                                },
                                              },
                                              {
                                                title: '交易日数',
                                                dataIndex: 'trading_days',
                                                key: 'trading_days',
                                                width: 100,
                                                align: 'center' as const,
                                                render: (days: number) => `${days}天`,
                                              },
                                            ]}
                                            pagination={{
                                              current: monthlyCycleCurrent,
                                              pageSize: monthlyCyclePageSize,
                                              showSizeChanger: true,
                                              showQuickJumper: true,
                                              showTotal: (total) => `共 ${total} 个月度`,
                                              pageSizeOptions: ['10', '20', '30', '50'],
                                              onChange: (page, pageSize) => {
                                                setMonthlyCycleCurrent(page);
                                                setMonthlyCyclePageSize(pageSize);
                                              },
                                              onShowSizeChange: (_current, size) => {
                                                setMonthlyCycleCurrent(1);
                                                setMonthlyCyclePageSize(size);
                                              },
                                              locale: {
                                                items_per_page: '条/页',
                                                jump_to: '跳至',
                                                page: '页',
                                              },
                                            }}
                                            size="small"
                                            style={{ fontSize: 12 }}
                                            scroll={{ x: 'max-content' }}
                                            rowKey={(record) => `monthly-${record.year}-${record.month}`}
                                          />
                                        </div>
                                      ),
                                    } : null,
                                  ].filter((item): item is NonNullable<typeof item> => item !== null)}
                                />
                              </div>
                            ) : null}
                                </>
                              );
                            })()}
                          </div>
                        ),
                      }]}
                      style={{ marginTop: 0 }}
                    />
                    </div>
                  )}

                  {/* 机构操作分析 */}
                  {analysisResult.indicators.activity_score !== undefined && (
                    <div id="section-institutional">
                    <Collapse
                      ghost
                      defaultActiveKey={['institutional']}
                      items={[{
                        key: 'institutional',
                        label: (
                          <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            {createIndicatorLabel('机构操作分析', 'institutional_activity')}
                            {analysisResult.indicators.activity_level_desc && (
                              <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
                                {analysisResult.indicators.activity_level_desc}
                              </span>
                            )}
                          </span>
                        ),
                        children: (
                          <div>
                            {(() => {
                              const indicators = analysisResult.indicators;
                              return (
                                <>
                            <Descriptions
                              bordered
                              column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                              size="small"
                              layout="horizontal"
                              items={(() => {
                                const items = [];

                                // 机构操作强度
                                if (indicators.activity_score !== undefined) {
                                  items.push({
                                    label: '操作强度',
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        <div>
                                          <span style={{ fontSize: 14, fontWeight: 500 }}>
                                            {indicators.activity_score.toFixed(0)}分
                                          </span>
                                          <Tag
                                            color={
                                              indicators.activity_score >= 60 ? 'error' :
                                                indicators.activity_score >= 40 ? 'warning' :
                                                  indicators.activity_score >= 20 ? 'default' : 'success'
                                            }
                                            style={{ marginLeft: 8, fontSize: 12 }}
                                          >
                                            {indicators.activity_level === 'high' ? '明显' :
                                              indicators.activity_level === 'medium' ? '中等' :
                                                indicators.activity_level === 'low' ? '较弱' : '无'}
                                          </Tag>
                                        </div>
                                        {indicators.suggestion && (
                                          <span style={{ fontSize: 11, color: '#666' }}>
                                            {indicators.suggestion}
                                          </span>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 成交量异常
                                if (indicators.volume_ratio_20 !== undefined) {
                                  items.push({
                                    label: '成交量比率',
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        <span style={{ fontSize: 14, fontWeight: 500 }}>
                                          {indicators.volume_ratio_20.toFixed(2)}倍
                                        </span>
                                        {indicators.is_volume_surge && (
                                          <Tag color="error" style={{ fontSize: 12 }}>
                                            异常放量（强烈）
                                          </Tag>
                                        )}
                                        {indicators.is_volume_spike && !indicators.is_volume_surge && (
                                          <Tag color="warning" style={{ fontSize: 12 }}>
                                            放量
                                          </Tag>
                                        )}
                                        {indicators.is_volume_shrink && (
                                          <Tag color="default" style={{ fontSize: 12 }}>
                                            缩量
                                          </Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 量价关系
                                if (indicators.price_change_5d !== undefined && indicators.volume_change_5d !== undefined) {
                                  items.push({
                                    label: '量价关系',
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        <span style={{ fontSize: 13 }}>
                                          5日价格: {indicators.price_change_5d >= 0 ? '+' : ''}{indicators.price_change_5d.toFixed(2)}%
                                        </span>
                                        <span style={{ fontSize: 13 }}>
                                          5日成交量: {indicators.volume_change_5d >= 0 ? '+' : ''}{indicators.volume_change_5d.toFixed(2)}%
                                        </span>
                                        {indicators.price_volume_rising && (
                                          <Tag color="success" style={{ fontSize: 12 }}>
                                            价涨量增（建仓信号）
                                          </Tag>
                                        )}
                                        {indicators.price_volume_falling && (
                                          <Tag color="error" style={{ fontSize: 12 }}>
                                            价跌量增（出货信号）
                                          </Tag>
                                        )}
                                        {indicators.price_rising_volume_shrinking && (
                                          <Tag color="warning" style={{ fontSize: 12 }}>
                                            价涨量缩（控盘）
                                          </Tag>
                                        )}
                                        {indicators.price_falling_volume_shrinking && (
                                          <Tag color="default" style={{ fontSize: 12 }}>
                                            价跌量缩（洗盘）
                                          </Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 资金流向
                                if (indicators.fund_flow) {
                                  items.push({
                                    label: '资金流向',
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        <Tag
                                          color={
                                            indicators.fund_flow === 'inflow' ? 'success' :
                                              indicators.fund_flow === 'outflow' ? 'error' : 'default'
                                          }
                                          style={{ fontSize: 12 }}
                                        >
                                          {indicators.fund_flow_desc || 
                                            (indicators.fund_flow === 'inflow' ? '资金流入' :
                                              indicators.fund_flow === 'outflow' ? '资金流出' : '资金平衡')}
                                        </Tag>
                                      </Space>
                                    ),
                                  });
                                }

                                // 持仓成本
                                if (indicators.cost_position) {
                                  items.push({
                                    label: '持仓成本',
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        {indicators.vwap && (
                                          <span style={{ fontSize: 13 }}>
                                            VWAP: {formatCurrency(indicators.vwap)}
                                          </span>
                                        )}
                                        {indicators.vwap_deviation !== undefined && (
                                          <span style={{ fontSize: 13 }}>
                                            偏离: {indicators.vwap_deviation >= 0 ? '+' : ''}{indicators.vwap_deviation.toFixed(2)}%
                                          </span>
                                        )}
                                        <Tag
                                          color={
                                            indicators.cost_position === 'below_cost' ? 'success' :
                                              indicators.cost_position === 'above_cost' ? 'error' : 'default'
                                          }
                                          style={{ fontSize: 12 }}
                                        >
                                          {indicators.cost_position_desc || 
                                            (indicators.cost_position === 'below_cost' ? '低于机构成本' :
                                              indicators.cost_position === 'above_cost' ? '高于机构成本' : '接近机构成本')}
                                        </Tag>
                                      </Space>
                                    ),
                                  });
                                }

                                // 筹码集中度
                                if (indicators.chip_concentration) {
                                  items.push({
                                    label: '筹码集中度',
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        {indicators.vp_poc && (
                                          <span style={{ fontSize: 13 }}>
                                            POC: {formatCurrency(indicators.vp_poc)}
                                          </span>
                                        )}
                                        {indicators.poc_deviation !== undefined && (
                                          <span style={{ fontSize: 13 }}>
                                            偏离: {indicators.poc_deviation >= 0 ? '+' : ''}{indicators.poc_deviation.toFixed(2)}%
                                          </span>
                                        )}
                                        <Tag
                                          color={
                                            indicators.chip_concentration === 'high' ? 'success' :
                                              indicators.chip_concentration === 'low' ? 'error' : 'default'
                                          }
                                          style={{ fontSize: 12 }}
                                        >
                                          {indicators.chip_concentration_desc || 
                                            (indicators.chip_concentration === 'high' ? '高度集中' :
                                              indicators.chip_concentration === 'medium' ? '中等集中' : '分散')}
                                        </Tag>
                                      </Space>
                                    ),
                                  });
                                }

                                // 价格行为模式
                                if (indicators.price_pattern) {
                                  items.push({
                                    label: '价格模式',
                                    children: (
                                      <Space size="small" orientation="vertical">
                                        <Tag
                                          color={
                                            indicators.price_pattern === 'accumulation' ? 'success' :
                                              indicators.price_pattern === 'distribution' ? 'error' :
                                                indicators.price_pattern === 'controlled_rise' ? 'warning' : 'default'
                                          }
                                          style={{ fontSize: 12 }}
                                        >
                                          {indicators.price_pattern_desc || 
                                            (indicators.price_pattern === 'accumulation' ? '建仓模式' :
                                              indicators.price_pattern === 'distribution' ? '出货模式' :
                                                indicators.price_pattern === 'consolidation' ? '洗盘模式' :
                                                  indicators.price_pattern === 'controlled_rise' ? '控盘拉升' : '正常波动')}
                                        </Tag>
                                      </Space>
                                    ),
                                  });
                                }

                                // 操作信号
                                if (indicators.activity_signals && indicators.activity_signals.length > 0) {
                                  items.push({
                                    label: '操作信号',
                                    span: 2,
                                    children: (
                                      <Space size="small" wrap>
                                        {indicators.activity_signals.map((signal, index) => (
                                          <Tag key={index} color="blue" style={{ fontSize: 12 }}>
                                            {signal}
                                          </Tag>
                                        ))}
                                      </Space>
                                    ),
                                  });
                                }

                                return items;
                              })()}
                            />
                                </>
                              );
                            })()}
                          </div>
                        ),
                      }]}
                      style={{ marginTop: 0 }}
                    />
                    </div>
                  )}

                  {/* 关键价位 */}
                  {(analysisResult.indicators.pivot || analysisResult.indicators.pivot_r1 || analysisResult.indicators.resistance_20d_high) && (
                    <div id="section-pivot">
                    <Collapse
                      ghost
                      defaultActiveKey={['pivot']}
                      items={[{
                        key: 'pivot',
                        label: (
                          <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            关键价位
                          </span>
                        ),
                        children: (
                          <Descriptions
                            bordered
                            column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                            size="small"
                            layout="vertical"
                            items={(() => {
                              const items = [];
                              const indicators = analysisResult.indicators;

                              if (indicators.pivot) {
                                items.push({
                                  label: createIndicatorLabel('枢轴点', 'pivot'),
                                  children: (
                                    <span style={{ fontSize: 14, fontWeight: 600 }}>
                                      {formatCurrency(indicators.pivot)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_r1) {
                                items.push({
                                  label: createIndicatorLabel('压力位R1', 'pivot_r1'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      {formatCurrency(indicators.pivot_r1)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_r2) {
                                items.push({
                                  label: createIndicatorLabel('压力位R2', 'pivot_r2'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      {formatCurrency(indicators.pivot_r2)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_r3) {
                                items.push({
                                  label: createIndicatorLabel('压力位R3', 'pivot_r3'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      {formatCurrency(indicators.pivot_r3)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_s1) {
                                items.push({
                                  label: createIndicatorLabel('支撑位S1', 'pivot_s1'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                      {formatCurrency(indicators.pivot_s1)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_s2) {
                                items.push({
                                  label: createIndicatorLabel('支撑位S2', 'pivot_s2'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                      {formatCurrency(indicators.pivot_s2)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_s3) {
                                items.push({
                                  label: createIndicatorLabel('支撑位S3', 'pivot_s3'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                      {formatCurrency(indicators.pivot_s3)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.resistance_20d_high) {
                                items.push({
                                  label: createIndicatorLabel('20日高点', 'resistance_20d_high'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      {formatCurrency(indicators.resistance_20d_high)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.support_20d_low) {
                                items.push({
                                  label: createIndicatorLabel('20日低点', 'support_20d_low'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                      {formatCurrency(indicators.support_20d_low)}
                                    </span>
                                  ),
                                });
                              }

                              return items;
                            })()}
                          />
                        ),
                      }]}
                      style={{ marginTop: 0 }}
                    />
                    </div>
                  )}

                  {/* 交易信号 */}
                  {analysisResult.signals && (
                    <Collapse
                      ghost
                      defaultActiveKey={['signals']}
                      items={[{
                        key: 'signals',
                        label: (
                          <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            交易信号
                          </span>
                        ),
                        children: (
                          <Descriptions
                            bordered
                            column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }}
                            size="small"
                            layout="vertical"
                            items={(() => {
                              const items = [];
                              const signals = analysisResult.signals;
                              const indicators = analysisResult.indicators;

                              if (signals.risk) {
                                const riskLevel = String(signals.risk.level || 'unknown');
                                const config = statusMaps.risk[riskLevel as keyof typeof statusMaps.risk] || 
                                  { color: 'default', text: '未知' };
                                items.push({
                                  label: '风险等级',
                                  
                                  children: <Tag color={config.color}>{config.text}</Tag>,
                                });
                              }

                              if (signals.stop_loss) {
                                items.push({
                                  label: '建议止损',
                                  
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#cf1322' }}>
                                      {formatCurrency(signals.stop_loss)}
                                    </span>
                                  ),
                                });
                              }

                              if (signals.take_profit) {
                                items.push({
                                  label: '建议止盈',
                                  
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#3f8600' }}>
                                      {formatCurrency(signals.take_profit)}
                                    </span>
                                  ),
                                });
                              }

                              if (signals.stop_loss && signals.take_profit && indicators.current_price && indicators.current_price > 0) {
                                const currentPrice = indicators.current_price;
                                items.push({
                                  label: '风险回报比',
                                  span: 3,
                                  children: (
                                    <Tag color="blue" style={{ fontSize: 14 }}>
                                      1:{formatValue(
                                        Math.abs(
                                          ((signals.take_profit - currentPrice) / currentPrice) /
                                          ((signals.stop_loss - currentPrice) / currentPrice)
                                        ), 1
                                      )}
                                    </Tag>
                                  ),
                                });
                              }

                              if (signals.signals && signals.signals.length > 0) {
                                items.push({
                                  label: '信号列表',
                                  span: 3,
                                  children: (
                                    <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                                      {signals.signals.map((signal: string, index: number) => (
                                        <li key={index} style={{ marginBottom: 4, fontSize: 14 }}>
                                          {renderSignalWithIcon(signal)}
                                        </li>
                                      ))}
                                    </ul>
                                  ),
                                });
                              }

                              return items;
                            })()}
                          />
                        ),
                      }]}
                      style={{ marginTop: 0 }}
                    />
                  )}

                  {/* 基本面数据 */}
                  {analysisResult.indicators.fundamental_data &&
                    typeof analysisResult.indicators.fundamental_data === 'object' &&
                    !analysisResult.indicators.fundamental_data.raw_xml &&
                    Object.keys(analysisResult.indicators.fundamental_data).length > 0 && (
                      <Collapse
                        ghost
                        defaultActiveKey={[]}
                        items={[{
                          key: 'fundamental',
                          label: (
                            <span>
                              <DatabaseOutlined style={{ marginRight: 8 }} />
                              <span>基本面数据</span>
                            </span>
                          ),
                          children: (
                            <Descriptions
                              bordered
                              column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                              size="small"
                              layout="vertical"
                              items={(() => {
                                const items = [];
                                const fd = analysisResult.indicators.fundamental_data;

                                // 基本信息
                                if (fd.CompanyName) {
                                  items.push({
                                    label: createIndicatorLabel('公司名称', 'fundamental'),
                                    span: 2,
                                    children: fd.CompanyName,
                                  });
                                }

                                if (fd.Exchange) {
                                  items.push({
                                    label: createIndicatorLabel('交易所', 'fundamental'),
                                    
                                    children: fd.Exchange,
                                  });
                                }

                                if (fd.Employees) {
                                  items.push({
                                    label: createIndicatorLabel('员工数', 'fundamental'),
                                    
                                    children: `${String(fd.Employees)}人`,
                                  });
                                }

                                if (fd.SharesOutstanding) {
                                  const shares = parseFloat(String(fd.SharesOutstanding));
                                  items.push({
                                    label: createIndicatorLabel('流通股数', 'fundamental'),
                                    
                                    children: formatLargeNumber(shares, ''),
                                  });
                                }

                                if (fd.MarketCap) {
                                  items.push({
                                    label: createIndicatorLabel('市值', 'market_cap'),
                                    
                                    children: formatLargeNumber(parseFloat(String(fd.MarketCap)), currencySymbol),
                                  });
                                }

                                if (fd.Price) {
                                  items.push({
                                    label: createIndicatorLabel('当前价', 'fundamental'),
                                    
                                    children: formatCurrency(parseFloat(String(fd.Price || 0)), 2),
                                  });
                                }

                                if (fd['52WeekHigh'] && fd['52WeekLow']) {
                                  items.push({
                                    label: createIndicatorLabel('52周区间', 'fundamental'),
                                    span: 2,
                                    children: `${formatCurrency(parseFloat(String(fd['52WeekLow'] || 0)), 2)} - ${formatCurrency(parseFloat(String(fd['52WeekHigh'] || 0)), 2)}`,
                                  });
                                }

                                if (fd.RevenueTTM) {
                                  items.push({
                                    label: createIndicatorLabel('营收(TTM)', 'revenue'),
                                    
                                    children: formatLargeNumber(parseFloat(String(fd.RevenueTTM)), currencySymbol),
                                  });
                                }

                                if (fd.NetIncomeTTM) {
                                  items.push({
                                    label: createIndicatorLabel('净利润(TTM)', 'fundamental'),
                                    
                                    children: formatLargeNumber(parseFloat(String(fd.NetIncomeTTM)), currencySymbol),
                                  });
                                }

                                if (fd.EBITDATTM) {
                                  items.push({
                                    label: createIndicatorLabel('EBITDA(TTM)', 'fundamental'),
                                    
                                    children: formatLargeNumber(parseFloat(String(fd.EBITDATTM)), currencySymbol),
                                  });
                                }

                                if (fd.ProfitMargin) {
                                  items.push({
                                    label: createIndicatorLabel('利润率', 'profit_margin'),
                                    
                                    children: `${formatValue(parseFloat(String(fd.ProfitMargin || 0)) * 100, 2)}%`,
                                  });
                                }

                                if (fd.GrossMargin) {
                                  items.push({
                                    label: createIndicatorLabel('毛利率', 'profit_margin'),
                                    
                                    children: `${formatValue(parseFloat(String(fd.GrossMargin || 0)) * 100, 2)}%`,
                                  });
                                }

                                // 每股数据
                                if (fd.EPS) {
                                  items.push({
                                    label: createIndicatorLabel('每股收益(EPS)', 'eps'),
                                    
                                    children: formatCurrency(parseFloat(String(fd.EPS || 0)), 2),
                                  });
                                }

                                if (fd.BookValuePerShare) {
                                  items.push({
                                    label: createIndicatorLabel('每股净资产', 'fundamental'),
                                    
                                    children: formatCurrency(parseFloat(String(fd.BookValuePerShare || 0)), 2),
                                  });
                                }

                                if (fd.CashPerShare) {
                                  items.push({
                                    label: createIndicatorLabel('每股现金', 'fundamental'),
                                    
                                    children: formatCurrency(parseFloat(String(fd.CashPerShare || 0)), 2),
                                  });
                                }

                                if (fd.DividendPerShare) {
                                  items.push({
                                    label: createIndicatorLabel('每股股息', 'fundamental'),
                                    
                                    children: formatCurrency(parseFloat(String(fd.DividendPerShare || 0)), 3),
                                  });
                                }

                                // 估值指标
                                if (fd.PE) {
                                  const pe = parseFloat(String(fd.PE));
                                  items.push({
                                    label: createIndicatorLabel('市盈率(PE)', 'pe'),
                                    
                                    children: (
                                      <Space>
                                        <span>{formatValue(parseFloat(String(pe)), 2)}</span>
                                        {pe < 15 ? (
                                          <Tag color="success">低估</Tag>
                                        ) : pe > 25 ? (
                                          <Tag color="warning">高估</Tag>
                                        ) : (
                                          <Tag color="default">合理</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                if (fd.PriceToBook) {
                                  const pb = parseFloat(String(fd.PriceToBook));
                                  items.push({
                                    label: createIndicatorLabel('市净率(PB)', 'pb'),
                                    
                                    children: (
                                      <Space>
                                        <span>{formatValue(parseFloat(String(pb)), 2)}</span>
                                        {pb < 1 ? (
                                          <Tag color="success">低估</Tag>
                                        ) : pb > 3 ? (
                                          <Tag color="warning">高估</Tag>
                                        ) : (
                                          <Tag color="default">合理</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                if (fd.ROE) {
                                  const roe = parseFloat(String(fd.ROE)) * 100;
                                  items.push({
                                    label: createIndicatorLabel('净资产收益率(ROE)', 'roe'),
                                    
                                    children: (
                                      <Space>
                                        <span>{formatValue(parseFloat(String(roe)), 2)}%</span>
                                        {roe > 15 ? (
                                          <Tag color="success">优秀</Tag>
                                        ) : roe > 10 ? (
                                          <Tag color="default">良好</Tag>
                                        ) : (
                                          <Tag color="warning">一般</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 分析师预测
                                if (fd.TargetPrice) {
                                  const target = parseFloat(String(fd.TargetPrice));
                                  const currentPrice = parseFloat(String(fd.Price || analysisResult.indicators.current_price || 0));
                                  const upside = currentPrice > 0 ? ((target - currentPrice) / currentPrice * 100) : 0;
                                  items.push({
                                    label: createIndicatorLabel('目标价', 'target_price'),
                                    
                                    children: (
                                      <Space>
                                        <span>{formatCurrency(parseFloat(String(target)), 2)}</span>
                                        {upside > 0 ? (
                                          <Tag color="success">+{formatValue(upside, 1)}%</Tag>
                                        ) : (
                                          <Tag color="error">{formatValue(upside, 1)}%</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                if (fd.ConsensusRecommendation) {
                                  const config = statusMaps.consensus[String(fd.ConsensusRecommendation) as keyof typeof statusMaps.consensus] || 
                                    { text: String(fd.ConsensusRecommendation), color: 'default' };
                                  items.push({
                                    label: createIndicatorLabel('共识评级', 'fundamental'),
                                    
                                    children: <Tag color={config.color}>{config.text}</Tag>,
                                  });
                                }

                                if (fd.ProjectedEPS) {
                                  items.push({
                                    label: createIndicatorLabel('预测EPS', 'eps'),
                                    
                                    children: formatCurrency(parseFloat(String(fd.ProjectedEPS || 0)), 2),
                                  });
                                }

                                if (fd.ProjectedGrowthRate) {
                                  items.push({
                                    label: createIndicatorLabel('预测增长率', 'fundamental'),
                                    
                                    children: `${formatValue(parseFloat(String(fd.ProjectedGrowthRate || 0)) * 100, 2)}%`,
                                  });
                                }

                                return items;
                              })()}
                            />
                          ),
                        },
                        // 详细财务报表
                        ...(analysisResult.indicators.fundamental_data?.Financials ||
                          analysisResult.indicators.fundamental_data?.QuarterlyFinancials ||
                          analysisResult.indicators.fundamental_data?.BalanceSheet ||
                          analysisResult.indicators.fundamental_data?.Cashflow ? [{
                            key: 'financial-statements',
                            label: (
                              <span>
                                <FileTextOutlined style={{ marginRight: 8 }} />
                                <span>详细财务报表</span>
                              </span>
                            ),
                            children: (
                              <Tabs
                                defaultActiveKey="annual-financials"
                                items={[
                                  analysisResult.indicators.fundamental_data?.Financials && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.Financials) &&
                                  analysisResult.indicators.fundamental_data.Financials.length > 0 ? {
                                    key: 'annual-financials',
                                    label: '年度财务报表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.Financials} currencySymbol={currencySymbol} />,
                                  } : null,
                                  analysisResult.indicators.fundamental_data?.QuarterlyFinancials && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.QuarterlyFinancials) &&
                                  analysisResult.indicators.fundamental_data.QuarterlyFinancials.length > 0 ? {
                                    key: 'quarterly-financials',
                                    label: '季度财务报表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.QuarterlyFinancials} currencySymbol={currencySymbol} />,
                                  } : null,
                                  analysisResult.indicators.fundamental_data?.BalanceSheet && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.BalanceSheet) &&
                                  analysisResult.indicators.fundamental_data.BalanceSheet.length > 0 ? {
                                    key: 'balance-sheet',
                                    label: '资产负债表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.BalanceSheet} currencySymbol={currencySymbol} />,
                                  } : null,
                                  analysisResult.indicators.fundamental_data?.Cashflow && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.Cashflow) &&
                                  analysisResult.indicators.fundamental_data.Cashflow.length > 0 ? {
                                    key: 'cashflow',
                                    label: '现金流量表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.Cashflow} currencySymbol={currencySymbol} />,
                                  } : null,
                                ].filter((item): item is NonNullable<typeof item> => item !== null)}
                              />
                            ),
                          }] : []),
                      ]}
                      style={{ marginTop: 0 }}
                    />
                    )}

                  {/* 市场数据（股息、分析师推荐等） */}
                  {analysisResult.extra_data && (
                    <div>
                    <Collapse
                      ghost
                      defaultActiveKey={[]}
                      items={[
                        // 分析师推荐
                        analysisResult.extra_data.analyst_recommendations && analysisResult.extra_data.analyst_recommendations.length > 0 ? {
                          key: 'analyst',
                          label: (
                            <span>
                              <BarChartOutlined style={{ marginRight: 8 }} />
                              <span>分析师推荐</span> <span style={{ color: '#8c8c8c', fontSize: '13px' }}>(最近{analysisResult.extra_data.analyst_recommendations.length}条)</span>
                            </span>
                          ),
                          children: (
                            <Table
                              size="small"
                              pagination={{ pageSize: 10, showSizeChanger: false }}
                              dataSource={analysisResult.extra_data.analyst_recommendations}
                              rowKey={(record) => `${record.Firm || ''}-${record.Date || ''}-${record.id || Math.random().toString()}`}
                              columns={[
                                { 
                                  title: '日期', 
                                  dataIndex: 'Date', 
                                  key: 'date',
                                  width: '18%',
                                  render: (val: string) => (
                                    <span style={{ color: '#8c8c8c', fontSize: 12 }}>{val}</span>
                                  )
                                },
                                { 
                                  title: '机构', 
                                  dataIndex: 'Firm', 
                                  key: 'firm',
                                  width: '22%',
                                  render: (val: string) => (
                                    <span style={{ fontWeight: 500, fontSize: 13 }}>{val}</span>
                                  )
                                },
                                { 
                                  title: '原评级', 
                                  dataIndex: 'From Grade', 
                                  key: 'from',
                                  width: '20%',
                                  render: (val: string) => {
                                    if (!val) return <span style={{ color: '#bfbfbf' }}>-</span>;
                                    const lower = val.toLowerCase();
                                    const color = 
                                      lower.includes('strong buy') || lower.includes('outperform') ? 'green' :
                                      lower.includes('buy') || lower.includes('overweight') || lower.includes('positive') ? 'cyan' :
                                      lower.includes('hold') || lower.includes('neutral') ? 'default' :
                                      lower.includes('sell') || lower.includes('underperform') || lower.includes('underweight') ? 'red' : 'default';
                                    return (
                                      <Tag color={color}>
                                        {translateRating(val)}
                                      </Tag>
                                    );
                                  }
                                },
                                { 
                                  title: '新评级', 
                                  dataIndex: 'To Grade', 
                                  key: 'to',
                                  width: '20%',
                                  render: (val: string) => {
                                    if (!val) return <span style={{ color: '#bfbfbf' }}>-</span>;
                                    const lower = val.toLowerCase();
                                    const color = 
                                      lower.includes('strong buy') || lower.includes('outperform') ? 'green' :
                                      lower.includes('buy') || lower.includes('overweight') || lower.includes('positive') ? 'cyan' :
                                      lower.includes('hold') || lower.includes('neutral') ? 'default' :
                                      lower.includes('sell') || lower.includes('underperform') || lower.includes('underweight') ? 'red' : 'default';
                                    return (
                                      <Tag color={color} style={{ fontWeight: 600 }}>
                                        {translateRating(val)}
                                      </Tag>
                                    );
                                  }
                                },
                                { 
                                  title: '变化', 
                                  dataIndex: 'Action', 
                                  key: 'action',
                                  render: (val: string) => {
                                    if (!val) return '-';
                                    const lower = val.toLowerCase();
                                    const translated = translateAction(val);
                                    
                                    // 根据翻译结果确定颜色和图标
                                    let color = 'default';
                                    let icon = null;
                                    
                                    if (lower.includes('up') || lower.includes('upgrade')) {
                                      color = 'success';
                                      icon = <RiseOutlined />;
                                    } else if (lower.includes('down') || lower.includes('downgrade')) {
                                      color = 'error';
                                      icon = <FallOutlined />;
                                    } else if (lower.includes('init') || lower.includes('main')) {
                                      color = 'processing';
                                    }
                                    
                                    return (
                                      <Tag color={color} icon={icon}>
                                        {translated}
                                      </Tag>
                                    );
                                  }
                                },
                              ]}
                              scroll={{ x: 600 }}
                            />
                          ),
                        } : null,
                        
                        // 收益数据
                        analysisResult.extra_data.earnings?.quarterly && analysisResult.extra_data.earnings.quarterly.length > 0 ? {
                          key: 'earnings',
                          label: (
                            <span>
                              <MoneyCollectOutlined style={{ marginRight: 8 }} />
                              <span>季度收益</span> <span style={{ color: '#8c8c8c', fontSize: '13px' }}>({analysisResult.extra_data.earnings.quarterly.length}个季度)</span>
                            </span>
                          ),
                          children: (
                            <Table
                              size="small"
                              pagination={false}
                              dataSource={analysisResult.extra_data.earnings.quarterly}
                              rowKey={(record) => record.quarter || record.id || Math.random().toString()}
                              columns={[
                                { 
                                  title: '季度', 
                                  dataIndex: 'quarter', 
                                  key: 'quarter',
                                  width: '35%',
                                  render: (val: string) => (
                                    <span style={{ fontWeight: 600 }}>{val}</span>
                                  )
                                },
                                { 
                                  title: '营收', 
                                  dataIndex: 'Revenue', 
                                  key: 'revenue',
                                  render: (val: number) => val ? (
                                    <span style={{ color: '#1890ff', fontWeight: 500 }}>
                                      {formatLargeNumber(val)}
                                    </span>
                                  ) : '-'
                                },
                                { 
                                  title: '盈利', 
                                  dataIndex: 'Earnings', 
                                  key: 'earnings',
                                  render: (val: number) => val ? (
                                    <span style={{ color: val >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>
                                      {formatLargeNumber(val)}
                                    </span>
                                  ) : '-'
                                },
                              ]}
                            />
                          ),
                        } : null,
                        
                        // 新闻
                        analysisResult.extra_data?.news && analysisResult.extra_data.news.length > 0 ? {
                          key: 'news',
                          label: (
                            <span>
                              <FileTextOutlined style={{ marginRight: 8 }} />
                              <span>最新新闻</span> <span style={{ color: '#8c8c8c', fontSize: '13px' }}>({analysisResult.extra_data.news.length}条)</span>
                            </span>
                          ),
                          children: (() => {
                            const newsPageSize = 30;
                            const allNews = analysisResult.extra_data.news || [];
                            const totalNews = allNews.length;
                            const startIndex = (newsPage - 1) * newsPageSize;
                            const endIndex = startIndex + newsPageSize;
                            const currentNews = allNews.slice(startIndex, endIndex);
                            
                            return (
                              <div style={{ padding: '8px 0' }}>
                                {currentNews.map((item, index) => (
                                  <div 
                                    key={startIndex + index} 
                                    style={{ 
                                      marginBottom: 16, 
                                      paddingBottom: 16, 
                                      borderBottom: index < currentNews.length - 1 ? '1px solid #f0f0f0' : 'none',
                                      transition: 'all 0.3s'
                                    }}
                                    onMouseEnter={(e) => {
                                      e.currentTarget.style.backgroundColor = '#fafafa';
                                    }}
                                    onMouseLeave={(e) => {
                                      e.currentTarget.style.backgroundColor = 'transparent';
                                    }}
                                  >
                                    <div style={{ 
                                      fontWeight: 600, 
                                      marginBottom: 6,
                                      fontSize: 14,
                                      lineHeight: 1.5
                                    }}>
                                      {item.link ? (
                                        <a 
                                          href={item.link} 
                                          target="_blank" 
                                          rel="noopener noreferrer"
                                          style={{ 
                                            color: '#1890ff',
                                            textDecoration: 'none'
                                          }}
                                        >
                                          <RightOutlined style={{ fontSize: 10, marginRight: 6 }} />
                                          {item.title || item.headline || '无标题'}
                                        </a>
                                      ) : (
                                        <span>
                                          <RightOutlined style={{ fontSize: 10, marginRight: 6 }} />
                                          {item.title || item.headline || '无标题'}
                                        </span>
                                      )}
                                    </div>
                                    <div style={{ 
                                      fontSize: 12, 
                                      color: '#8c8c8c',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 8
                                    }}>
                                      {item.publisher && (
                                        <Tag color="blue" style={{ margin: 0 }}>
                                          {item.publisher}
                                        </Tag>
                                      )}
                                      {item.providerPublishTime && (
                                        <span style={{ fontSize: 12 }}>
                                          {formatDateTime(item.providerPublishTime)}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ))}
                                
                                {/* 分页组件 */}
                                {totalNews > newsPageSize && (
                                  <div style={{ 
                                    marginTop: 16, 
                                    display: 'flex', 
                                    justifyContent: 'center' 
                                  }}>
                                    <Pagination
                                      current={newsPage}
                                      pageSize={newsPageSize}
                                      total={totalNews}
                                      onChange={(page) => setNewsPage(page)}
                                      showSizeChanger={false}
                                      showTotal={(total) => `共 ${total} 条新闻`}
                                      size="small"
                                    />
                                  </div>
                                )}
                              </div>
                            );
                          })(),
                        } : null,
                      ].filter((item): item is NonNullable<typeof item> => item !== null)}
                      style={{ marginTop: 0 }}
                    />
                    </div>
                  )}

                </div>
                </div>
              )}

            </Space>
          </div>
        )}
      </div>

      {/* 交易抽屉 - 已隐藏 */}
      {false && (
        <Drawer
          title={
            <span>
              <DollarOutlined style={{ marginRight: 8 }} />
              交易
            </span>
          }
          placement="right"
          width={isMobile ? '100%' : 600}
          onClose={() => setTradeDrawerVisible(false)}
          open={tradeDrawerVisible}
          styles={{
            body: {
              padding: isMobile ? '12px' : '24px',
            },
          }}
        >
          <Tabs 
            activeKey={tradeDrawerTab} 
            onChange={setTradeDrawerTab}
            items={[
              {
                key: 'trade-form',
                label: (
                  <span>
                    <DollarOutlined />
                    下单
                  </span>
                ),
                children: (
                  <Form
                    form={tradeForm}
                    layout="vertical"
                    onFinish={async (values) => {
                      await handleTradeSubmit(values);
                      setTradeDrawerTab('orders');
                    }}
                    initialValues={{
                      action: 'BUY',
                      orderType: 'MKT',
                    }}
                  >
                    <Form.Item
                      label="交易方向"
                      name="action"
                      rules={[{ required: true, message: '请选择交易方向' }]}
                    >
                      <Select>
                        <Select.Option value="BUY">买入</Select.Option>
                        <Select.Option value="SELL">卖出</Select.Option>
                      </Select>
                    </Form.Item>

                    <Form.Item
                      label="股票代码"
                      name="symbol"
                      rules={[{ required: true, message: '请输入股票代码' }]}
                    >
                      <Input placeholder="例如: AAPL" style={{ textTransform: 'uppercase' }} />
                    </Form.Item>

                    <Form.Item
                      label="数量"
                      name="quantity"
                      rules={[{ required: true, message: '请输入数量' }]}
                    >
                      <InputNumber
                        min={1}
                        step={1}
                        placeholder="例如: 10"
                        style={{ width: '100%' }}
                      />
                    </Form.Item>

                    <Form.Item
                      label="订单类型"
                      name="orderType"
                      rules={[{ required: true, message: '请选择订单类型' }]}
                    >
                      <Select>
                        <Select.Option value="MKT">市价单</Select.Option>
                        <Select.Option value="LMT">限价单</Select.Option>
                      </Select>
                    </Form.Item>

                    <Form.Item
                      noStyle
                      shouldUpdate={(prevValues, currentValues) =>
                        prevValues.orderType !== currentValues.orderType
                      }
                    >
                      {({ getFieldValue }) =>
                        getFieldValue('orderType') === 'LMT' ? (
                          <Form.Item
                            label="限价"
                            name="limitPrice"
                            rules={[{ required: true, message: '请输入限价' }]}
                          >
                            <InputNumber
                              min={0}
                              step={0.01}
                              placeholder="例如: 175.50"
                              style={{ width: '100%' }}
                            />
                          </Form.Item>
                        ) : null
                      }
                    </Form.Item>

                    <Form.Item>
                      <Button type="primary" htmlType="submit" loading={tradeLoading} block>
                        提交订单
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
              {
                key: 'orders',
                label: (
                  <span>
                    <ShoppingOutlined />
                    订单列表
                  </span>
                ),
                children: (
                  <Space orientation="vertical" style={{ width: '100%' }}>
                    <div>
                      <Button icon={<ReloadOutlined />} onClick={loadOrders} loading={orderLoading}>
                        刷新
                      </Button>
                      <span style={{ marginLeft: 16, color: '#666' }}>
                        共 {orders.length} 个订单
                      </span>
                    </div>
                    <Table
                      columns={orderColumns}
                      dataSource={orders}
                      rowKey="orderId"
                      loading={orderLoading}
                      pagination={{ pageSize: 10 }}
                      scroll={{ y: 400 }}
                    />
                  </Space>
                ),
              },
            ]}
          />
        </Drawer>
      )}

      {/* AI分析报告抽屉 */}
      <Drawer
        title={
          <span>
            <RobotOutlined style={{ marginRight: 8 }} />
            AI 分析报告
            {aiAnalysisResult?.model && (
              <span style={{ marginLeft: 12, fontSize: 12, color: '#8c8c8c', fontWeight: 'normal' }}>
                ({aiAnalysisResult.model})
              </span>
            )}
          </span>
        }
        placement="right"
        size={isMobile ? 'large' : 800}
        onClose={() => setAiAnalysisDrawerVisible(false)}
        open={aiAnalysisDrawerVisible}
        styles={{
          body: {
            padding: isMobile ? '12px' : '24px',
          },
        }}
      >
        {aiAnalysisResult && aiAnalysisResult.ai_analysis && (
          <div style={{
            fontSize: 14,
            lineHeight: '1.8',
            padding: '8px',
          }}>
            <ReactMarkdown>{aiAnalysisResult.ai_analysis}</ReactMarkdown>
          </div>
        )}
      </Drawer>

      {/* 浮动页面定位器 */}
      {analysisResult && (
        <>
          <Popover
            content={
              <Menu
                mode="vertical"
                style={{ border: 'none', minWidth: 160 }}
                onClick={({ key }) => {
                  const sectionMap: Record<string, string> = {
                    'price-info': 'section-price-info',
                    'chart': 'section-chart',
                    'indicators': 'section-indicators',
                    'cycle': 'section-cycle',
                    'institutional': 'section-institutional',
                    'pivot': 'section-pivot',
                  };
                  const sectionId = sectionMap[key];
                  if (sectionId) {
                    scrollToSection(sectionId);
                  }
                }}
                items={[
                  {
                    key: 'price-info',
                    label: '价格信息',
                    icon: <DollarOutlined />,
                  },
                  {
                    key: 'chart',
                    label: 'K线图',
                    icon: <BarChartOutlined />,
                  },
                  {
                    key: 'indicators',
                    label: '技术指标',
                    icon: <ThunderboltOutlined />,
                  },
                  ...(analysisResult?.indicators?.dominant_cycle !== undefined || analysisResult?.indicators?.avg_cycle_length !== undefined) ? [{
                    key: 'cycle',
                    label: '周期分析',
                    icon: <CloudOutlined />,
                  }] : [],
                  ...(analysisResult?.indicators?.activity_score !== undefined) ? [{
                    key: 'institutional',
                    label: '机构操作分析',
                    icon: <TeamOutlined />,
                  }] : [],
                  ...(analysisResult?.indicators?.pivot || analysisResult?.indicators?.pivot_r1 || analysisResult?.indicators?.resistance_20d_high) ? [{
                    key: 'pivot',
                    label: '关键价位',
                    icon: <WarningOutlined />,
                  }] : [],
                ]}
              />
            }
            trigger="click"
            open={pageNavigatorVisible}
            onOpenChange={setPageNavigatorVisible}
            placement="leftTop"
          >
            <div style={{ 
              position: 'fixed', 
              right: isMobile ? 8 : 24, 
              bottom: 16, 
              zIndex: 1000 
            }}>
              <Button
                type="primary"
                size="small"
                icon={pageNavigatorVisible ? <CloseOutlined /> : <MenuOutlined />}
                style={{
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                }}
                title="页面导航"
              />
            </div>
          </Popover>
        </>
      )}

    </div>
  );
};

export default MainPage;
