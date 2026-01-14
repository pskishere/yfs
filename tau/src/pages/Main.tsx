/**
 * 主页面 - 股票分析功能（重构版）
 */
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Button,
  Space,
  Form,
  Select,
  AutoComplete,
  Spin,
  message,
  Drawer,
  Modal,
  Menu,
} from 'antd';
import {
  ReloadOutlined,
  DollarOutlined,
  BarChartOutlined,
  RobotOutlined,
  ShareAltOutlined,
  ThunderboltOutlined,
  CloudOutlined,
  WarningOutlined,
  DeleteOutlined,
  MenuOutlined,
  UnorderedListOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import type { HotStock } from '../types/index';
import { useStockAnalysis } from '../hooks/useStockAnalysis';
import { PriceInfo } from '../components/PriceInfo';
import { ChartSection } from '../components/ChartSection';
import { TechnicalIndicators } from '../components/TechnicalIndicators';
import { CycleAnalysis } from '../components/CycleAnalysis';
import { PivotPoints } from '../components/PivotPoints';
import { FundamentalData } from '../components/FundamentalData';
import { MarketData } from '../components/MarketData';
import { OptionsTable } from '../components/OptionsTable';
import { IndicatorLabel } from '../components/IndicatorLabel';
import ChatSessionDrawer from '../components/ChatSessionDrawer';
import ChatDrawer from '../components/ChatDrawer';
import './Main.css';

/**
 * 主页面组件
 */
const MainPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [analyzeForm] = Form.useForm();

  // 使用自定义 Hook 管理分析状态和业务逻辑
  const {
    analysisResult,
    aiAnalysisResult,
    analysisLoading,
    aiAnalysisDrawerVisible,
    currentSymbol,
    aiStatus,
    aiStatusMsg,
    stockOptions,
    indicatorInfoMap,
    setAiAnalysisDrawerVisible,
    setCurrentSymbol,
    runAiAnalysis,
    handleAnalyze,
    handleRefreshAnalyze,
    handleDeleteStock,
    loadHotStocks,
    loadIndicatorInfo,
    stopAiPolling,
    optionsData,
  } = useStockAnalysis();

  const [newsPage, setNewsPage] = useState<number>(1);
  const [pageNavigatorVisible, setPageNavigatorVisible] = useState<boolean>(false);
  const [isMobile, setIsMobile] = useState<boolean>(typeof window !== 'undefined' && window.innerWidth <= 768);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState<boolean>(false);
  const [chatDrawerOpen, setChatDrawerOpen] = useState<boolean>(false);
  const [currentChatSessionId, setCurrentChatSessionId] = useState<string | undefined>(undefined);

  // 监听模型变化
  const selectedModel = Form.useWatch('model', analyzeForm);

  // 标记是否已从 URL 加载过
  const hasLoadedFromUrlRef = useRef<boolean>(false);

  // 货币符号
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

  // 股票名称
  const stockName = useMemo(() => {
    if (!analysisResult) return '';
    return (
      (analysisResult as any)?.stock_name ||
      (analysisResult.extra_data as any)?.stock_name ||
      ''
    );
  }, [analysisResult]);

  /**
   * 创建带知识讲解的指标标签
   */
  const createIndicatorLabel = (label: string, indicatorKey: string): React.ReactNode => {
    return <IndicatorLabel label={label} indicatorKey={indicatorKey} indicatorInfoMap={indicatorInfoMap} />;
  };

  /**
   * 更新 URL 参数
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

  /**
   * 跳转到页面指定模块
   */
  const scrollToSection = (sectionId: string) => {
    setPageNavigatorVisible(false);
    
    setTimeout(() => {
      let element = document.getElementById(sectionId);
      
      if (!element) {
        element = document.querySelector(`#${sectionId}`) as HTMLElement;
      }
      
      if (element) {
        const headerOffset = 80;
        const rect = element.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const elementTop = rect.top + scrollTop;
        const offsetPosition = elementTop - headerOffset;

        window.scrollTo({
          top: Math.max(0, offsetPosition),
          behavior: 'smooth',
        });
        
        setTimeout(() => {
          const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
          const targetScrollTop = elementTop - headerOffset;
          if (Math.abs(currentScrollTop - targetScrollTop) > 10) {
            element.scrollIntoView({
              behavior: 'smooth',
              block: 'start',
            });
            setTimeout(() => {
              window.scrollTo({
                top: Math.max(0, elementTop - headerOffset),
                behavior: 'smooth',
              });
            }, 100);
          }
        }, 300);
      }
    }, 200);
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
   * 执行分析（封装）
   */
  const onAnalyze = async (values: any): Promise<void> => {
    if (!values || !values.symbol) {
      message.error('请输入股票代码');
      return;
    }

    stopAiPolling();
    setNewsPage(1); // 重置新闻页码

    const { symbol, duration, barSize } = values;
    const durationValue = duration || '5y';
    const barSizeValue = barSize || '1 day';

    await handleAnalyze(symbol, durationValue, barSizeValue);
    setCurrentSymbol(symbol);
    updateUrlParams(symbol);
  };

  /**
   * 刷新分析（封装）
   */
  const onRefreshAnalyze = async (): Promise<void> => {
    if (!currentSymbol) {
      message.warning('请先进行一次分析');
      return;
    }

    const formValues = analyzeForm.getFieldsValue();
    const duration = formValues.duration || '5y';
    const barSize = formValues.barSize || '1 day';

    await handleRefreshAnalyze(currentSymbol, duration, barSize);
  };

  /**
   * 触发 AI 分析
   */
  const onAiAnalyze = () => {
    if (!currentSymbol || !analysisResult) return;

    const formValues = analyzeForm.getFieldsValue();
    const duration = formValues.duration || '5y';
    const barSize = formValues.barSize || '1 day';
    const model = formValues.model || 'deepseek-v3.1:671b-cloud';

    console.log('手动触发AI分析，使用模型:', model);
    runAiAnalysis(currentSymbol, duration, barSize, model, analysisResult);
  };

  /**
   * 初始化：加载热门股票和指标信息
   */
  useEffect(() => {
    loadHotStocks(renderStockOption);
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
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  /**
   * 从 URL 参数自动加载分析
   */
  useEffect(() => {
    if (hasLoadedFromUrlRef.current) return;
    
    const symbolFromUrl = searchParams.get('symbol');
    if (symbolFromUrl) {
      hasLoadedFromUrlRef.current = true;
      
      analyzeForm.setFieldsValue({
        symbol: symbolFromUrl.toUpperCase(),
      });
      
      setTimeout(() => {
        onAnalyze({
          symbol: symbolFromUrl.toUpperCase(),
        });
      }, 100);
    }
  }, []);

  return (
    <div className="main-page">
      {/* 固定顶部区域：股票输入框 */}
      <div className="fixed-top">
        <Space orientation="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Form
              form={analyzeForm}
              layout="inline"
              onFinish={onAnalyze}
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
                  }}
                  onFocus={() => {
                    loadHotStocks(renderStockOption);
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
                    { label: 'Gemini 3 Flash Preview', value: 'gemini-3-flash-preview:latest' },
                    { label: 'Gemini 3 Flash Preview', value: 'gemini-3-flash-preview:cloud' },
                    { label: 'Qwen3 Next 80B', value: 'qwen3-next:80b-cloud' },
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
            <Space orientation="vertical" style={{ width: '100%' }} size="small">
              {/* 操作按钮区域 */}
              <Space style={{ marginBottom: 16 }} wrap>
                <Button
                  type="default"
                  icon={<ReloadOutlined />}
                  onClick={onRefreshAnalyze}
                  loading={analysisLoading}
                >
                  刷新
                </Button>
                <Button
                  type="default"
                  icon={<RobotOutlined />}
                  loading={aiStatus === 'running'}
                  disabled={!currentSymbol || !analysisResult}
                  onClick={onAiAnalyze}
                >
                  {aiStatus === 'running' ? aiStatusMsg : 'AI分析'}
                </Button>
                <Button
                  type="default"
                  icon={<ShareAltOutlined />}
                  onClick={handleShare}
                  disabled={!currentSymbol}
                >
                  分享
                </Button>
              </Space>

              {/* 技术分析组件 */}
              {analysisResult && analysisResult.indicators && (
                <div>
                  <PriceInfo
                    analysisResult={analysisResult}
                    currentSymbol={currentSymbol}
                    stockName={stockName}
                    currencySymbol={currencySymbol}
                    createIndicatorLabel={createIndicatorLabel}
                  />

                  <ChartSection
                    currentSymbol={currentSymbol}
                    analysisResult={analysisResult}
                    isMobile={isMobile}
                  />

                  <TechnicalIndicators
                    analysisResult={analysisResult}
                    currencySymbol={currencySymbol}
                    createIndicatorLabel={createIndicatorLabel}
                  />

                  <CycleAnalysis
                    analysisResult={analysisResult}
                    currencySymbol={currencySymbol}
                    createIndicatorLabel={createIndicatorLabel}
                  />

                  <PivotPoints
                    analysisResult={analysisResult}
                    currencySymbol={currencySymbol}
                    createIndicatorLabel={createIndicatorLabel}
                  />

                  <FundamentalData
                    analysisResult={analysisResult}
                    currencySymbol={currencySymbol}
                    createIndicatorLabel={createIndicatorLabel}
                    newsPage={newsPage}
                    setNewsPage={setNewsPage}
                  />

                  {analysisResult.extra_data && (
                    <MarketData
                      analysisResult={analysisResult}
                      currencySymbol={currencySymbol}
                      createIndicatorLabel={createIndicatorLabel}
                    />
                  )}

                  {optionsData && (
                    <OptionsTable 
                      data={optionsData} 
                      createIndicatorLabel={createIndicatorLabel}
                    />
                  )}
                </div>
              )}
            </Space>
          </div>
        )}
      </div>

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
        width={isMobile ? '100%' : 800}
        onClose={() => setAiAnalysisDrawerVisible(false)}
        open={aiAnalysisDrawerVisible}
        styles={{
          header: {
            paddingTop: 'calc(16px + env(safe-area-inset-top))',
          },
          body: {
            padding: isMobile ? '12px' : '24px',
            paddingBottom: 'calc(24px + env(safe-area-inset-bottom))',
          },
        }}
      >
        {aiAnalysisResult && aiAnalysisResult.ai_analysis && (
          <div className="markdown-content" style={{
            fontSize: 14,
            lineHeight: '1.8',
            padding: '8px',
          }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{aiAnalysisResult.ai_analysis}</ReactMarkdown>
          </div>
        )}
      </Drawer>

      {/* 浮动操作按钮 */}
      <div style={{ 
        position: 'fixed', 
        right: 24, 
        bottom: `calc(${analysisResult ? 70 : 24}px + env(safe-area-inset-bottom))`, 
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }}>
        <Button
          type="primary"
          shape="circle"
          size="large"
          icon={<MessageOutlined />}
          onClick={() => setSessionDrawerOpen(true)}
          style={{
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            width: 48,
            height: 48,
          }}
          title="聊天会话"
        />
      </div>

      {/* 侧边导航抽屉 */}
      {analysisResult && (
        <>
          <Drawer
            title="页面导航"
            placement="right"
            onClose={() => setPageNavigatorVisible(false)}
            open={pageNavigatorVisible}
            width={isMobile ? 240 : 280}
            styles={{
              header: {
                paddingTop: 'calc(16px + env(safe-area-inset-top))',
              },
              body: {
                padding: 0,
                paddingBottom: 'env(safe-area-inset-bottom)',
              }
            }}
          >
            <Menu
              mode="vertical"
              style={{ border: 'none' }}
              onClick={({ key }) => {
                const sectionMap: Record<string, string> = {
                  'price-info': 'section-price-info',
                  'chart': 'section-chart',
                  'indicators': 'section-indicators',
                  'cycle': 'section-cycle',
                  'pivot': 'section-pivot',
                  'fundamental': 'section-fundamental',
                };
                const sectionId = sectionMap[key];
                if (sectionId) {
                  scrollToSection(sectionId);
                  if (isMobile) setPageNavigatorVisible(false);
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
                ...(analysisResult?.indicators?.pivot || analysisResult?.indicators?.pivot_r1 || analysisResult?.indicators?.resistance_20d_high) ? [{
                  key: 'pivot',
                  label: '关键价位',
                  icon: <WarningOutlined />,
                }] : [],
                {
                  key: 'fundamental',
                  label: '基本面/新闻',
                  icon: <UnorderedListOutlined />,
                },
              ]}
            />
          </Drawer>

          {/* 抽屉唤起手柄 */}
          {!pageNavigatorVisible && !chatDrawerOpen && !sessionDrawerOpen && !aiAnalysisDrawerVisible && (
            <div 
              className="nav-drawer-handle"
              onClick={() => setPageNavigatorVisible(true)}
            >
              <MenuOutlined />
            </div>
          )}
        </>
      )}

      {/* 会话列表抽屉 */}
      <ChatSessionDrawer
        open={sessionDrawerOpen}
        onClose={() => setSessionDrawerOpen(false)}
        onSelectSession={(sessionId) => {
          setCurrentChatSessionId(sessionId);
          setChatDrawerOpen(true);
        }}
        model={selectedModel}
      />

      {/* AI 对话抽屉 */}
      <ChatDrawer
        open={chatDrawerOpen}
        onClose={() => setChatDrawerOpen(false)}
        sessionId={currentChatSessionId}
        model={selectedModel}
      />
    </div>
  );
};

export default MainPage;
