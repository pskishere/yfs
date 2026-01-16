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
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, Sequence, Union
import operator

from .models import ChatSession, ChatMessage, StockAnalysis
from .tools import STOCKS_TOOLS, get_technical_indicators, get_stock_news, get_fundamental_data, get_cycle_analysis

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """
    LangGraph 工作流状态定义
    使用 Annotated[..., operator.add] 来实现消息列表的自动追加
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str


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
                content=ai_output,
                thoughts=outputs.get('thoughts', [])
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
        ).bind_tools(STOCKS_TOOLS)
        
        # 定义系统提示词模板 (Context Engineering)
        self.system_prompt_template = """你是一个极度专业且资深的股票技术分析专家和市场策略师。
你拥有强大的工具库，可以按需获取股票的技术指标、最新新闻、基本面数据和周期分析。

【你的工作流程】
          1. **识别需求**：当用户询问某只股票时，首先判断你需要哪些数据。如果用户没有指定股票代码，请先使用 `search_stock_symbol` 工具进行搜索，或询问用户。
          2. **调用工具**：使用 `get_technical_indicators` 获取技术面，`get_stock_news` 获取新闻面，`get_fundamental_data` 获取基本面，`get_cycle_analysis` 获取周期分析，`get_options_data` 获取期权数据，以及 `search_stock_symbol` 搜索代码。
          3. **综合分析**：
   - **指标共振**：分析技术指标间的共振或背离。
   - **新闻驱动**：结合最新新闻分析对市场情绪的影响。
   - **期权洞察**：分析期权链数据（如行权价分布、隐含波动率）以判断市场对未来的波动预期和潜在支撑/阻力位。
   - **周期位置**：利用周期数据预测潜在拐点。
   - **风险管理**：基于数据给出概率性的展望，而非确定性的买卖建议。

【当前上下文】
- 会话 ID: {session_id}

【注意事项】
- 始终基于工具返回的真实数据进行回答。
- 如果数据缺失，请客观说明。
- 保持回答逻辑严密、专业术语准确。
- 回答应尽量简明扼要，直击重点，避免过长且冗余的描述。
- **重要：可视化展示**：你可以通过在回复中插入特定的标签来展示专业的可视化组件。
  - 标签格式：`<stock-analysis symbol="股票代码" module="模块名称" />`
  - 可用模块名称：
    - `price`: 价格信息（当前价格、涨跌幅、高低价等）
    - `indicators`: 技术指标（RSI, MACD, KDJ 等详细数值）
    - `chart`: K线图表
    - `fundamental`: 基本面数据（市值、市盈率、收入等）
    - `market`: 市场行情（成交量、平均成交量等）
    - `cycle`: 周期分析（短期、中期、长期趋势）
    - `pivot`: 枢轴点（支撑位与阻力位）
    - `options`: 期权链数据（行权价、隐含波动率等）
  - **触发规则**：
    - 提及价格/走势：必须包含 `price` 和 `chart`。
    - 询问技术指标/买卖点：必须包含 `indicators` 和 `chart`。
    - 询问公司价值/财务：必须包含 `fundamental`。
    - 询问期权/波动率：必须包含 `options`。
    - 综合诊断：应包含 `price`, `chart`, `indicators`, `fundamental`, `cycle`。
  - **指令响应**：
176→    - 如果用户输入类似 `/{{module}} {{symbol}}` 的指令（如 `/价格 AAPL`、`/图表 AAPL`、`/指标 700.HK` 等），请**立即调用相关工具**获取数据，并**仅返回**对应的可视化标签（如 `<stock-analysis symbol="AAPL" module="价格" />`），无需多余文字解释，除非数据获取失败。
  - **组合建议**：
    - 基础分析：`price` + `chart`
    - 技术分析：`chart` + `indicators` + `pivot`
    - 全方位分析：`price` + `chart` + `indicators` + `fundamental` + `cycle`
  - 示例：当你分析 AAPL 的价格时，可以在文字描述后加上 `<stock-analysis symbol="AAPL" module="price" />`。你可以一次性插入多个模块，每个模块占一行。"""
        
        # 初始化工作流
        self._build_workflow()

    def _build_workflow(self):
        """
        构建基于 ReAct 模式的对话工作流 (Context Engineering)
        """
        def call_model(state: WorkflowState):
            """调用模型决定下一步操作"""
            # 获取当前状态的消息列表
            messages = list(state["messages"])
            session_id = state["session_id"]
            
            # 动态生成系统提示词
            system_prompt = self.system_prompt_template.format(
                session_id=session_id
            )
            
            # 如果消息列表开头不是系统消息，则添加
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=system_prompt)] + list(messages)
            else:
                # 更新现有的系统消息
                messages = [SystemMessage(content=system_prompt)] + list(messages[1:])
            
            response = self.llm.invoke(messages)
            return {"messages": [response]}

        def should_continue(state: WorkflowState):
            """判断是否需要继续调用工具"""
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        # 创建工作流图
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(STOCKS_TOOLS))
        
        # 设置入口和边
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        workflow.add_edge("tools", "agent")
        
        self.app = workflow.compile()
    
    def chat(self, session_id: str, user_input: str) -> str:
        """
        处理用户输入并返回 AI 回复 (ReAct 模式)
        """
        # 加载历史记录
        memory = StockMemory(session_id)
        history_vars = memory.load_memory_variables({'input': user_input})
        
        # 将历史记录解析为消息列表 (简化处理，假设 history 是文本)
        # 更好的做法是直接存储消息对象，这里先做转换
        messages = []
        history_text = history_vars.get('history', '')
        if history_text:
            for line in history_text.split('\n'):
                if line.startswith('用户: '):
                    messages.append(HumanMessage(content=line[4:]))
                elif line.startswith('助手: '):
                    messages.append(AIMessage(content=line[4:]))
        
        # 添加当前输入
        messages.append(HumanMessage(content=user_input))
        
        # 获取当前会话关联的股票
        session = ChatSession.objects.get(session_id=session_id)
        initial_state = {
            "messages": messages,
            "session_id": session_id
        }
        
        result = self.app.invoke(initial_state)
        
        # 提取最后一条 AI 消息作为回复
        final_response = result["messages"][-1].content
        
        # 保存上下文
        memory.save_context({'input': user_input}, {'response': final_response})
        
        return final_response
    
    async def stream_chat(self, session_id: str, user_input: str, skip_save_context: bool = False):
        """
        流式处理用户输入并逐步返回 AI 回复 (Context Engineering)
        支持流式返回 token 和思维链 (Tool Calls)，并在完成时保存上下文
        """
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def get_context():
            memory = StockMemory(session_id)
            history_vars = memory.load_memory_variables({'input': user_input})
            session = ChatSession.objects.get(session_id=session_id)
            return history_vars, session

        history_vars, session = await get_context()
        
        messages = []
        history_text = history_vars.get('history', '')
        if history_text:
            for line in history_text.split('\n'):
                if line.startswith('用户: '):
                    messages.append(HumanMessage(content=line[4:]))
                elif line.startswith('助手: '):
                    messages.append(AIMessage(content=line[4:]))
        
        messages.append(HumanMessage(content=user_input))
        
        initial_state = {
            "messages": messages,
            "session_id": session_id
        }
        
        full_response = ""
        
        # 工具名称到展示名称的映射
        tool_display_names = {
            "get_technical_indicators": "分析技术指标",
            "get_stock_news": "查询最新新闻",
            "get_fundamental_data": "获取基本面数据",
            "get_cycle_analysis": "执行周期分析",
            "get_options_data": "获取期权链数据",
            "search_stock_symbol": "搜索股票代码"
        }
        
        # 使用 astream_events 来捕获流式输出
        async for event in self.app.astream_events(initial_state, version="v1"):
            kind = event["event"]
            
            # 当 agent 节点正在流式生成内容时
            if kind == "on_chat_model_stream" and event["metadata"].get("langgraph_node") == "agent":
                content = event["data"]["chunk"].content
                if content:
                    full_response += content
                    yield {"type": "token", "content": content}
            
            # 捕获工具调用开始
            elif kind == "on_tool_start":
                tool_name = event["name"]
                display_name = tool_display_names.get(tool_name, tool_name)
                yield {
                    "type": "thought",
                    "content": f"正在{display_name}...",
                    "status": "loading",
                    "tool": tool_name
                }
            
            # 捕获工具调用结束
            elif kind == "on_tool_end":
                tool_name = event["name"]
                display_name = tool_display_names.get(tool_name, tool_name)
                yield {
                    "type": "thought",
                    "content": f"已完成{display_name}",
                    "status": "success",
                    "tool": tool_name
                }

        # 完成后异步保存上下文
        if not skip_save_context:
            @database_sync_to_async
            def save_context(resp):
                memory = StockMemory(session_id)
                memory.save_context({'input': user_input}, {'response': resp})
            
            await save_context(full_response)

    def create_new_session(self, model: Optional[str] = None) -> str:
        """
        创建一个新的聊天会话

        Args:
            model: 使用的模型名称

        Returns:
            会话ID
        """
        session_id = str(uuid.uuid4())
        ChatSession.objects.create(
            session_id=session_id,
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
                    'thoughts': msg.thoughts,
                    'metadata': msg.metadata,
                    'created_at': msg.created_at.isoformat()
                })
            
            return result
        except ChatSession.DoesNotExist:
            return []
