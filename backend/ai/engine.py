import os
import re
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
            
            # 打印 LLM 的完整响应
            print(f"\n{'='*20} LLM Response [{self.namespace}] {'='*20}")
            if response.content:
                print(f"Content: {response.content}")
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"Tool Calls: {response.tool_calls}")
            print(f"{'='*60}\n")
            
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
        流式对话接口，支持思维链标签解析
        """
        # 异步初始化 Memory
        memory = await sync_to_async(SessionMemory)(session_id)
        history_messages = await sync_to_async(memory.get_messages)(limit=10)
        
        messages = list(history_messages)
        
        # 移除末尾的空 AI 消息并确保用户输入正确添加
        if messages and isinstance(messages[-1], AIMessage) and not messages[-1].content.strip():
            messages = messages[:-1]
            
        if not (messages and isinstance(messages[-1], HumanMessage) and messages[-1].content == user_input):
            messages.append(HumanMessage(content=user_input))
        
        inputs = {"messages": messages, "session_id": session_id}
        
        full_content = []
        is_thinking = False
        tag_buffer = ""
        
        # 定义标签
        START_TAGS = ["<thought>", "<think>"]
        END_TAGS = ["</thought>", "</think>"]

        async for event in self.workflow.astream_events(inputs, version="v1"):
            kind = event["event"]
            
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = chunk.content
                if not content: continue
                
                tag_buffer += content
                
                while tag_buffer:
                    # 1. 检查开始标签
                    found_start = False
                    for tag in START_TAGS:
                        if tag in tag_buffer:
                            parts = tag_buffer.split(tag, 1)
                            if parts[0]:
                                yield self._format_chunk(parts[0], is_thinking, full_content)
                            
                            is_thinking = True
                            tag_buffer = parts[1]
                            found_start = True
                            break
                    if found_start: continue
                        
                    # 2. 检查结束标签
                    found_end = False
                    for tag in END_TAGS:
                        if tag in tag_buffer:
                            parts = tag_buffer.split(tag, 1)
                            if parts[0]:
                                yield self._format_chunk(parts[0], True, full_content)
                            
                            is_thinking = False
                            yield {"type": "thought", "thought": "", "tool": "reasoning", "status": "success"}
                            tag_buffer = parts[1]
                            found_end = True
                            break
                    if found_end: continue
                        
                    # 3. 处理部分标签 (Partial Tags)
                    potential_tags = START_TAGS + END_TAGS
                    max_partial_len = 0
                    for tag in potential_tags:
                        for i in range(len(tag) - 1, 0, -1):
                            if tag_buffer.endswith(tag[:i]):
                                max_partial_len = max(max_partial_len, i)
                                break
                    
                    if max_partial_len > 0:
                        content_to_send = tag_buffer[:-max_partial_len]
                        if content_to_send:
                            yield self._format_chunk(content_to_send, is_thinking, full_content)
                            tag_buffer = tag_buffer[-max_partial_len:]
                        break # 等待更多数据来匹配完整标签
                    else:
                        yield self._format_chunk(tag_buffer, is_thinking, full_content)
                        tag_buffer = ""
                        break
            
            elif kind == "on_tool_start":
                tool_name = event['name']
                display_name = self.config.tool_display_names.get(tool_name, tool_name)
                logger.debug(f"Tool Start: {tool_name}")
                yield {"type": "thought", "thought": f"正在{display_name}...", "tool": tool_name, "status": "loading"}
                
            elif kind == "on_tool_end":
                tool_name = event['name']
                display_name = self.config.tool_display_names.get(tool_name, tool_name)
                logger.debug(f"Tool End: {tool_name}")
                yield {"type": "thought", "thought": f"已完成{display_name}", "tool": tool_name, "status": "success"}

    def _format_chunk(self, content: str, is_thinking: bool, full_content_list: list) -> dict:
        """辅助方法：格式化输出 chunk"""
        if is_thinking:
            return {"type": "thought", "thought": content, "tool": "reasoning", "status": "loading"}
        else:
            full_content_list.append(content)
            return {"type": "token", "content": content, "status": "streaming"}

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
        
        # 解析思维链 (<thought>...</thought> 或 <think>...</think>)
        if isinstance(response_content, str):
            # 同时支持 thought 和 think 标签
            patterns = [
                re.compile(r'<thought>(.*?)</thought>', re.DOTALL),
                re.compile(r'<think>(.*?)</think>', re.DOTALL)
            ]
            
            for pattern in patterns:
                found_thoughts = pattern.findall(response_content)
                for thought in found_thoughts:
                    print(f"\n{'='*20} Chain of Thought {'='*20}\n{thought.strip()}\n{'='*58}\n")
                    thoughts.append({
                        "key": "reasoning",
                        "title": "思考过程",
                        "content": thought.strip(),
                        "status": "success"
                    })
                # 移除思维链内容
                response_content = pattern.sub('', response_content).strip()
             
        # 保存记忆
        memory.save_context(
            inputs={'input': message}, 
            outputs={'response': response_content, 'thoughts': thoughts}
        )
        
        return {
            "response": response_content,
            "thoughts": thoughts
        }
