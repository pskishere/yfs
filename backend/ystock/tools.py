"""
股票分析 Agent 工具模块
定义供 AI Agent 调用的各种股票数据获取工具
"""
import logging
import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from django.utils import timezone

from .models import StockAnalysis, ChatSession
from .services import perform_analysis
from .yfinance import get_stock_info, get_news, search_symbols, get_options

logger = logging.getLogger(__name__)

def _get_or_fetch_analysis(symbol: str, duration: str = "5y", bar_size: str = "1 day") -> Optional[StockAnalysis]:
    """
    获取现有的分析记录，如果没有或已过期，则执行新分析
    """
    symbol = symbol.upper().strip()
    try:
        # 查找最新的成功记录
        analysis = StockAnalysis.objects.filter(
            symbol=symbol,
            status=StockAnalysis.Status.SUCCESS
        ).order_by('-updated_at').first()
        
        # 如果没有记录，或者记录是昨天的（简单判断），则执行新分析
        if not analysis or (timezone.now() - analysis.updated_at).total_seconds() > 3600 * 4: # 4小时过期
            logger.info(f"为 Tool 调用触发新分析: {symbol}")
            payload, error = perform_analysis(symbol, duration, bar_size, use_cache=False)
            if not error:
                analysis, _ = StockAnalysis.objects.get_or_create(
                    symbol=symbol, duration=duration, bar_size=bar_size
                )
                analysis.mark_success(payload)
                return analysis
            else:
                logger.error(f"Tool 调用触发分析失败: {symbol}, {error}")
                return analysis # 返回旧的，总比没有强
        
        return analysis
    except Exception as e:
        logger.error(f"获取分析记录失败: {symbol}, {e}")
        return None

@tool
def get_technical_indicators(symbol: str) -> str:
    """
    获取股票的技术指标分析数据，包括移动平均线(MA)、RSI、MACD、布林带、KDJ、趋势强度等。
    当用户询问股票走势、买卖点、技术面情况时使用。
    """
    analysis = _get_or_fetch_analysis(symbol)
    if not analysis or not analysis.indicators:
        return f"未能获取到 {symbol} 的技术指标数据。"
    
    ind = analysis.indicators
    result = [
        f"### {symbol} 技术指标摘要",
        f"- 当前价格: {ind.get('current_price', 'N/A')}",
        f"- 价格变动: {ind.get('price_change_pct', 0):.2f}%",
        f"- 趋势方向: {ind.get('trend_direction', '未知')}",
        f"- 趋势强度: {ind.get('trend_strength', 0):.1f}%",
        f"- RSI(14): {ind.get('rsi', 'N/A')}",
        f"- MACD: {ind.get('macd', 0):.4f} (信号线: {ind.get('macd_signal', 0):.4f})",
        f"- MA组合: MA5={ind.get('ma5', 'N/A')}, MA20={ind.get('ma20', 'N/A')}, MA50={ind.get('ma50', 'N/A')}, MA200={ind.get('ma200', 'N/A')}",
        f"- 布林带: 上轨={ind.get('bb_upper', 'N/A')}, 中轨={ind.get('bb_middle', 'N/A')}, 下轨={ind.get('bb_lower', 'N/A')}",
        f"- 支撑位: {ind.get('support_levels', [])}",
        f"- 阻力位: {ind.get('resistance_levels', [])}"
    ]
    return "\n".join(result)

@tool
def get_stock_news(symbol: str) -> str:
    """
    获取股票的最新相关新闻报道。
    当用户询问公司近况、重大事件、新闻面影响时使用。
    """
    # 优先尝试从最新的分析记录获取
    analysis = StockAnalysis.objects.filter(symbol=symbol.upper()).order_by('-updated_at').first()
    news_data = []
    
    if analysis and analysis.indicators and 'news_data' in analysis.indicators:
        news_data = analysis.indicators['news_data']
    
    # 如果分析记录里没新闻，或者新闻太旧，直接去取新鲜的
    if not news_data:
        news_data = get_news(symbol)
        
    if not news_data:
        return f"未能获取到 {symbol} 的最新新闻。"
    
    result = [f"### {symbol} 最新新闻"]
    for item in news_data[:10]: # 返回前10条
        title = item.get('title', '无标题')
        publisher = item.get('publisher', '未知来源')
        pub_time = item.get('provider_publish_time_fmt', '')
        time_str = f" [{pub_time}]" if pub_time else ""
        result.append(f"- **{title}** ({publisher}){time_str}")
        
    return "\n".join(result)

@tool
def get_fundamental_data(symbol: str) -> str:
    """
    获取股票的基本面数据，包括市值、市盈率(P/E)、每股收益(EPS)、公司简介等。
    当用户询问公司价值、财务状况、基本面表现时使用。
    """
    analysis = _get_or_fetch_analysis(symbol)
    if not analysis or not analysis.indicators or 'fundamental_data' not in analysis.indicators:
        # 尝试直接获取
        info = get_stock_info(symbol)
        if not info:
            return f"未能获取到 {symbol} 的基本面数据。"
        fundamental = info
    else:
        fundamental = analysis.indicators['fundamental_data']
        
    if not fundamental:
        return f"未能获取到 {symbol} 的基本面数据。"
        
    result = [f"### {symbol} 基本面数据"]
    
    # 提取常用字段
    fields = {
        'longName': '公司全称',
        'marketCap': '市值',
        'trailingPE': '滚动市盈率 (PE)',
        'forwardPE': '预测市盈率',
        'trailingEps': '每股收益 (EPS)',
        'dividendYield': '股息率',
        'fiftyTwoWeekHigh': '52周最高',
        'fiftyTwoWeekLow': '52周最低',
        'averageVolume': '平均成交量'
    }
    
    for key, label in fields.items():
        val = fundamental.get(key)
        if val is not None:
            if 'marketCap' in key or 'Volume' in key:
                # 格式化大数字
                if val >= 1e12: result.append(f"- {label}: {val/1e12:.2f}T")
                elif val >= 1e9: result.append(f"- {label}: {val/1e9:.2f}B")
                elif val >= 1e6: result.append(f"- {label}: {val/1e6:.2f}M")
                else: result.append(f"- {label}: {val}")
            elif 'Yield' in key:
                result.append(f"- {label}: {val*100:.2f}%")
            else:
                result.append(f"- {label}: {val}")
                
    if 'longBusinessSummary' in fundamental:
        summary = fundamental['longBusinessSummary']
        result.append(f"\n**公司业务摘要**: {summary[:300]}...")
        
    return "\n".join(result)

@tool
def get_cycle_analysis(symbol: str) -> str:
    """
    获取股票的周期分析数据，包括主周期长度、周期强度、周期规律以及季节性表现。
    当用户询问长线趋势、周期规律、时间拐点时使用。
    """
    analysis = _get_or_fetch_analysis(symbol)
    if not analysis or not analysis.indicators:
        return f"未能获取到 {symbol} 的周期分析数据。"
        
    ind = analysis.indicators
    result = [f"### {symbol} 周期分析报告"]
    
    # 1. 核心周期指标
    dominant_cycle = ind.get('dominant_cycle')
    if dominant_cycle:
        strength = ind.get('cycle_strength', 0) * 100
        quality = ind.get('cycle_quality', '未知')
        result.append(f"- **主周期**: {dominant_cycle:.1f} 天")
        result.append(f"- **周期强度**: {strength:.1f}% (质量: {quality})")
    
    # 2. 周期状态与预测
    status = ind.get('cycle_status')
    if status:
        prediction = ind.get('cycle_prediction', '中性')
        next_point = ind.get('next_turning_point', '未知')
        result.append(f"- **当前状态**: {status}")
        result.append(f"- **预测方向**: {prediction}")
        result.append(f"- **下个拐点**: {next_point}")

    # 3. 周期总结
    summary = ind.get('cycle_summary')
    if summary:
        result.append(f"- **周期总结**: {summary}")
        
    # 4. 季节性规律 (简略版)
    yearly = ind.get('yearly_cycles', [])
    if yearly:
        result.append("\n**年度历史表现 (最近3年):**")
        for y in sorted(yearly, key=lambda x: x.get('year', 0), reverse=True)[:3]:
            change = y.get('first_to_last_change', 0)
            result.append(f"- {y.get('year')}年: 涨幅 {change:.2f}% (交易日: {y.get('trading_days')}天)")
            
    monthly = ind.get('monthly_cycles', [])
    if monthly:
        result.append("\n**最近月度表现:**")
        for m in sorted(monthly, key=lambda x: x.get('month', ''), reverse=True)[:3]:
            change = m.get('first_to_last_change', 0)
            result.append(f"- {m.get('month')}: 涨幅 {change:.2f}%")
            
    return "\n".join(result)

@tool
def search_stock_symbol(query: str) -> str:
    """
    通过公司名称或关键词搜索股票代码。
    当用户提到公司名字但没有提供代码，或者你不知道具体代码时使用。
    """
    results = search_symbols(query)
    if not results:
        return f"未找到与 '{query}' 相关的股票代码。"
    
    result = [f"### '{query}' 的搜索结果"]
    for item in results:
        result.append(f"- **{item['symbol']}**: {item['name']} ({item['exchange']}, {item['type']})")
        
    return "\n".join(result)

@tool
def get_options_data(symbol: str) -> str:
    """
    获取股票的期权链数据，包括不同到期日的看涨(Calls)和看跌(Puts)期权的行权价、最新价、隐含波动率等。
    当用户询问期权情况、市场情绪（如 Put/Call Ratio 隐含信息）、波动率预期时使用。
    """
    options = get_options(symbol)
    if not options or not options.get('expiration_dates'):
        return f"未能获取到 {symbol} 的期权数据。该证券可能没有期权交易。"
    
    exp_dates = options['expiration_dates']
    chains = options.get('chains', {})
    
    result = [f"### {symbol} 期权数据摘要"]
    result.append(f"- 可用到期日: {', '.join(exp_dates[:5])}{'...' if len(exp_dates) > 5 else ''}")
    
    # 取最近一个到期日的数据做简要展示
    if exp_dates:
        first_date = exp_dates[0]
        chain = chains.get(first_date)
        if chain:
            calls = chain.get('calls', [])
            puts = chain.get('puts', [])
            
            result.append(f"\n**最近到期日 ({first_date}) 概览:**")
            result.append(f"- 看涨期权 (Calls) 数量: {len(calls)}")
            result.append(f"- 看跌期权 (Puts) 数量: {len(puts)}")
            
            # 计算简单的平值期权信息（假设当前价在行权价附近）
            if calls and puts:
                # 按行权价排序
                calls_sorted = sorted(calls, key=lambda x: x.get('strike', 0))
                # 简单展示中间几个行权价
                mid_idx = len(calls_sorted) // 2
                display_calls = calls_sorted[max(0, mid_idx-2):min(len(calls_sorted), mid_idx+3)]
                
                result.append("\n**部分行权价详情:**")
                result.append("| 行权价 | 类型 | 最新价 | 涨跌幅 | 隐含波动率 |")
                result.append("| --- | --- | --- | --- | --- |")
                for c in display_calls:
                    strike = c.get('strike')
                    # 寻找对应行权价的 put
                    p = next((x for x in puts if x.get('strike') == strike), None)
                    
                    result.append(f"| {strike} | Call | {c.get('lastPrice', 'N/A')} | {c.get('percentChange', 0):.2f}% | {c.get('impliedVolatility', 0)*100:.2f}% |")
                    if p:
                        result.append(f"| {strike} | Put | {p.get('lastPrice', 'N/A')} | {p.get('percentChange', 0):.2f}% | {p.get('impliedVolatility', 0)*100:.2f}% |")
    
    result.append("\n*注：以上仅显示部分数据，完整数据请查看期权分析面板。*")
    return "\n".join(result)

# 定义所有可用工具列表
STOCKS_TOOLS = [
    get_technical_indicators,
    get_stock_news,
    get_fundamental_data,
    get_cycle_analysis,
    get_options_data,
    search_stock_symbol
]
