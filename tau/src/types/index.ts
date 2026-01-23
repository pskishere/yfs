/**
 * API响应基础类型
 */
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  error_code?: number;  // 错误代码（如200表示证券不存在）
  data?: T;
  [key: string]: any;
}

/**
 * K线数据
 */
export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * 技术指标
 */
export interface Indicators {
  symbol?: string;
  current_price?: number;
  data_points?: number;
  price_change_pct?: number;
  trend_direction?: string;
  trend_strength?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  bb_upper?: number;
  bb_middle?: number;
  bb_lower?: number;
  bb_upper_series?: number[];  // 布林带上轨历史数据
  bb_middle_series?: number[]; // 布林带中轨历史数据
  bb_lower_series?: number[];  // 布林带下轨历史数据
  ma5?: number;
  ma10?: number;
  ma20?: number;
  ma50?: number;
  kdj_k?: number;
  kdj_d?: number;
  kdj_j?: number;
  williams_r?: number;
  atr?: number;
  atr_percent?: number;
  // 新增现代指标
  cci?: number;
  cci_signal?: string;  // 'overbought' | 'oversold' | 'neutral'
  adx?: number;
  adx_signal?: string;  // 'strong_trend' | 'trend' | 'weak_trend'
  plus_di?: number;
  minus_di?: number;
  vwap?: number;
  vwap_20?: number;
  vwap_signal?: string;  // 'above' | 'below' | 'at'
  vwap_deviation?: number;
  sar?: number;
  sar_signal?: string;  // 'buy' | 'sell'
  sar_trend?: string;  // 'up' | 'down'
  sar_distance_pct?: number;
  sar_af?: number;
  sar_ep?: number;
  // Ichimoku Cloud
  ichimoku_tenkan_sen?: number;
  ichimoku_kijun_sen?: number;
  ichimoku_senkou_span_a?: number;
  ichimoku_senkou_span_b?: number;
  ichimoku_chikou_span?: number;
  ichimoku_status?: string;
  ichimoku_tk_cross?: string;
  ichimoku_cloud_top?: number;
  ichimoku_cloud_bottom?: number;
  // SuperTrend
  supertrend?: number;
  supertrend_direction?: string; // 'up' | 'down'
  // StochRSI
  stoch_rsi_k?: number;
  stoch_rsi_d?: number;
  stoch_rsi_status?: string; // 'oversold' | 'overbought' | 'neutral'
  // Volume Profile
  vp_poc?: number;
  vp_vah?: number;
  vp_val?: number;
  vp_status?: string; // 'above_va' | 'below_va' | 'inside_va'
  // 其他指标
  volatility_20?: number;
  volume_ratio?: number;
  obv_trend?: string;
  consecutive_up_days?: number;
  consecutive_down_days?: number;
  pivot?: number;
  pivot_r1?: number;
  pivot_r2?: number;
  pivot_r3?: number;
  pivot_s1?: number;
  pivot_s2?: number;
  pivot_s3?: number;
  fundamental_data?: FundamentalData;
  news_data?: NewsItem[];
  resistance_20d_high?: number;
  support_20d_low?: number;
  // 周期分析
  dominant_cycle?: number;
  cycle_strength?: number;
  cycle_quality?: 'strong' | 'moderate' | 'weak' | 'none';
  cycle_position?: number;
  cycle_phase?: 'early_rise' | 'mid_rise' | 'late_rise' | 'decline';
  cycle_phase_desc?: string;
  avg_cycle_length?: number;
  std_cycle_length?: number;
  cycle_consistency?: number;
  cycle_stability?: 'high' | 'medium' | 'low' | 'very_low';
  cycle_stability_desc?: string;
  avg_peak_period?: number;
  avg_trough_period?: number;
  std_peak_period?: number;
  std_trough_period?: number;
  overall_cycle_strength?: number;
  peak_count?: number;
  trough_count?: number;
  fft_cycle?: number;
  fft_power?: number;
  avg_autocorrelation?: number;
  max_autocorrelation?: number;
  // 多周期检测
  short_cycles?: number[];
  short_cycle_strength?: number;
  medium_cycles?: number[];
  medium_cycle_strength?: number;
  long_cycles?: number[];
  long_cycle_strength?: number;
  // 周期预测
  days_from_last_trough?: number;
  days_to_next_peak?: number;
  days_to_next_trough?: number;
  next_turn_type?: 'peak' | 'trough';
  next_turn_days?: number;
  next_turn_desc?: string;
  // 周期振幅
  avg_cycle_amplitude?: number;
  max_cycle_amplitude?: number;
  min_cycle_amplitude?: number;
  // 周期总结
  cycle_summary?: string;
  // 横盘判断
  sideways_market?: boolean;
  sideways_strength?: number;
  sideways_price_range_pct?: number;
  sideways_price_change_pct?: number;
  sideways_volatility?: number;
  sideways_amplitude_20?: number; // 20日振幅统计
  sideways_trend_pct?: number; // 趋势变化百分比
  sideways_slope_pct?: number; // 横盘斜率百分比
  sideways_price_entropy?: number; // 价格分布熵
  sideways_volume_cv?: number; // 成交量变异系数
  sideways_type?: 'narrow' | 'standard' | 'wide'; // 横盘类型
  sideways_type_desc?: string; // 横盘类型描述
  // 周期分析增强
  adaptive_config_used?: boolean; // 是否使用自适应配置
  config_volatility_level?: 'high' | 'medium' | 'low'; // 配置波动率等级
  wavelet_available?: boolean; // 小波分析是否可用
  wavelet_dominant_cycle?: number; // 小波主导周期
  wavelet_cycle_strength?: number; // 小波周期强度
  wavelet_recent_cycle?: number; // 最近周期（小波）
  wavelet_cycle_stability?: number; // 小波周期稳定性
  wavelet_significant_cycles?: Array<{
    period: number;
    strength: number;
    scale: number;
  }>; // 显著周期列表
  wavelet_method?: string; // 小波方法
  confidence_score?: number; // 周期预测置信度分数
  confidence_level?: 'high' | 'medium' | 'low' | 'very_low' | 'none'; // 置信度等级
  confidence_desc?: string; // 置信度描述
  confidence_factors?: string[]; // 置信度因素
  // 周期时间段详情
  cycle_periods?: Array<{
    period_index: number;
    cycle_type?: 'rise' | 'decline' | 'sideways';
    cycle_type_desc?: string;
    start_time?: string;
    end_time?: string;
    start_index: number;
    end_index: number;
    duration: number;
    high_price: number;
    high_time?: string;
    low_price: number;
    low_time?: string;
    is_current?: boolean; // 标记是否为当前进行中的周期
  }>;
  // 年周期数据
  yearly_cycles?: Array<{
    year: number;
    first_date?: string;
    last_date?: string;
    first_close: number;
    last_close: number;
    first_to_last_change: number;
    min_low?: number;
    max_high?: number;
    min_low_date?: string;
    max_high_date?: string;
    low_to_high_change: number;
    trading_days: number;
  }>;
  // 月周期数据
  monthly_cycles?: Array<{
    month: string;  // 格式: "2024-01"
    first_date?: string;
    last_date?: string;
    first_close: number;
    last_close: number;
    first_to_last_change: number;
    min_low?: number;
    max_high?: number;
    min_low_date?: string;
    max_high_date?: string;
    low_to_high_change: number;
    trading_days: number;
  }>;
  [key: string]: any;
}

/**
 * 交易信号
 */
export interface Signals {
  signals: string[];
  [key: string]: any;
}

/**
 * 技术分析结果
 */
export interface AnalysisResult {
  success: boolean;
  message?: string;
  error_code?: number;  // 错误代码（如200表示证券不存在）
  indicators: Indicators;
  signals?: Signals;
  candles?: Candle[];
  [key: string]: any;
}

/**
 * 订阅股票
 */
export interface SubscriptionStock {
  symbol: string;
  name: string;
  category: string;
}



/**
 * 基本面数据 - 详细类型定义
 */
export interface FundamentalData {
  // 基本信息
  CompanyName?: string;
  Exchange?: string;
  Employees?: number;
  SharesOutstanding?: number;
  
  // 市值与价格
  MarketCap?: number;
  Price?: number;
  '52WeekHigh'?: number;
  '52WeekLow'?: number;
  
  // 财务指标
  RevenueTTM?: number;
  NetIncomeTTM?: number;
  EBITDATTM?: number;
  ProfitMargin?: number;
  GrossMargin?: number;
  OperatingMargin?: number;
  
  // 每股数据
  EPS?: number;
  ForwardEPS?: number;
  BookValuePerShare?: number;
  CashPerShare?: number;

  // 估值指标
  PE?: number;
  ForwardPE?: number;
  PriceToBook?: number;
  ROE?: number;
  ROA?: number;
  ROIC?: number;
  
  // 分析师预测
  TargetPrice?: number;
  TargetHighPrice?: number;
  TargetLowPrice?: number;
  ConsensusRecommendation?: number | string;
  RecommendationKey?: string;
  NumberOfAnalystOpinions?: number;
  ProjectedEPS?: number;
  ProjectedGrowthRate?: number;
  
  // 详细财务报表（新增）
  Financials?: FinancialRecord[];  // 年度财务报表
  QuarterlyFinancials?: FinancialRecord[];  // 季度财务报表
  BalanceSheet?: BalanceSheetRecord[];  // 年度资产负债表
  QuarterlyBalanceSheet?: BalanceSheetRecord[];  // 季度资产负债表
  Cashflow?: CashflowRecord[];  // 年度现金流量表
  QuarterlyCashflow?: CashflowRecord[];  // 季度现金流量表
  
  // 期权数据
  options?: OptionsData;
  
  // 历史数据
  StockSplits?: Record<string, number>;  // 日期 -> 分割比例
  
  // 其他字段
  [key: string]: any;
}

/**
 * 财务报表记录
 */
export interface FinancialRecord {
  index?: string;
  Date?: string;
  [key: string]: any;  // 动态字段，如 TotalRevenue, NetIncome 等
}

/**
 * 资产负债表记录
 */
export interface BalanceSheetRecord {
  index?: string;
  Date?: string;
  [key: string]: any;  // 动态字段，如 TotalAssets, TotalLiab 等
}

/**
 * 现金流量表记录
 */
export interface CashflowRecord {
  index?: string;
  Date?: string;
  [key: string]: any;  // 动态字段，如 OperatingCashFlow, CapitalExpenditure 等
}



/**
 * 股票新闻项
 */
export interface NewsItem {
  uuid: string;
  title: string;
  publisher: string;
  link: string;
  provider_publish_time: number;
  type: string;
  thumbnail?: {
    resolutions: Array<{
      url: string;
      width: number;
      height: number;
      tag: string;
    }>;
  };
}

/**
 * 期权项数据
 */
export interface OptionItem {
  contractSymbol: string;
  lastTradeDate: string;
  strike: number;
  lastPrice: number;
  bid: number;
  ask: number;
  change: number;
  percentChange: number;
  volume: number;
  openInterest: number;
  impliedVolatility: number;
  inTheMoney: boolean;
  contractSize: string;
  currency: string;
}

/**
 * 期权链数据 (单个到期日)
 */
export interface OptionChain {
  calls: OptionItem[];
  puts: OptionItem[];
}

/**
 * 期权数据响应
 */
export interface OptionsData {
  expiration_dates: string[];
  chains: Record<string, OptionChain>;
}