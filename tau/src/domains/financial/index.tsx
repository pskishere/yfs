import { registry } from '../../framework/core/registry';
import { FinancialDetailView } from './components/FinancialDetailView';
import { LineChartOutlined, FundOutlined, HistoryOutlined } from '@ant-design/icons';

export const FinancialModule = {
  init: () => {
    // Register the main view for different modules
    registry.registerComponent('chart', FinancialDetailView, {
      title: 'K线图表',
      icon: <LineChartOutlined />
    });
    
    registry.registerComponent('options', FinancialDetailView, {
      title: '期权链',
      icon: <FundOutlined />
    });

    registry.registerComponent('cycle', FinancialDetailView, {
      title: '周期分析',
      icon: <HistoryOutlined />
    });
    
    // Chinese aliases
    registry.registerComponent('图表', FinancialDetailView, {
      title: 'K线图表',
      icon: <LineChartOutlined />
    });
    registry.registerComponent('k线', FinancialDetailView, {
      title: 'K线图表',
      icon: <LineChartOutlined />
    });
    registry.registerComponent('期权', FinancialDetailView, {
      title: '期权链',
      icon: <FundOutlined />
    });
    registry.registerComponent('周期', FinancialDetailView, {
      title: '周期分析',
      icon: <HistoryOutlined />
    });

    // Register suggestions
    const suggestions = [
      { label: 'K线图表', value: 'K线图表' },
      { label: '新闻资讯', value: '新闻资讯' },
      { label: '技术指标', value: '技术指标' },
      { label: '周期分析', value: '周期分析' },
      { label: '期权链', value: '期权链' },
      { label: '基本面', value: '基本面' },
    ];

    suggestions.forEach(s => registry.registerSuggestion(s));
  }
};
