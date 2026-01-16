/**
 * 基本面数据组件
 */
import React from 'react';
import { Collapse, Descriptions, Space, Tag, Tabs, Typography, Pagination } from 'antd';
import { 
  DatabaseOutlined, 
  FileTextOutlined,
} from '@ant-design/icons';
import type { AnalysisResult } from '../types/index';
import { formatValue, formatLargeNumber, statusMaps } from '../utils/formatters';
import { FinancialTable } from './FinancialTable';

interface FundamentalDataProps {
  analysisResult: AnalysisResult;
  currencySymbol: string;
  createIndicatorLabel: (label: string, indicatorKey: string) => React.ReactNode;
}

/**
 * 基本面数据组件
 */
export const FundamentalData: React.FC<FundamentalDataProps> = ({
  analysisResult,
  currencySymbol,
  createIndicatorLabel,
}) => {
  const formatCurrency = (value?: number, decimals: number = 2) =>
    `${currencySymbol}${formatValue(value ?? 0, decimals)}`;

  const fd = analysisResult.indicators.fundamental_data;

  // 检查是否有基本面数据
  if (!fd || typeof fd !== 'object' || fd.raw_xml || Object.keys(fd).length === 0) {
    return null;
  }

  const renderFundamentalItems = () => {
    const items = [];

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
  };

  // 检查是否有详细财务报表
  const hasFinancialStatements = fd.Financials || fd.QuarterlyFinancials || fd.BalanceSheet || fd.Cashflow;

  const collapseItems = [
    {
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
          items={renderFundamentalItems()}
        />
      ),
    },
  ];

  // 添加详细财务报表
  if (hasFinancialStatements) {
    const tabItems = [];

    if (fd.Financials && Array.isArray(fd.Financials) && fd.Financials.length > 0) {
      tabItems.push({
        key: 'annual-financials',
        label: '年度财务报表',
        children: <FinancialTable data={fd.Financials} currencySymbol={currencySymbol} />,
      });
    }

    if (fd.QuarterlyFinancials && Array.isArray(fd.QuarterlyFinancials) && fd.QuarterlyFinancials.length > 0) {
      tabItems.push({
        key: 'quarterly-financials',
        label: '季度财务报表',
        children: <FinancialTable data={fd.QuarterlyFinancials} currencySymbol={currencySymbol} />,
      });
    }

    if (fd.BalanceSheet && Array.isArray(fd.BalanceSheet) && fd.BalanceSheet.length > 0) {
      tabItems.push({
        key: 'balance-sheet',
        label: '资产负债表',
        children: <FinancialTable data={fd.BalanceSheet} currencySymbol={currencySymbol} />,
      });
    }

    if (fd.Cashflow && Array.isArray(fd.Cashflow) && fd.Cashflow.length > 0) {
      tabItems.push({
        key: 'cashflow',
        label: '现金流量表',
        children: <FinancialTable data={fd.Cashflow} currencySymbol={currencySymbol} />,
      });
    }

    if (tabItems.length > 0) {
      collapseItems.push({
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
            items={tabItems}
          />
        ),
      });
    }
  }

  return (
    <div id="section-fundamental">
      <Collapse
        ghost
        defaultActiveKey={['fundamental']}
        items={collapseItems}
        style={{ marginTop: 0 }}
      />
    </div>
  );
};
