"""
股票分析 Agent 工具模块
定义供 AI Agent 调用的各种股票数据获取工具
"""
import logging
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

from .services import perform_analysis, get_cached_news
from .yfinance import get_stock_info, search_symbols, get_options_chain, get_holders, get_financials, crawl_news_article
from ai.tools import load_document

logger = logging.getLogger(__name__)

def _get_or_fetch_analysis(symbol: str, duration: str = "5y", bar_size: str = "1 day") -> Optional[Dict[str, Any]]:
    """
    获取分析结果
    """
    symbol = symbol.upper().strip()
    try:
        # 直接调用服务层，利用其内部的 StockKLine 缓存机制
        result, error = perform_analysis(symbol, duration, bar_size)
        
        if error or not result:
            logger.error(f"Tool 调用获取分析失败: {symbol}, {error}")
            return None
            
        return result
    except Exception as e:
        logger.error(f"获取分析结果失败: {symbol}, {e}")
        return None

def _format_technical_data(analysis: Dict[str, Any], symbol: str) -> str:
    if not analysis or 'indicators' not in analysis:
        return ""
    
    ind = analysis['indicators']
    result = [
        f"### {symbol} 技术指标详情",
        f"- **价格信息**: 当前价 {ind.get('current_price', 'N/A')}, 变动 {ind.get('price_change_pct', 0):.2f}%",
        f"- **趋势概览**: 方向 {ind.get('trend_direction', '未知')}, 强度 {ind.get('trend_strength', 0):.1f}%",
        f"- **移动平均线**: MA5={ind.get('ma5', 'N/A')}, MA20={ind.get('ma20', 'N/A')}, MA50={ind.get('ma50', 'N/A')}, MA200={ind.get('ma200', 'N/A')}",
        f"- **布林带**: 上轨={ind.get('bb_upper', 'N/A')}, 中轨={ind.get('bb_middle', 'N/A')}, 下轨={ind.get('bb_lower', 'N/A')}",
        f"- **动量指标**:",
        f"  - RSI(14): {ind.get('rsi', 'N/A')} ({'超买' if ind.get('rsi', 50) > 70 else '超卖' if ind.get('rsi', 50) < 30 else '中性'})",
        f"  - MACD: {ind.get('macd', 0):.4f} (信号线: {ind.get('macd_signal', 0):.4f}, 柱状图: {ind.get('macd_histogram', 0):.4f})",
        f"  - KDJ: K={ind.get('k_line', 'N/A')}, D={ind.get('d_line', 'N/A')}, J={ind.get('j_line', 'N/A')}",
        f"- **趋势/波动指标**:",
        f"  - VWAP: {ind.get('vwap', 'N/A')}",
        f"  - ADX: {ind.get('adx', 'N/A')} (强度: {ind.get('adx_strength', '未知')})",
        f"  - SuperTrend: {ind.get('supertrend_direction', '未知')}",
        f"  - ATR (14): {ind.get('atr', 'N/A')} (波动率: {ind.get('atr_percent', 0):.2f}%)",
        f"- **关键位置**:",
        f"  - 支撑位: {', '.join(map(str, ind.get('support_levels', [])))}",
        f"  - 阻力位: {', '.join(map(str, ind.get('resistance_levels', [])))}",
        f"  - 枢轴点 (Pivot): {ind.get('pivot_p', 'N/A')} (S1:{ind.get('pivot_s1', 'N/A')}, R1:{ind.get('pivot_r1', 'N/A')})"
    ]
    return "\n".join(result)

def _format_stock_news(symbol: str, news_data: List[Dict[str, Any]] = None) -> str:
    if not news_data:
        # 尝试直接获取
        news_data = get_cached_news(symbol)
        
    if not news_data:
        return ""
    
    result = [f"### {symbol} 详细新闻资讯"]
    for item in news_data[:50]: # 尽可能提供更多新闻，增加到最多50条
        title = item.get('title', '无标题')
        publisher = item.get('publisher', '未知来源')
        link = item.get('link', '')
        # 优先使用已经格式化好的日期
        time_str = item.get('provider_publish_time_fmt', '')
        if not time_str:
            time_str = item.get('provider_publish_time', '')
        
        time_display = f" ({time_str})" if time_str else ""
        
        if link:
            news_entry = [f"- **[{title}]({link})**{time_display} - *{publisher}*"]
        else:
            news_entry = [f"- **{title}**{time_display} - *{publisher}*"]
            
        related = item.get('related_tickers', [])
        if related:
            news_entry.append(f"  *相关板块/股票: {', '.join(related[:5])}*")
            
        result.append("\n".join(news_entry))
        
    return "\n".join(result)

def _format_fundamental_data(analysis: Dict[str, Any], symbol: str) -> str:
    if not analysis or not analysis.get('indicators') or 'fundamental_data' not in analysis['indicators']:
        # 尝试直接获取
        info = get_stock_info(symbol)
        if not info:
            return ""
        fundamental = info
    else:
        fundamental = analysis['indicators']['fundamental_data']
        
    if not fundamental:
        return ""
        
    result = [f"### {symbol} 基本面数据"]
    
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
                if val >= 1e12: result.append(f"- {label}: {val/1e12:.2f}T")
                elif val >= 1e9: result.append(f"- {label}: {val/1e9:.2f}B")
                elif val >= 1e6: result.append(f"- {label}: {val/1e6:.2f}M")
                else: result.append(f"- {label}: {val}")
            elif 'Yield' in key:
                result.append(f"- {label}: {val*100:.2f}%")
            else:
                result.append(f"- {label}: {val}")
    
    # 增加分析师评级和目标价
    if 'targetMeanPrice' in fundamental or 'recommendationKey' in fundamental:
        result.append("\n**分析师评级与目标价**:")
        if fundamental.get('targetMeanPrice'):
            result.append(f"- 平均目标价: {fundamental.get('targetMeanPrice')} (高: {fundamental.get('targetHighPrice')}, 低: {fundamental.get('targetLowPrice')})")
        if fundamental.get('recommendationKey'):
            result.append(f"- 综合建议: {fundamental.get('recommendationKey').upper()} (基于 {fundamental.get('numberOfAnalystOpinions', 0)} 名分析师)")

    if 'longBusinessSummary' in fundamental:
        summary = fundamental['longBusinessSummary']
        result.append(f"\n**公司业务摘要**: {summary[:1000]}...") # 提供更详尽的业务描述
        
    return "\n".join(result)

def _format_holders_data(symbol: str) -> str:
    holders = get_holders(symbol)
    if not holders:
        return ""
    
    result = [f"### {symbol} 持股结构分析"]
    
    major = holders.get('major_holders', {})
    if major:
        # yfinance 返回的 major_holders 通常是一个字典
        # 0: 比例, 1: 描述
        # 例如: {0: {0: '0.13%', 1: '12.84%', ...}, 1: {0: '% of Shares Held by All Insider', ...}}
        try:
            # 尝试转换成更易读的格式
            rows = []
            for i in range(len(major.get(0, {}))):
                pct = major[0].get(i)
                desc = major[1].get(i)
                if pct and desc:
                    rows.append(f"- {desc}: {pct}")
            if rows:
                result.append("**主要持股概览**:")
                result.extend(rows)
        except Exception:
            pass

    inst = holders.get('institutional_holders', [])
    if inst:
        result.append("\n**前五大机构股东**:")
        for item in inst[:5]:
            holder = item.get('Holder', '未知')
            pct = item.get('pctHeld', 0)
            shares = item.get('Shares', 0)
            if shares > 1e6: shares_str = f"{shares/1e6:.1f}M"
            else: shares_str = f"{shares}"
            result.append(f"- {holder}: 持股 {shares_str} ({pct*100:.2f}%)")
            
    return "\n".join(result) if len(result) > 1 else ""

def _format_upcoming_events(fundamental: Dict[str, Any], symbol: str) -> str:
    result = [f"### {symbol} 分红与重要事件"]
    
    # 分红信息
    has_data = False
    if fundamental.get('dividendRate') or fundamental.get('trailingAnnualDividendYield'):
        has_data = True
        result.append("**分红信息**:")
        result.append(f"- 股息率: {fundamental.get('trailingAnnualDividendYield', 0)*100:.2f}%")
        result.append(f"- 每股股息: {fundamental.get('dividendRate', 'N/A')}")
        if fundamental.get('exDividendDate'):
            try:
                dt = datetime.fromtimestamp(fundamental.get('exDividendDate'))
                result.append(f"- 除权日: {dt.strftime('%Y-%m-%d')}")
            except: pass

    # 财报日
    calendar = fundamental.get('calendarEvents', {})
    earnings = calendar.get('earnings', {})
    if earnings:
        has_data = True
        earnings_date = earnings.get('earningsDate', [])
        if earnings_date:
            result.append("\n**下期财报预测**:")
            dates = []
            for d in earnings_date:
                try:
                    dt = datetime.fromtimestamp(d)
                    dates.append(dt.strftime('%Y-%m-%d'))
                except: pass
            if dates:
                result.append(f"- 预计日期: {' 至 '.join(dates)}")
    
    return "\n".join(result) if has_data else ""

def _format_financial_summary(symbol: str) -> str:
    fins = get_financials(symbol)
    if not fins:
        return ""
    
    result = [f"### {symbol} 财务报表摘要 (最新)"]
    
    # 提取利润表关键项
    income = fins.get('income_stmt', {})
    if income:
        try:
            # yfinance 返回的字典键通常是 Timestamp，我们需要找最近的一个
            latest_date = sorted(income.keys(), reverse=True)[0]
            data = income[latest_date]
            result.append("**利润表亮点**:")
            
            mapping = {
                'Total Revenue': '总营收',
                'Net Income': '净利润',
                'EBITDA': 'EBITDA',
                'Gross Profit': '毛利润'
            }
            for k, label in mapping.items():
                val = data.get(k)
                if val is not None:
                    if abs(val) >= 1e12: v_str = f"{val/1e12:.2f}T"
                    elif abs(val) >= 1e9: v_str = f"{val/1e9:.2f}B"
                    elif abs(val) >= 1e6: v_str = f"{val/1e6:.2f}M"
                    else: v_str = f"{val}"
                    result.append(f"- {label}: {v_str}")
        except: pass

    # 提取资产负债表关键项
    balance = fins.get('balance_sheet', {})
    if balance:
        try:
            latest_date = sorted(balance.keys(), reverse=True)[0]
            data = balance[latest_date]
            result.append("\n**资产负债表亮点**:")
            mapping = {
                'Total Assets': '总资产',
                'Total Liabilities Net Minority Interest': '总负债',
                'Total Equity Gross Minority Interest': '总权益',
                'Cash And Cash Equivalents': '现金储备'
            }
            for k, label in mapping.items():
                val = data.get(k)
                if val is not None:
                    if abs(val) >= 1e12: v_str = f"{val/1e12:.2f}T"
                    elif abs(val) >= 1e9: v_str = f"{val/1e9:.2f}B"
                    elif abs(val) >= 1e6: v_str = f"{val/1e6:.2f}M"
                    else: v_str = f"{val}"
                    result.append(f"- {label}: {v_str}")
        except: pass

    return "\n".join(result) if len(result) > 1 else ""

def _format_cycle_analysis(analysis: Dict[str, Any], symbol: str, full: bool = False) -> str:
    if not analysis or not analysis.get('indicators'):
        return ""
        
    ind = analysis['indicators']
    result = [f"### {symbol} 周期分析报告"]
    
    dominant_cycle = ind.get('dominant_cycle')
    if dominant_cycle:
        strength = ind.get('cycle_strength', 0) * 100
        quality = ind.get('cycle_quality', '未知')
        result.append(f"- **主周期**: {dominant_cycle:.1f} 天")
        result.append(f"- **周期强度**: {strength:.1f}% (质量: {quality})")
    
    status = ind.get('cycle_status')
    if status:
        prediction = ind.get('cycle_prediction', '中性')
        next_point = ind.get('next_turning_point', '未知')
        result.append(f"- **当前状态**: {status}")
        result.append(f"- **预测方向**: {prediction}")
        result.append(f"- **下个拐点**: {next_point}")

    summary = ind.get('cycle_summary')
    if summary:
        result.append(f"- **周期总结**: {summary}")

    if full:
        yearly = ind.get('yearly_cycles', [])
        if yearly:
            result.append("\n**年度历史表现 (最近5年):**")
            for y in sorted(yearly, key=lambda x: x.get('year', 0), reverse=True)[:5]:
                change = y.get('first_to_last_change', 0)
                result.append(f"- {y.get('year')}年: 涨幅 {change:.2f}% (交易日: {y.get('trading_days')}天)")
                
        monthly = ind.get('monthly_cycles', [])
        if monthly:
            result.append("\n**最近月度表现 (最近6个月):**")
            for m in sorted(monthly, key=lambda x: x.get('month', ''), reverse=True)[:6]:
                change = m.get('first_to_last_change', 0)
                result.append(f"- {m.get('month')}: 涨幅 {change:.2f}%")
            
    return "\n".join(result)

def _format_options_data(symbol: str, options: Dict[str, Any] = None) -> str:
    if not options:
        try:
            options = get_options_chain(symbol)
        except Exception as e:
            logger.error(f"获取 {symbol} 期权链失败: {e}")
            return ""
        
    if not options or not options.get('expirations'):
        return ""
    
    exp_dates = options.get('expirations', [])
    current_expiry = options.get('current_expiry')
    calls = options.get('calls', [])
    puts = options.get('puts', [])
    
    result = [f"### {symbol} 期权深度分析"]
    result.append(f"- **可用到期日**: {', '.join(exp_dates[:10])}{'...' if len(exp_dates) > 10 else ''}")
    
    if not (calls or puts):
        result.append(f"\n*注意：虽然存在到期日 {exp_dates[:3]}，但未能提取到具体的 Call/Put 详细列表。请尝试使用 `internet_search` 查询异动。*")
        return "\n".join(result)

    result.append(f"\n**最近到期日 ({current_expiry}) 数据统计:**")
    
    # 计算看涨看跌比例 (Volume based)
    call_vol = sum(c.get('volume', 0) or 0 for c in calls)
    put_vol = sum(p.get('volume', 0) or 0 for p in puts)
    pc_ratio = put_vol / call_vol if call_vol > 0 else (0 if put_vol == 0 else float('inf'))
    
    result.append(f"- Call 总成交量: {call_vol:,}")
    result.append(f"- Put 总成交量: {put_vol:,}")
    
    pc_status = "中性"
    if pc_ratio > 1.2: pc_status = "看空情绪较浓"
    elif pc_ratio < 0.7: pc_status = "看多情绪较浓"
    
    pc_ratio_str = f"{pc_ratio:.2f}" if pc_ratio != float('inf') else "Inf"
    result.append(f"- **P/C Ratio (成交量)**: {pc_ratio_str} ({pc_status})")
    
    # 展示行权价详情
    # 合并所有行权价并去重排序
    all_strikes = sorted(list(set([c.get('strike') for c in calls if c.get('strike')] + [p.get('strike') for p in puts if p.get('strike')])))
    
    if all_strikes:
        # 简单估算平值 (ATM) 为中间位置
        mid_idx = len(all_strikes) // 2
        display_strikes = all_strikes[max(0, mid_idx-5):min(len(all_strikes), mid_idx+6)]
        
        result.append("\n**关键行权价详情:**")
        
        for strike in display_strikes:
            c = next((x for x in calls if x.get('strike') == strike), None)
            p = next((x for x in puts if x.get('strike') == strike), None)
            
            strike_info = [f"- **行权价 {strike}**"]
            if c:
                c_vol = c.get('volume', 0) or 0
                c_oi = c.get('openInterest', 0) or 0
                c_iv = c.get('impliedVolatility', 0) or 0
                c_price = c.get('lastPrice', 'N/A')
                c_change = c.get('percentChange', 0) or 0
                strike_info.append(f"  - **Call**: 价格 {c_price} ({c_change:.2f}%), 成交 {c_vol:,}, 未平仓 {c_oi:,}, IV {c_iv*100:.1f}%")
            
            if p:
                p_vol = p.get('volume', 0) or 0
                p_oi = p.get('openInterest', 0) or 0
                p_iv = p.get('impliedVolatility', 0) or 0
                p_price = p.get('lastPrice', 'N/A')
                p_change = p.get('percentChange', 0) or 0
                strike_info.append(f"  - **Put**: 价格 {p_price} ({p_change:.2f}%), 成交 {p_vol:,}, 未平仓 {p_oi:,}, IV {p_iv*100:.1f}%")
            
            result.append("\n".join(strike_info))
    
    result.append("\n*注：期权数据由 yfinance 提供，隐含波动率 (IV) 反映市场预期波动。*")
    return "\n".join(result)

@tool
def get_stock_data(symbol: str) -> str:
    """
    获取股票的综合分析数据。
    返回包含：
    1. 技术指标 (MA, RSI, MACD, KDJ, VWAP, 布林带等)
    2. 基本面 (市值、PE、盈余、分析师评级、目标价)
    3. 持股结构 (机构/内部人持股)
    4. 财务报表摘要 (营收、净利、现金流)
    5. 周期分析 (主周期、预测方向、拐点)
    6. 详细新闻列表 (包含链接，如需深入分析某篇新闻，请配合 get_news_detail 使用)
    7. 期权深度分析 (成交量分布、P/C Ratio、IV)
    """
    analysis = _get_or_fetch_analysis(symbol)
    if not analysis:
        return f"未能获取到 {symbol} 的数据。"
    
    sections = []
    
    # 1. 技术指标
    sections.append(_format_technical_data(analysis, symbol))
    
    # 2. 基本面 (包含分析师评级)
    fundamental = analysis.get('indicators', {}).get('fundamental_data')
    if not fundamental:
        info = get_stock_info(symbol)
        fundamental = info if info else {}
    
    sections.append(_format_fundamental_data(analysis, symbol))
    
    # 3. 持股结构 (新增)
    sections.append(_format_holders_data(symbol))
    
    # 4. 财务报表摘要 (新增)
    sections.append(_format_financial_summary(symbol))
    
    # 5. 分红与重要事件 (新增)
    sections.append(_format_upcoming_events(fundamental, symbol))
    
    # 6. 周期分析
    sections.append(_format_cycle_analysis(analysis, symbol, full=True))
    
    # 6. 新闻
    news_data = analysis.get('indicators', {}).get('news_data')
    news_content = _format_stock_news(symbol, news_data)
    sections.append(news_content)
    
    # 7. 期权 (摘要)
    sections.append(_format_options_data(symbol))
    
    # 过滤掉空部分并合并
    active_sections = [s for s in sections if s.strip()]
    if not active_sections:
        return f"未能获取到 {symbol} 的任何有效数据。"
        
    return "\n\n".join(active_sections)

@tool
def get_news_detail(url: str) -> str:
    """
    根据新闻链接抓取并分析新闻全文内容。
    当你需要深入了解某篇新闻的细节、背景或专家观点时使用。
    """
    detail = crawl_news_article(url)
    if not detail or not detail.get('text'):
        return f"无法获取链接 {url} 的新闻详情内容。"
    
    result = [
        f"### 新闻详情: {detail.get('title', '未知标题')}",
        f"- **发布时间**: {detail.get('publish_date', '未知')}",
        f"- **作者**: {', '.join(detail.get('authors', [])) if detail.get('authors') else '未知'}",
        f"\n**正文内容摘要**:\n{detail.get('summary') or detail.get('text')[:1000] + '...'}",
        f"\n**关键词**: {', '.join(detail.get('keywords', [])) if detail.get('keywords') else '无'}"
    ]
    
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
def internet_search(query: str) -> str:
    """
    使用搜索引擎（优先检索雅虎金融 Yahoo Finance）查询互联网上的实时信息。
    当需要获取最新的市场新闻、宏观经济数据、公司公告、行业动态时使用。
    """
    wrapper = DuckDuckGoSearchAPIWrapper(max_results=10)
    # 尝试使用不同的后端或配置
    search = DuckDuckGoSearchRun(api_wrapper=wrapper, name='DuckDuckGo搜索')
    
    # 尝试多种搜索策略
    search_queries = []
    
    # 策略 1: 原始查询 + 雅虎金融限制
    if "site:finance.yahoo.com" not in query:
        search_queries.append(f"{query} site:finance.yahoo.com")
    else:
        search_queries.append(query)
        
    # 策略 2: 原始查询 (去掉限制，增加成功率)
    clean_query = query.replace("site:finance.yahoo.com", "").strip()
    if clean_query:
        search_queries.append(clean_query)
        
    last_error = None
    for sq in search_queries:
        try:
            logger.info(f"正在尝试互联网搜索: {sq}")
            result = search.invoke(sq)
            if result and "No good DuckDuckGo Search Result" not in result:
                return result
        except Exception as e:
            last_error = str(e)
            logger.warning(f"搜索策略失败 ({sq}): {e}")
            continue
            
    if last_error:
        # 尝试返回一个稍微干净点的错误信息
        if "return None" in last_error and "bing.com" in last_error:
            return "当前搜索引擎服务繁忙或受限，请稍后再试，或尝试更简短的关键词。"
        return f"搜索遭遇错误: {last_error}"
    
    return "未能搜索到相关实时资讯，建议更换关键词重试。"

# 定义所有可用工具列表
STOCKS_TOOLS = [
    get_stock_data,
    search_stock_symbol,
    internet_search,
    load_document
]
