"""
股票分析 AI Agent 服务模块
集成 LangChain 和 Ollama，提供股票分析对话功能
"""
import os
import uuid
import logging
import re
from typing import Optional, Dict, Any, List
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

from .models import ChatSession, ChatMessage, StockAnalysis

logger = logging.getLogger(__name__)


class StockMemory:
    """
    基于 Django ORM 的股票分析对话记忆存储
    """
    def __init__(self, session_id: str):
        """
        初始化记忆存储
        
        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self.session, _ = ChatSession.objects.get_or_create(
            session_id=session_id
        )

    def save_context(self, inputs: Dict[str, str], outputs: Dict[str, str]):
        """
        保存对话上下文到数据库
        
        Args:
            inputs: 输入字典，包含用户消息
            outputs: 输出字典，包含 AI 回复
        """
        user_input = inputs.get('input', '')
        ai_output = outputs.get('response', '')
        
        # 保存用户消息（如果提供）
        if user_input:
            # 检查是否已经存在相同的用户消息（避免重复保存）
            existing = ChatMessage.objects.filter(
                session=self.session,
                role='user',
                content=user_input
            ).order_by('-created_at').first()
            
            if not existing:
                ChatMessage.objects.create(
                    session=self.session,
                    role='user',
                    content=user_input
                )
        
        # 保存助手回复
        if ai_output:
            ChatMessage.objects.create(
                session=self.session,
                role='assistant',
                content=ai_output
            )

    def load_memory_variables(self, inputs: Dict[str, str]) -> Dict[str, str]:
        """
        从数据库加载历史对话
        
        Args:
            inputs: 输入字典
            
        Returns:
            包含历史记录的字典
        """
        messages = ChatMessage.objects.filter(session=self.session).order_by('created_at')
        history = []
        
        for msg in messages:
            if msg.role == 'user':
                history.append(f"用户: {msg.content}")
            elif msg.role == 'assistant':
                history.append(f"助手: {msg.content}")
        
        return {'history': '\n'.join(history) if history else ''}

    def clear(self):
        """
        清空当前会话的记忆
        """
        ChatMessage.objects.filter(session=self.session).delete()


class StockAIAgent:
    """
    股票分析 AI Agent 服务类，提供对话和分析功能
    """
    def __init__(self, model_name: str = "deepseek-v3.2:cloud", base_url: Optional[str] = None):
        """
        初始化 AI Agent 服务
        
        Args:
            model_name: 使用的 Ollama 模型名称
            base_url: Ollama 服务的基础 URL
        """
        ollama_base_url = base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        ollama_base_url = ollama_base_url.rstrip('/')
        
        logger.info(f"初始化股票分析 AI Agent: model={model_name}, base_url={ollama_base_url}")
        
        self.model_name = model_name
        self.llm = ChatOllama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0.7,
        )
        
        # 创建股票分析专用提示模板
        self.prompt_template = PromptTemplate(
            input_variables=["stock_data", "input", "history"],
            template="""你是一个极度专业且资深的股票技术分析专家和市场策略师。你擅长通过复杂的技术指标组合和周期分析理论（如波浪理论、赫斯特周期等）来解读市场走势。

【上下文信息】
对话历史：
{history}

详细股票分析数据（包含技术指标、周期分析、市场状态、最新新闻等）：
{stock_data}

【当前任务】
用户问题：{input}

【分析要求】
1. **深度指标解读**：不要简单列举数据，要分析指标间的共振或背离。例如：RSI超买时，趋势强度(ADX)是否依然强劲？
2. **结合最新新闻**：基于提供的“最新新闻 (Recent News)”数据，分析近期新闻事件（如财报、重大合同、行业动态等）对股价走势、市场情绪的潜在影响，并判断新闻面与技术面是否共振。
3. **重点关注周期分析**：基于提供的“周期分析 (Cycle Analysis)”数据，指出当前处于周期的什么阶段，预测可能的拐点，并结合年度/月度周期规律给出见解。
4. **形态与支撑阻力**：结合横盘检测、Pivot Points和斐波那契回撤位，给出具体的关键价位分析。
5. **风险管理建议**：基于波动率(ATR)给出专业的风险提示，不要给出确定性的买卖建议，而是提供概率性的市场展望。
6. **专业性**：保持回答的逻辑严密、专业术语准确，且必须基于提供的 {stock_data} 数据进行分析。如果数据中某项缺失，请客观说明。

请开始你的深度分析："""
        )
        
        # 初始化工作流
        self._build_workflow()
    
    def _build_workflow(self):
        """
        构建对话工作流
        """
        class WorkflowState(TypedDict):
            session_id: str
            user_input: str
            history: str
            stock_data: str
            response: str
        
        def load_context_node(state: WorkflowState) -> Dict:
            """加载历史记录和股票数据"""
            session_id = state["session_id"]
            user_input = state["user_input"]
            
            # 加载历史对话
            memory = StockMemory(session_id)
            memory_vars = memory.load_memory_variables({'input': user_input})
            history = memory_vars.get('history', '')
            
            # 加载相关股票数据
            stock_data = self._load_stock_data(session_id, user_input)
            
            return {
                "history": history,
                "stock_data": stock_data
            }
        
        def generate_response_node(state: WorkflowState) -> Dict:
            """生成 AI 回复"""
            user_input = state["user_input"]
            history = state["history"]
            stock_data = state["stock_data"]
            
            prompt = self.prompt_template.format(
                history=history,
                stock_data=stock_data,
                input=user_input
            )
            
            # 打印提示词以供调试
            logger.info("=" * 50)
            logger.info(f"发送给 LLM 的提示词:\n{prompt}")
            logger.info("=" * 50)
            
            try:
                response = self.llm.invoke(prompt).content
            except Exception as e:
                logger.error(f"调用 LLM 失败: {e}")
                response = "抱歉，生成回复时出现错误。"
            
            return {"response": response}
        
        def save_context_node(state: WorkflowState) -> Dict:
            """保存对话上下文"""
            session_id = state["session_id"]
            user_input = state["user_input"]
            response = state["response"]
            
            memory = StockMemory(session_id)
            memory.save_context({'input': user_input}, {'response': response})
            
            return {}
        
        # 构建工作流图
        workflow_graph = StateGraph(WorkflowState)
        workflow_graph.add_node("load_context", load_context_node)
        workflow_graph.add_node("generate_response", generate_response_node)
        workflow_graph.add_node("save_context", save_context_node)
        
        workflow_graph.add_edge(START, "load_context")
        workflow_graph.add_edge("load_context", "generate_response")
        workflow_graph.add_edge("generate_response", "save_context")
        workflow_graph.add_edge("save_context", END)
        
        self.workflow = workflow_graph.compile()
    
    def _load_stock_data(self, session_id: str, user_input: str) -> str:
        """
        加载相关股票数据
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            
        Returns:
            格式化的股票数据字符串
        """
        try:
            # 从会话上下文中获取关注的股票代码
            session = ChatSession.objects.get(session_id=session_id)
            symbols = session.context_symbols or []
            
            # 从用户输入中提取可能的股票代码
            # 使用正则匹配：2-10位大写字母（可能带点或连字符）
            extracted_symbols = re.findall(r'\b[A-Z]{2,10}\b', user_input.upper())
            for symbol in extracted_symbols:
                if symbol not in symbols:
                    symbols.append(symbol)
            
            logger.info(f"会话 {session_id} 的关注股票: {symbols}")
            if symbols:
                session.context_symbols = list(set(symbols))[:5]  # 去重并最多保存5个
                session.save()
            
            # 获取这些股票的最新分析数据
            stock_data_parts = []
            # 优先加载当前选中的股票数据
            load_symbols = []
            for s in symbols:
                if s.upper() not in [ls.upper() for ls in load_symbols]:
                    load_symbols.append(s)
            load_symbols = load_symbols[:5]
            
            logger.info(f"正在为以下股票加载上下文数据: {load_symbols}")
            
            for symbol in load_symbols:
                try:
                    logger.info(f"正在尝试加载股票 {symbol} 的分析数据...")
                    # 查找最新的成功分析记录，放宽匹配条件（不区分大小写，且使用最新的记录）
                    analysis = StockAnalysis.objects.filter(
                        symbol__iexact=symbol.strip(),
                        status='success'
                    ).order_by('-updated_at').first()
                    
                    if analysis:
                        logger.info(f"成功找到股票 {symbol} 的分析数据 (ID: {analysis.id}, 更新于: {analysis.updated_at})")
                        data_summary = self._format_stock_analysis(analysis)
                        stock_data_parts.append(f"【{symbol.upper()}】\n{data_summary}")
                    else:
                        logger.warning(f"未找到股票 {symbol} 的成功分析记录 (status='success')")
                        # 如果没有成功记录，尝试找找看有没有任何记录
                        any_analysis = StockAnalysis.objects.filter(
                            symbol__iexact=symbol.strip()
                        ).order_by('-updated_at').first()
                        
                        if any_analysis:
                            logger.info(f"找到股票 {symbol} 的记录，但状态为: {any_analysis.status}")
                            stock_data_parts.append(f"【{symbol.upper()}】\n（该股票分析状态为 {any_analysis.status}，请先在详情页完成分析）")
                        else:
                            logger.info(f"数据库中完全没有股票 {symbol} 的分析记录")
                            stock_data_parts.append(f"【{symbol.upper()}】\n（暂无分析数据，请先对该股票进行一次技术分析）")
                except Exception as e:
                    logger.warning(f"加载股票 {symbol} 数据失败: {e}")
            
            if stock_data_parts:
                return '\n\n'.join(stock_data_parts)
            else:
                return "（暂无相关股票数据，请确保已对该股票进行了技术分析）"
                
        except Exception as e:
            logger.error(f"加载股票数据失败: {e}")
            return "（暂无相关股票数据）"
    
    def _format_stock_analysis(self, analysis: StockAnalysis) -> str:
        """
        格式化分析记录中的详细数据，供 LLM 使用
        """
        try:
            # 获取指标
            indicators = analysis.indicators or {}
            
            import json
            
            # 基本信息
            symbol = analysis.symbol.upper()
            extra = analysis.extra_data or {}
            currency_symbol = extra.get("currency_symbol") or extra.get("currencySymbol") or "$"
            
            def fmt_price(val):
                if val is None: return "N/A"
                try:
                    return f"{currency_symbol}{float(val):.2f}"
                except:
                    return f"{currency_symbol}{val}"

            sections = []
            
            # 1. 概览
            header = [
                f"# 股票代码: {symbol}",
                f"当前价格: {fmt_price(indicators.get('current_price'))}",
                f"价格涨跌: {indicators.get('price_change_pct', 0):.2f}%",
                f"分析时间: {analysis.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ]
            sections.append("\n".join(header))

            # 2. 最新新闻 (Recent News) - 新增
            news_data = indicators.get('news_data', [])
            if news_data:
                news_lines = ["## 最新新闻 (Recent News)", ""]
                for item in news_data:
                    title = item.get('title', '无标题')
                    publisher = item.get('publisher', '未知来源')
                    pub_time = item.get('provider_publish_time_fmt', '')
                    time_str = f" [{pub_time}]" if pub_time else ""
                    news_lines.append(f"- **{title}** ({publisher}){time_str}")
                news_lines.append("")
                sections.append("\n".join(news_lines))

            # 3. 技术指标 (Technical Indicators)
            tech_sections = [
                "## 技术指标 (Technical Indicators)",
                "",
                "### 趋势指标 (Trend Indicators)",
                f"- 移动平均线: MA5={fmt_price(indicators.get('ma5'))}, MA20={fmt_price(indicators.get('ma20'))}, MA50={fmt_price(indicators.get('ma50'))}, MA200={fmt_price(indicators.get('ma200'))}",
                f"- EMA: EMA12={fmt_price(indicators.get('ema12'))}, EMA26={fmt_price(indicators.get('ema26'))}",
                f"- 趋势方向: {indicators.get('trend_direction', 'neutral')}",
                f"- 趋势强度: {indicators.get('trend_strength', 0):.0f}%",
                f"- ADX: {indicators.get('adx', 0):.1f} (+DI={indicators.get('plus_di', 0):.1f}, -DI={indicators.get('minus_di', 0):.1f})",
                f"- SuperTrend: {fmt_price(indicators.get('supertrend'))} (方向: {indicators.get('supertrend_direction')})",
                f"- Ichimoku云层: {indicators.get('ichimoku_status', 'unknown')}",
                "",
                "### 动量指标 (Momentum Indicators)",
                f"- RSI (14): {indicators.get('rsi', 0):.1f}",
                f"- MACD: {indicators.get('macd', 0):.4f} (信号线: {indicators.get('macd_signal', 0):.4f}, 柱状图: {indicators.get('macd_histogram', 0):.4f})",
                f"- KDJ: K={indicators.get('kdj_k', 0):.1f}, D={indicators.get('kdj_d', 0):.1f}, J={indicators.get('kdj_j', 0):.1f}",
                f"- Williams %R: {indicators.get('williams_r', 0):.1f}",
                "",
                "### 波幅与成交量 (Volatility & Volume)",
                f"- 布林带 (Bollinger Bands): 上轨={fmt_price(indicators.get('bb_upper'))}, 中轨={fmt_price(indicators.get('bb_middle'))}, 下轨={fmt_price(indicators.get('bb_lower'))}",
                f"- ATR: {indicators.get('atr', 0):.4f} ({indicators.get('atr_percent', 0):.2f}%)",
                f"- 成交量比率: {indicators.get('volume_ratio', 0):.2f} (20日均量: {indicators.get('avg_volume_20', 0):.0f})",
                "",
                "### 支撑与阻力 (Support & Resistance)",
                f"- Pivot Point: {fmt_price(indicators.get('pivot'))}",
                f"- 阻力位: R1={fmt_price(indicators.get('pivot_r1'))}, R2={fmt_price(indicators.get('pivot_r2'))}, R3={fmt_price(indicators.get('pivot_r3'))}",
                f"- 支撑位: S1={fmt_price(indicators.get('pivot_s1'))}, S2={fmt_price(indicators.get('pivot_s2'))}, S3={fmt_price(indicators.get('pivot_s3'))}",
                f"- 50日高低点: 高={fmt_price(indicators.get('resistance_50d_high'))}, 低={fmt_price(indicators.get('support_50d_low'))}",
                ""
            ]
            sections.append("\n".join(tech_sections))

            # 3. 周期分析 (Cycle Analysis)
            cycle_sections = [
                "## 周期分析 (Cycle Analysis)",
                "",
                f"- 总体周期强度: {indicators.get('cycle_strength', 0):.2f}",
                f"- 周期一致性: {indicators.get('cycle_consistency', 0):.2f}",
                f"- 主导周期长度: {indicators.get('dominant_cycle', 'N/A')} 天",
                f"- 周期质量: {indicators.get('cycle_quality', 'N/A')}",
                f"- 年度周期 (Yearly Cycles): {json.dumps(indicators.get('yearly_cycles', []), ensure_ascii=False)}",
                f"- 月度周期 (Monthly Cycles): {json.dumps(indicators.get('monthly_cycles', []), ensure_ascii=False)}",
                f"- 周期总结: {indicators.get('cycle_summary', '暂无周期总结')}",
                ""
            ]
            sections.append("\n".join(cycle_sections))

            # 4. 形态与状态 (Patterns & Status)",
            status_sections = [
                "## 市场形态与状态 (Market Patterns & Status)",
                "",
                f"- 横盘检测: {'是' if indicators.get('sideways_market') else '否'} (强度: {indicators.get('sideways_strength', 0):.0f}%)",
                f"- 横盘类型: {indicators.get('sideways_type_desc', 'N/A')}",
                f"- 连续涨跌天数: {indicators.get('consecutive_up_days', 0)}天涨 / {indicators.get('consecutive_down_days', 0)}天跌",
                f"- 斐波那契回撤: 23.6%={fmt_price(indicators.get('fib_23.6'))}, 38.2%={fmt_price(indicators.get('fib_38.2'))}, 50%={fmt_price(indicators.get('fib_50.0'))}, 61.8%={fmt_price(indicators.get('fib_61.8'))}",
                ""
            ]
            sections.append("\n".join(status_sections))

            return "\n".join(sections)
                
        except Exception as e:
            logger.error(f"格式化股票分析数据失败: {e}")
            return f"（格式化数据时出错: {str(e)}）"
    
    def chat(self, session_id: str, user_input: str) -> str:
        """
        处理用户输入并返回 AI 回复
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            
        Returns:
            AI 的回复内容
        """
        initial_state = {
            "session_id": session_id,
            "user_input": user_input,
            "history": "",
            "stock_data": "",
            "response": ""
        }
        
        result = self.workflow.invoke(initial_state)
        return result["response"]
    
    async def stream_chat(self, session_id: str, user_input: str, skip_save_context: bool = False):
        """
        流式处理用户输入并逐步返回 AI 回复
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            skip_save_context: 是否跳过保存上下文（WebSocket 场景使用）
            
        Yields:
            AI 回复的 token 字符串
        """
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def load_memory():
            memory = StockMemory(session_id)
            return memory.load_memory_variables({'input': user_input})
        
        @database_sync_to_async
        def load_stock_data():
            return self._load_stock_data(session_id, user_input)
        
        @database_sync_to_async
        def save_memory_context(full_response):
            if not skip_save_context:
                memory = StockMemory(session_id)
                memory.save_context({'input': user_input}, {'response': full_response})
        
        # 加载股票数据
        stock_data = await load_stock_data()
        
        # 加载历史记录
        memory_vars = await load_memory()
        history = memory_vars.get('history', '')
        
        # 构建提示
        prompt = self.prompt_template.format(
            history=history,
            stock_data=stock_data,
            input=user_input
        )
        
        # 打印提示词以供调试
        logger.info("=" * 50)
        logger.info(f"发送给 LLM 的流式提示词:\n{prompt}")
        logger.info("=" * 50)
        
        # 流式调用 LLM
        full_response = ""
        async for chunk in self.llm.astream(prompt):
            if hasattr(chunk, 'content') and chunk.content:
                token = chunk.content
                full_response += token
                yield token
        
        # 保存完整回复
        await save_memory_context(full_response)
    
    def create_new_session(self, symbol: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        创建一个新的聊天会话

        Args:
            symbol: 关联的股票代码
            model: 使用的模型名称

        Returns:
            会话ID
        """
        session_id = str(uuid.uuid4())
        context_symbols = [symbol] if symbol else []
        ChatSession.objects.create(
            session_id=session_id,
            context_symbols=context_symbols,
            model=model
        )
        return session_id
    
    def get_session_history(self, session_id: str, limit: int = 50) -> list:
        """
        获取会话历史记录
        
        Args:
            session_id: 会话ID
            limit: 返回的最大消息数量
            
        Returns:
            消息列表
        """
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = ChatMessage.objects.filter(session=session).order_by('created_at')[:limit]
            
            result = []
            for msg in messages:
                result.append({
                    'id': msg.id,
                    'role': msg.role,
                    'content': msg.content,
                    'status': msg.status,
                    'metadata': msg.metadata,
                    'created_at': msg.created_at.isoformat()
                })
            
            return result
        except ChatSession.DoesNotExist:
            return []
