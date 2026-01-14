/**
 * 格式化工具函数
 */

/**
 * 格式化数值
 * 
 * @param value - 要格式化的数值
 * @param decimals - 小数位数，默认2位
 * @returns 格式化后的字符串，如果值为undefined或null则返回'N/A'
 */
export const formatValue = (value: number | undefined, decimals: number = 2): string => {
  if (value === undefined || value === null) return 'N/A';
  return typeof value === 'number' ? value.toFixed(decimals) : String(value);
};

/**
 * 格式化大数字(市值、营收等)
 * 
 * @param value - 要格式化的数值
 * @returns 格式化后的字符串，如 $1.23B、$456.78M 等
 */
export const formatLargeNumber = (value: number, symbol: string = '$'): string => {
  const absValue = Math.abs(value);
  if (absValue >= 1e12) {
    return `${symbol}${(value / 1e12).toFixed(2)}T`;
  } else if (absValue >= 1e9) {
    return `${symbol}${(value / 1e9).toFixed(2)}B`;
  } else if (absValue >= 1e6) {
    return `${symbol}${(value / 1e6).toFixed(2)}M`;
  }
  return `${symbol}${value.toFixed(2)}`;
};

/**
 * 格式化时间显示
 * 支持 ISO 8601 格式 (2025-12-07T13:30:23Z) 和其他常见格式
 * 
 * @param dateTime - 时间字符串、时间戳或Date对象
 * @returns 格式化后的时间字符串，如"刚刚"、"5分钟前"、"2025-01-01 12:00"等
 */
export const formatDateTime = (dateTime: string | number | Date | undefined | null): string => {
  if (!dateTime) return '-';
  
  try {
    let date: Date;
    
    if (dateTime instanceof Date) {
      date = dateTime;
    } else if (typeof dateTime === 'number') {
      date = new Date(dateTime);
    } else if (typeof dateTime === 'string') {
      // 处理 ISO 8601 格式 (2025-12-07T13:30:23Z)
      date = new Date(dateTime);
    } else {
      return String(dateTime);
    }
    
    if (isNaN(date.getTime())) {
      return String(dateTime);
    }
    
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diff / 60000);
    const diffHours = Math.floor(diff / 3600000);
    const diffDays = Math.floor(diff / 86400000);
    
    // 如果是今天，显示相对时间
    if (diffMinutes < 1) {
      return '刚刚';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}分钟前`;
    } else if (diffHours < 24 && date.getDate() === now.getDate()) {
      return `${diffHours}小时前`;
    } else if (diffDays === 1) {
      return '昨天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    } else {
      // 超过7天，显示完整日期时间
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    }
  } catch (e) {
    return String(dateTime);
  }
};

/**
 * 翻译财务术语为中文
 * 
 * @param term - 英文财务术语
 * @returns 对应的中文翻译，如果没有匹配则返回原文
 */
export const translateFinancialTerm = (term: string): string => {
  if (!term) return term;
  
  const termMap: Record<string, string> = {
    // 基本财务指标
    'Date': '日期',
    'TotalRevenue': '总营收',
    'Revenue': '营业收入',
    'CostOfRevenue': '营业成本',
    'Cost Of Revenue': '营业成本',
    'GrossProfit': '毛利润',
    'Gross Profit': '毛利润',
    'OperatingIncome': '营业利润',
    'Operating Income': '营业利润',
    'NetIncome': '净利润',
    'Net Income': '净利润',
    'EBIT': '息税前利润',
    'EBITDA': '息税折旧摊销前利润',
    
    // 每股指标
    'BasicEPS': '基本每股收益',
    'Basic EPS': '基本每股收益',
    'DilutedEPS': '稀释每股收益',
    'Diluted EPS': '稀释每股收益',
    'BasicAverageShares': '基本平均股本',
    'Basic Average Shares': '基本平均股数',
    'DilutedAverageShares': '稀释平均股本',
    'Diluted Average Shares': '稀释平均股数',
    'DilutedNIAvailtoComStockholders': '稀释后归属于普通股股东的净利润',
    'Diluted NI Availto Com Stockholders': '稀释后归属于普通股股东的净利润',
    
    // 资产负债表
    'TotalAssets': '总资产',
    'Total Assets': '总资产',
    'TotalLiab': '总负债',
    'Total Liab': '总负债',
    'TotalStockholderEquity': '股东权益总额',
    'Total Stockholder Equity': '股东权益总额',
    'CurrentAssets': '流动资产',
    'Current Assets': '流动资产',
    'CurrentLiabilities': '流动负债',
    'Current Liabilities': '流动负债',
    'Cash': '现金',
    'CashAndCashEquivalents': '现金及现金等价物',
    'Cash And Cash Equivalents': '现金及现金等价物',
    'ShortTermInvestments': '短期投资',
    'Short Term Investments': '短期投资',
    'AccountsReceivable': '应收账款',
    'Accounts Receivable': '应收账款',
    'Inventory': '存货',
    'LongTermInvestments': '长期投资',
    'Long Term Investments': '长期投资',
    'PropertyPlantEquipment': '固定资产',
    'Property Plant Equipment': '固定资产',
    'GoodWill': '商誉',
    'Good Will': '商誉',
    'IntangibleAssets': '无形资产',
    'Intangible Assets': '无形资产',
    'LongTermDebt': '长期债务',
    'Long Term Debt': '长期债务',
    
    // 现金流量表
    'OperatingCashFlow': '经营现金流',
    'Operating Cash Flow': '经营活动现金流量',
    'CapitalExpenditure': '资本支出',
    'Capital Expenditure': '资本支出',
    'FreeCashFlow': '自由现金流',
    'Free Cash Flow': '自由现金流',
    'CashFlowFromOperatingActivities': '经营活动现金流',
    'Cash Flow From Operating Activities': '经营活动产生的现金流量',
    'CashFlowFromInvestingActivities': '投资活动现金流',
    'Cash Flow From Investing Activities': '投资活动产生的现金流量',
    'CashFlowFromFinancingActivities': '融资活动现金流',
    'Cash Flow From Financing Activities': '筹资活动产生的现金流量',
    'Cash Flow From Continuing Financing Activities': '持续筹资活动产生的现金流量',
    'NetChangeInCash': '现金净变化',
    'Net Change In Cash': '现金净变化',
    'Changes In Cash': '现金变动',
    'Changes In Cash And Cash Equivalents': '现金及现金等价物变动',
    'Change In Cash': '现金变动',
    'Change In Cash And Cash Equivalents': '现金及现金等价物变动',
    'End Cash Position': '期末现金余额',
    'Beginning Cash Position': '期初现金余额',
    'Financing Cash Flow': '筹资活动现金流量',
    'Investing Cash Flow': '投资活动现金流量',
    'Repurchase Of Capital Stock': '回购股本',
    'Repayment Of Debt': '偿还债务',
    'Issuance Of Debt': '发行债务',
    'Issuance Of Capital Stock': '发行股本',
    'Interest Paid Supplemental Data': '支付的利息（补充数据）',
    'Income Tax Paid Supplemental Data': '支付的所得税（补充数据）',
    'Net Other Financing Charges': '其他融资费用净额',
    'Cash Dividends Paid': '支付的现金股利',
    'Common Stock Dividend Paid': '普通股股利支付',
    'Net Common Stock Issuance': '普通股净发行',
    'Common Stock Payments': '普通股支付',
    'Common Stock Issuance': '普通股发行',
    'Net Issuance Payments Of Debt': '债务净发行支付',
    'Amortization Of Intangibles': '无形资产摊销',
    'Amortization Of Intangibles And Other': '无形资产及其他摊销',
    'Change In Account Payable': '应付账款变动',
    'Change In Accounts Payable': '应付账款变动',
    'Change In Accrued Expenses': '应计费用变动',
    'Change In Accrued Ex': '应计费用变动',
    'Change In Working Capital': '营运资金变动',
    'Change In Other Working Capital': '其他营运资金变动',
    'Change In Other Current Liabilities': '其他流动负债变动',
    'Change In Other Current Assets': '其他流动资产变动',
    'Change In Payables And Accrued Expense': '应付账款及应计费用变动',
    'Change In Payable': '应付账款变动',
    'Change In Inventory': '存货变动',
    'Change In Receivables': '应收账款变动',
    'Changes In Account Receivables': '应收账款变动',
    'Depreciation': '折旧',
    'Depreciation And Amortization': '折旧和摊销',
    'Depreciation Amortization Depletion': '折旧摊销和折耗',
    'Stock Based Compensation': '股票薪酬',
    'Net Borrowings': '净借款',
    'Net Income From Continuing Operations': '持续经营净利润',
    'Other Operating Cash Flow': '其他经营现金流',
    'Other Investing Cash Flow': '其他投资现金流',
    'Other Financing Cash Flow': '其他筹资现金流',
    'Other Non Cash Items': '其他非现金项目',
    'Deferred Tax': '递延税',
    'Deferred Income Tax': '递延所得税',
    'Net Short Term Debt Issuance': '短期债务净发行',
    'Net Long Term Debt Issuance': '长期债务净发行',
    'Long Term Debt Payments': '长期债务支付',
    'Long Term Debt Issuance': '长期债务发行',
    'Cash Flow From Continuing Investing Activities': '持续投资活动产生的现金流量',
    'Net Other Investing Changes': '其他投资变动净额',
    'Net Investment Purchase And Sale': '投资买卖净额',
    'Sale Of Investment': '出售投资',
    'Purchase Of Investment': '购买投资',
    'Net Business Purchase And Sale': '业务买卖净额',
    'Purchase Of Business': '购买业务',
    'Net PPE Purchase And Sale': '固定资产买卖净额',
    'Purchase Of PPE': '购买固定资产',
    
    // 其他常见字段
    'Interest': '利息',
    'InterestExpense': '利息支出',
    'Interest Expense': '利息支出',
    'InterestIncome': '利息收入',
    'Interest Income': '利息收入',
    'TaxProvision': '所得税',
    'Tax Provision': '所得税',
    'ResearchDevelopment': '研发费用',
    'Research Development': '研发费用',
    'SellingGeneralAdministrative': '销售及管理费用',
    'Selling General Administrative': '销售及管理费用',
    'TotalOperatingExpenses': '营业费用总额',
    'Total Operating Expenses': '营业费用总额',
    'IncomeBeforeTax': '税前利润',
    'Income Before Tax': '税前利润',
    'IncomeTaxExpense': '所得税费用',
    'Income Tax Expense': '所得税费用',
    'Net Income Common Stockholders': '归属于普通股股东的净利润',
  };
  
  // 精确匹配（优先）
  if (termMap[term]) {
    return termMap[term];
  }
  
  // 尝试去除空格和大小写差异的匹配
  const normalizedTerm = term.replace(/\s+/g, ' ').trim();
  if (termMap[normalizedTerm]) {
    return termMap[normalizedTerm];
  }
  
  // 部分匹配（仅在精确匹配失败时使用，且要求匹配度较高）
  const lowerTerm = term.toLowerCase().trim();
  let bestMatch: { key: string; value: string; score: number } | null = null;
  
  for (const [key, value] of Object.entries(termMap)) {
    const lowerKey = key.toLowerCase().trim();
    
    // 如果术语完全包含在键中，或键完全包含在术语中（长度相近）
    if (lowerTerm === lowerKey) {
      return value; // 完全匹配
    }
    
    // 避免短词匹配到长词（如 "Cash" 不应该匹配 "Free Cash Flow"）
    // 只有当较短的词长度 >= 较长词的 60% 时才进行匹配
    const minLen = Math.min(lowerTerm.length, lowerKey.length);
    const maxLen = Math.max(lowerTerm.length, lowerKey.length);
    
    // 如果短词太短（少于5个字符），要求更高的匹配度
    if (minLen < 5 && maxLen > minLen * 2) {
      continue; // 跳过这种不匹配的情况
    }
    
    // 计算匹配度
    if (lowerTerm.includes(lowerKey) || lowerKey.includes(lowerTerm)) {
      const score = minLen / maxLen;
      
      // 只接受匹配度较高的结果
      // 对于短词（<5字符），要求匹配度 > 0.8
      // 对于长词（>=5字符），要求匹配度 > 0.6
      const threshold = minLen < 5 ? 0.8 : 0.6;
      
      if (score > threshold && (!bestMatch || score > bestMatch.score)) {
        bestMatch = { key, value, score };
      }
    }
  }
  
  // 如果找到较好的匹配，返回它
  if (bestMatch) {
    return bestMatch.value;
  }
  
  // 如果都不匹配，返回原值
  return term;
};

/**
 * 翻译股票评级为中文
 * 
 * @param rating - 英文评级字符串
 * @returns 对应的中文评级，如果没有匹配则返回原文
 */
export const translateRating = (rating: string | undefined | null): string => {
  if (!rating) return '-';
  
  const lower = rating.toLowerCase().trim();
  
  // 常见评级翻译映射
  const ratingMap: Record<string, string> = {
    // 买入类
    'strong buy': '强烈买入',
    'buy': '买入',
    'outperform': '跑赢大市',
    'overweight': '增持',
    'positive': '正面',
    'accumulate': '累积',
    'add': '加仓',
    
    // 持有类
    'hold': '持有',
    'neutral': '中性',
    'equal weight': '等权重',
    'market perform': '与大市同步',
    'sector perform': '与行业同步',
    'in-line': '符合预期',
    
    // 卖出类
    'underweight': '减持',
    'underperform': '跑输大市',
    'sell': '卖出',
    'strong sell': '强烈卖出',
    'reduce': '减仓',
    'negative': '负面',
  };
  
  // 精确匹配
  if (ratingMap[lower]) {
    return ratingMap[lower];
  }
  
  // 部分匹配
  for (const [key, value] of Object.entries(ratingMap)) {
    if (lower.includes(key) || key.includes(lower)) {
      return value;
    }
  }
  
  // 如果都不匹配，返回原值
  return rating;
};

/**
 * 获取RSI状态
 * 
 * @param rsi - RSI指标值
 * @returns 包含颜色和文本的状态对象
 */
export const getRSIStatus = (rsi: number | undefined): { color: string; text: string } => {
  if (!rsi) return { color: 'default', text: '中性' };
  if (rsi < 30) return { color: 'success', text: '超卖' };
  if (rsi > 70) return { color: 'error', text: '超买' };
  return { color: 'default', text: '中性' };
};

/**
 * 翻译交易操作类型
 * 
 * @param action - 交易操作类型（如 "upgrade", "downgrade", "init" 等）
 * @returns 对应的中文翻译
 */
export const translateAction = (action: string | undefined | null): string => {
  if (!action) return '-';
  
  const lower = action.toLowerCase().trim();
  
  const actionMap: Record<string, string> = {
    // 评级变化
    'up': '上调',
    'upgrade': '上调',
    'upgraded': '上调',
    'down': '下调',
    'downgrade': '下调',
    'downgraded': '下调',
    'init': '新评级',
    'initiate': '新评级',
    'initiated': '新评级',
    'maintain': '维持',
    'maintained': '维持',
    'main': '维持',
    'reiterate': '重申',
    'reiterated': '重申',
    'no change': '无变化',
    'unchanged': '无变化',
    
    // 交易类型
    'buy': '买入',
    'purchase': '购买',
    'sell': '卖出',
    'sale': '出售',
    'hold': '持有',
    
    // 其他
    'change': '变化',
    '変化': '变化', // 日语
    'reit': 'REIT', // 房地产投资信托基金
  };
  
  // 精确匹配
  if (actionMap[lower]) {
    return actionMap[lower];
  }
  
  // 部分匹配
  for (const [key, value] of Object.entries(actionMap)) {
    if (lower.includes(key) || key.includes(lower)) {
      return value;
    }
  }
  
  // 如果都不匹配，返回原值
  return action;
};

/**
 * 状态映射配置
 */
export const statusMaps = {
  trend: {
    'up': { color: 'success', text: '上涨' },
    'down': { color: 'error', text: '下跌' },
    'neutral': { color: 'default', text: '震荡' },
  },
  consensus: {
    '1': { text: '强烈买入', color: 'success' },
    '2': { text: '买入', color: 'success' },
    '3': { text: '持有', color: 'default' },
    '4': { text: '卖出', color: 'error' },
    '5': { text: '强烈卖出', color: 'error' },
  },
};
