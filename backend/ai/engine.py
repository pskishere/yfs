import os
import logging
from typing import Optional, Dict, Any, Sequence, List
import operator

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
from asgiref.sync import sync_to_async

from .registry import AgentRegistry
from .memory import SessionMemory

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """
    LangGraph 工作流状态定义
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str

class AIAgentEngine:
    """
    通用 AI Agent 引擎
    """
    def __init__(self, namespace: str, model_name: str = None):
        """
        初始化指定业务的 Agent
        
        Args:
            namespace: 业务命名空间
            model_name: 可选的模型名称覆盖
        """
        self.config = AgentRegistry.get_config(namespace)
        if not self.config:
            raise ValueError(f"No agent configuration found for namespace: {namespace}")

        self.namespace = namespace
        self.model_name = model_name or self.config.model_name
        
        # 初始化 LLM
        ollama_base_url = self.config.base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        ollama_base_url = ollama_base_url.rstrip('/')
        
        logger.info(f"初始化 AI Agent [{namespace}]: model={self.model_name}, base_url={ollama_base_url}")
        
        self.llm = ChatOllama(
            model=self.model_name,
            base_url=ollama_base_url,
            temperature=0.7,
        )
        
        if self.config.tools:
            self.llm = self.llm.bind_tools(self.config.tools)
        
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """
        构建基于 ReAct 模式的对话工作流
        """
        def call_model(state: WorkflowState):
            messages = list(state["messages"])
            session_id = state["session_id"]
            
            # 动态注入 Session ID 到 System Prompt
            system_prompt = self.config.system_prompt.format(session_id=session_id)
            
            # 确保 SystemMessage 存在且是最新的
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=system_prompt)] + list(messages)
            else:
                messages[0] = SystemMessage(content=system_prompt)
            
            response = self.llm.invoke(messages)
            return {"messages": [response]}

        workflow = StateGraph(WorkflowState)
        workflow.add_node("agent", call_model)
        
        if self.config.tools:
            tool_node = ToolNode(self.config.tools)
            workflow.add_node("tools", tool_node)
            workflow.add_edge(START, "agent")
            
            def should_continue(state: WorkflowState):
                messages = state["messages"]
                last_message = messages[-1]
                if last_message.tool_calls:
                    return "tools"
                return END
                
            workflow.add_conditional_edges("agent", should_continue)
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge(START, "agent")
            workflow.add_edge("agent", END)

        return workflow.compile()

    def create_new_session(self, model: Optional[str] = None) -> str:
        """创建一个新会话"""
        return SessionMemory.create_session()

    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取会话历史"""
        memory = SessionMemory(session_id)
        return memory.get_history_dicts(limit=limit)

    async def stream_chat(self, session_id: str, user_input: str, skip_save_context: bool = False):
        """
        流式对话接口
        """
        # 异步初始化 Memory (因为 __init__ 包含 DB 操作)
        memory = await sync_to_async(SessionMemory)(session_id)
        
        # 异步加载历史记录
        history_messages = await sync_to_async(memory.get_messages)(limit=10)
        
        messages = list(history_messages)
        
        # 1. 移除末尾的空 AI 消息 (占位符)
        if messages and isinstance(messages[-1], AIMessage) and not messages[-1].content.strip():
            messages = messages[:-1]
            
        # 2. 检查末尾是否已经包含当前用户输入
        if messages and isinstance(messages[-1], HumanMessage) and messages[-1].content == user_input:
            pass # 已经包含，不用添加
        else:
            # 构建当前输入
            messages.append(HumanMessage(content=user_input))
        
        inputs = {"messages": messages, "session_id": session_id}
        
        # 使用 astream_events 获取流式事件
        async for event in self.workflow.astream_events(inputs, version="v1"):
            kind = event["event"]
            
            # 监听 LLM 生成的 token
            if kind == "on_chat_model_stream":
                # 忽略工具调用的流式输出，只关注最终回复
                # 但 ReAct 模式下，Agent 思考过程也是 chat_model_stream
                # 我们需要区分是 Tool Call 还是 Final Response
                # 这里简单处理：只要有 content 就输出
                chunk = event["data"]["chunk"]
                content = chunk.content
                if content:
                    yield {
                        "type": "token",
                        "content": content,
                        "status": "streaming"
                    }
            
            # 监听工具调用开始
            elif kind == "on_tool_start":
                tool_name = event['name']
                display_name = self.config.tool_display_names.get(tool_name, tool_name)
                yield {
                    "type": "thought",
                    "content": f"正在{display_name}...",
                    "tool": tool_name,
                    "status": "loading"
                }
                
            # 监听工具调用结束
            elif kind == "on_tool_end":
                tool_name = event['name']
                display_name = self.config.tool_display_names.get(tool_name, tool_name)
                yield {
                    "type": "thought",
                    "content": f"已完成{display_name}",
                    "tool": tool_name,
                    "status": "success"
                }

    def process_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        处理用户消息 (非流式)
        """
        memory = SessionMemory(session_id)
        history_messages = memory.get_messages(limit=10)
        
        inputs = {"messages": history_messages + [HumanMessage(content=message)], "session_id": session_id}
        
        final_state = self.workflow.invoke(inputs)
        
        # 获取最后一条 AI 消息
        last_message = final_state["messages"][-1]
        response_content = last_message.content
        
        # 提取思维链 (如果模型支持)
        thoughts = []
        # TODO: 解析思维链
             
        # 保存记忆
        memory.save_context(
            inputs={'input': message}, 
            outputs={'response': response_content, 'thoughts': thoughts}
        )
        
        return {
            "response": response_content,
            "thoughts": thoughts
        }
