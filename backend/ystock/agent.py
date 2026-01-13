"""
股票分析 AI Agent 服务模块
集成 LangChain 和 Ollama，提供股票分析对话功能
"""
import os
import uuid
import logging
from typing import Optional, Dict, Any
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
    def __init__(self, model_name: str = "qwen2.5:latest", base_url: Optional[str] = None):
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
            input_variables=["history", "stock_data", "input"],
            template="""你是一个专业的股票分析助手，擅长技术分析和市场解读。

以下是历史对话记录：
{history}

相关股票数据和分析结果：
{stock_data}

用户问题：{input}

请基于提供的数据给出专业、客观的分析建议。回答时注意：
1. 结合技术指标进行分析
2. 解释关键指标的含义和信号
3. 提供风险提示
4. 语言简洁专业，避免过度承诺

助手回复："""
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
            words = user_input.upper().split()
            for word in words:
                # 简单判断：如果是全大写且包含字母，可能是股票代码
                if word.isalnum() and any(c.isalpha() for c in word):
                    if word not in symbols:
                        symbols.append(word)
            
            # 更新会话的股票代码列表
            session.context_symbols = symbols[:5]  # 最多保存5个
            session.save()
            
            # 获取这些股票的最新分析数据
            stock_data_parts = []
            for symbol in symbols[:3]:  # 最多加载3个股票的数据
                try:
                    analysis = StockAnalysis.objects.filter(
                        symbol=symbol,
                        status=StockAnalysis.Status.SUCCESS
                    ).order_by('-updated_at').first()
                    
                    if analysis:
                        data_summary = self._format_stock_analysis(analysis)
                        stock_data_parts.append(f"【{symbol}】\n{data_summary}")
                except Exception as e:
                    logger.warning(f"加载股票 {symbol} 数据失败: {e}")
            
            if stock_data_parts:
                return '\n\n'.join(stock_data_parts)
            else:
                return "（暂无相关股票数据）"
                
        except Exception as e:
            logger.error(f"加载股票数据失败: {e}")
            return "（暂无相关股票数据）"
    
    def _format_stock_analysis(self, analysis: StockAnalysis) -> str:
        """
        格式化股票分析数据为文本
        
        Args:
            analysis: 股票分析记录
            
        Returns:
            格式化的分析数据文本
        """
        parts = []
        
        # 添加基本信息
        if analysis.extra_data:
            stock_name = analysis.extra_data.get('stock_name', '')
            currency = analysis.extra_data.get('currency', '')
            if stock_name:
                parts.append(f"名称: {stock_name}")
            if currency:
                parts.append(f"货币: {currency}")
        
        # 添加技术指标摘要
        if analysis.indicators:
            indicators = analysis.indicators
            indicator_parts = []
            
            # 添加关键指标
            if 'ma' in indicators:
                ma_data = indicators['ma']
                if ma_data and len(ma_data) > 0:
                    latest = ma_data[-1]
                    indicator_parts.append(f"MA: {latest.get('ma5', 'N/A'):.2f} / {latest.get('ma20', 'N/A'):.2f}")
            
            if 'rsi' in indicators:
                rsi_data = indicators['rsi']
                if rsi_data and len(rsi_data) > 0:
                    latest_rsi = rsi_data[-1].get('rsi', 0)
                    indicator_parts.append(f"RSI: {latest_rsi:.2f}")
            
            if 'macd' in indicators:
                macd_data = indicators['macd']
                if macd_data and len(macd_data) > 0:
                    latest_macd = macd_data[-1]
                    indicator_parts.append(f"MACD: {latest_macd.get('macd', 0):.2f}")
            
            if indicator_parts:
                parts.append("技术指标: " + ", ".join(indicator_parts))
        
        # 添加交易信号
        if analysis.signals:
            signals = analysis.signals
            if 'overall_signal' in signals:
                parts.append(f"综合信号: {signals['overall_signal']}")
        
        # 添加 AI 分析（如果有）
        if analysis.ai_analysis:
            parts.append(f"AI分析: {analysis.ai_analysis[:200]}...")
        
        return '\n'.join(parts) if parts else "无详细数据"
    
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
        
        # 加载历史记录和股票数据
        memory_vars = await load_memory()
        history = memory_vars.get('history', '')
        stock_data = await load_stock_data()
        
        # 构建提示
        prompt = self.prompt_template.format(
            history=history,
            stock_data=stock_data,
            input=user_input
        )
        
        # 流式调用 LLM
        full_response = ""
        async for chunk in self.llm.astream(prompt):
            if hasattr(chunk, 'content') and chunk.content:
                token = chunk.content
                full_response += token
                yield token
        
        # 保存完整回复
        await save_memory_context(full_response)
    
    def create_new_session(self) -> str:
        """
        创建新的会话
        
        Returns:
            新的会话ID
        """
        session_id = str(uuid.uuid4())
        ChatSession.objects.create(session_id=session_id)
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
