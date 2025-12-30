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
 * 持仓数据
 */
export interface Position {
  symbol: string;
  position: number;
  avg_cost: number;
  market_price: number;
  market_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
}

/**
 * 订单数据
 */
export interface Order {
  orderId: number;
  symbol: string;
  action: 'BUY' | 'SELL';
  orderType: string;
  totalQuantity: number;
  lmtPrice?: number;
  auxPrice?: number;
  status: string;
  filled?: number;
  remaining?: number;
  avg_fill_price?: number;
  [key: string]: any; // 允许其他字段
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
  resistance_20d_high?: number;
  support_20d_low?: number;
  // 周期分析
  dominant_cycle?: number;
  cycle_strength?: number;
  cycle_quality?: 'strong' | 'moderate' | 'weak' | 'none';
  cycle_position?: number;
  cycle_phase?: 'early_rise' | 'mid_rise' | 'late_rise' | 'decline';
  cycle_phase_desc?: string;
  cycle_suggestion?: string;
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
  sideways_reasons?: string[];
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
  // 机构操作分析
  volume_ratio_20?: number;
  volume_ratio_60?: number;
  is_volume_spike?: boolean;
  is_volume_surge?: boolean;
  is_volume_shrink?: boolean;
  price_change_5d?: number;
  volume_change_5d?: number;
  price_volume_rising?: boolean;
  price_volume_falling?: boolean;
  price_rising_volume_shrinking?: boolean;
  price_falling_volume_shrinking?: boolean;
  fund_flow?: 'inflow' | 'outflow' | 'neutral';
  fund_flow_desc?: string;
  cost_position?: 'below_cost' | 'above_cost' | 'near_cost';
  cost_position_desc?: string;
  chip_concentration?: 'high' | 'medium' | 'low';
  chip_concentration_desc?: string;
  price_pattern?: 'accumulation' | 'distribution' | 'consolidation' | 'controlled_rise' | 'normal';
  price_pattern_desc?: string;
  suggestion?: string;
  // 机构操作分析增强 - MFI
  mfi?: number; // 资金流量指数
  money_flow_ratio?: number; // 资金流量比率
  mfi_signal?: 'overbought' | 'strong' | 'neutral' | 'weak' | 'oversold'; // MFI信号
  mfi_signal_desc?: string; // MFI信号描述
  mfi_divergence?: 'bearish' | 'bullish' | 'none'; // MFI背离
  // 机构操作分析增强 - CMF
  cmf?: number; // 蔡金资金流量
  cmf_signal?: 'strong_accumulation' | 'accumulation' | 'neutral' | 'distribution' | 'strong_distribution'; // CMF信号
  cmf_signal_desc?: string; // CMF信号描述
  // 机构操作分析增强 - 筹码分布
  chip_profit_ratio?: number; // 获利盘比例
  chip_loss_ratio?: number; // 亏损盘比例
  chip_peak_price?: number; // 筹码峰值价格
  chip_peak_volume_ratio?: number; // 筹码峰值成交量比例
  chip_concentration_level?: 'high' | 'medium' | 'low'; // 筹码集中度等级
  chip_weighted_avg_cost?: number; // 加权平均成本
  chip_cost_deviation_pct?: number; // 成本偏离度百分比
  chip_main_cost_low?: number; // 主力成本区间下限
  chip_main_cost_high?: number; // 主力成本区间上限
  chip_main_cost_center?: number; // 主力成本中心
  chip_price_position?: 'below_main_cost' | 'above_main_cost' | 'in_main_cost'; // 价格相对主力成本位置
  chip_price_position_desc?: string; // 价格位置描述
  chip_entropy?: number; // 筹码熵（分散度）
  chip_dispersion?: 'highly_dispersed' | 'moderately_dispersed' | 'concentrated'; // 筹码分散程度
  chip_dispersion_desc?: string; // 筹码分散描述
  // 机构操作分析增强 - 主力成本
  main_force_cost?: number; // 主力成本
  main_force_cost_lower?: number; // 主力成本下限
  main_force_cost_upper?: number; // 主力成本上限
  main_force_cost_range_pct?: number; // 主力成本区间百分比
  main_force_cost_deviation_pct?: number; // 主力成本偏离度
  main_force_position?: 'below_cost' | 'above_cost' | 'near_cost'; // 主力仓位
  main_force_position_desc?: string; // 主力仓位描述
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
  buy?: boolean;
  sell?: boolean;
  score?: number;
  recommendation?: string;
  risk?: {
    level: string;
    score: number;
  };
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
  signals: Signals;
  candles?: Candle[];
  ai_analysis?: string;
  ai_available?: boolean;
  model?: string;
  ai_error?: string;
  extra_data?: ExtraAnalysisData;  // 额外数据（股息、机构持仓等）
  [key: string]: any;
}

/**
 * 热门股票
 */
export interface HotStock {
  symbol: string;
  name: string;
  category: string;
}

/**
 * 指标信息
 */
export interface IndicatorInfo {
  name: string;
  description: string;
  calculation?: string;
  reference_range: Record<string, string>;
  interpretation: string;
  usage: string;
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
  DividendPerShare?: number;
  
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
  
  // 持有人信息
  MajorHolders?: HolderRecord[];
  InstitutionalHolders?: InstitutionalHolderRecord[];
  
  // 历史数据
  DividendHistory?: Record<string, number>;  // 日期 -> 股息金额
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
 * 持有人记录
 */
export interface HolderRecord {
  Holder?: string;
  Name?: string;
  Shares?: number | string;
  Value?: number | string;
  '% Out'?: number | string;
  Percent?: number | string;
  [key: string]: any;
}

/**
 * 机构持有人记录
 */
export interface InstitutionalHolderRecord {
  Holder?: string;
  Name?: string;
  Shares?: number | string;
  Value?: number | string;
  '% Out'?: number | string;
  Percent?: number | string;
  DateReported?: string;
  [key: string]: any;
}

/**
 * 指标信息响应
 */
export interface IndicatorInfoResponse {
  success: boolean;
  indicators?: Record<string, IndicatorInfo>;
  indicator?: string;
  info?: IndicatorInfo;
  message?: string;
}

/**
 * 内部交易记录
 */
export interface InsiderTransaction {
  Insider?: string;
  Transaction?: string;
  Shares?: number;
  Value?: number;
  Date?: string;
  [key: string]: any;
}

/**
 * 分析师推荐记录
 */
export interface AnalystRecommendation {
  Firm?: string;
  'To Grade'?: string;
  'From Grade'?: string;
  Action?: string;
  Date?: string;
  [key: string]: any;
}

/**
 * 收益数据
 */
export interface EarningsData {
  yearly?: Array<{
    year: string;
    Revenue?: number;
    Earnings?: number;
    [key: string]: any;
  }>;
  quarterly?: Array<{
    quarter: string;
    Revenue?: number;
    Earnings?: number;
    [key: string]: any;
  }>;
}

/**
 * 新闻记录
 */
export interface NewsItem {
  title?: string;
  publisher?: string;
  link?: string;
  providerPublishTime?: string;
  [key: string]: any;
}

/**
 * 额外分析数据
 */
export interface ExtraAnalysisData {
  institutional_holders?: InstitutionalHolderRecord[];
  insider_transactions?: InsiderTransaction[];
  analyst_recommendations?: AnalystRecommendation[];
  earnings?: EarningsData;
  news?: NewsItem[];
}