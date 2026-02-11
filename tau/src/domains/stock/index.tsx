import { registry } from '../../framework/core/registry';
import { StockDetailView } from './components/StockDetailView';
import { LineChartOutlined, FundOutlined, HistoryOutlined, ReadOutlined, RadarChartOutlined } from '@ant-design/icons';

export const StockModule = {
  init: () => {
    // Register the main view for different modules
    registry.registerComponent('chart', StockDetailView, {
      title: 'K线图表',
      icon: <LineChartOutlined />
    });
    
    registry.registerComponent('options', StockDetailView, {
      title: '期权链',
      icon: <FundOutlined />
    });

    registry.registerComponent('cycle', StockDetailView, {
      title: '周期分析',
      icon: <HistoryOutlined />
    });

    registry.registerComponent('news', StockDetailView, {
      title: '新闻资讯',
      icon: <ReadOutlined />
    });

    registry.registerComponent('technical', StockDetailView, {
      title: '技术指标',
      icon: <RadarChartOutlined />
    });
    
    // Chinese aliases
    registry.registerComponent('图表', StockDetailView, {
      title: 'K线图表',
      icon: <LineChartOutlined />
    });
    registry.registerComponent('k线', StockDetailView, {
      title: 'K线图表',
      icon: <LineChartOutlined />
    });
    registry.registerComponent('期权', StockDetailView, {
      title: '期权链',
      icon: <FundOutlined />
    });
    registry.registerComponent('周期', StockDetailView, {
      title: '周期分析',
      icon: <HistoryOutlined />
    });
    registry.registerComponent('新闻', StockDetailView, {
      title: '新闻资讯',
      icon: <ReadOutlined />
    });
    registry.registerComponent('指标', StockDetailView, {
      title: '技术指标',
      icon: <RadarChartOutlined />
    });
    registry.registerComponent('技术', StockDetailView, {
      title: '技术指标',
      icon: <RadarChartOutlined />
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
