import logging
from typing import Optional, Dict, Any, Sequence, List
import operator

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
from asgiref.sync import sync_to_async

from .registry import AgentRegistry
from .memory import SessionMemory

logger = logging.getLogger(__name__)


def _extract_text(content) -> str:
    """Normalize LLM chunk content to plain string (handles str and list-of-parts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return ""


class WorkflowState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    correction_count: int  # tracks self-correction iterations (LastValue semantics)


class AIAgentEngine:
    """
    通用 AI Agent 引擎，通过 LiteLLM 支持 100+ LLM 提供商。

    可选特性（通过 AgentConfig 启用）：
      enable_vector_memory  — 语义记忆，按相关性召回历史而非截断
      critic_prompt         — 自我修正，每次生成后评估质量并重试
    """

    def __init__(self, namespace: str, model_name: str = None):
        self.config = AgentRegistry.get_config(namespace)
        if not self.config:
            raise ValueError(f"No agent configuration found for namespace: {namespace}")

        self.namespace = namespace
        self.model_name = model_name or self.config.model_name
        self.llm = self._create_llm()
        self.llm_with_tools = self.llm.bind_tools(self.config.tools) if self.config.tools else self.llm
        self.workflow = self._build_workflow()

    def _create_llm(self):
        from langchain_community.chat_models import ChatLiteLLM

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "temperature": 0.7,
        }
        if self.config.base_url:
            kwargs["api_base"] = self.config.base_url
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        if self.config.litellm_params:
            kwargs.update(self.config.litellm_params)

        logger.info(f"[{self.namespace}] LiteLLM: {self.model_name}")
        return ChatLiteLLM(**kwargs)

    def _build_workflow(self):
        has_tools = bool(self.config.tools)
        has_critic = bool(self.config.critic_prompt)

        def call_model(state: WorkflowState):
            messages = list(state["messages"])
            system_prompt = self.config.system_prompt.format(session_id=state["session_id"])
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=system_prompt)] + messages
            else:
                messages[0] = SystemMessage(content=system_prompt)
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}

        graph = StateGraph(WorkflowState)
        graph.add_node("agent", call_model)
        graph.add_edge(START, "agent")

        if has_tools:
            graph.add_node("tools", ToolNode(self.config.tools))
            graph.add_edge("tools", "agent")

        def route_after_agent(state: WorkflowState):
            last = state["messages"][-1]
            if has_tools and isinstance(last, AIMessage) and last.tool_calls:
                return "tools"
            if has_critic:
                return "critic"
            return END

        destinations = (["tools"] if has_tools else []) + (["critic"] if has_critic else []) + [END]
        graph.add_conditional_edges("agent", route_after_agent, destinations)

        if has_critic:
            def critic_node(state: WorkflowState):
                if state.get("correction_count", 0) >= self.config.max_correction_retries:
                    return {}
                last = state["messages"][-1]
                if not isinstance(last, AIMessage) or last.tool_calls:
                    return {}
                critic_msgs = [
                    SystemMessage(content=self.config.critic_prompt),
                    HumanMessage(content=(
                        f"请评估以下 AI 回复的质量。\n"
                        f"如需改进，回复 'RETRY: <改进说明>'；如果合格，回复 'PASS'。\n\n"
                        f"回复内容：\n{last.content}"
                    )),
                ]
                evaluation = self.llm.invoke(critic_msgs)
                if "RETRY:" in evaluation.content:
                    feedback = evaluation.content.split("RETRY:", 1)[-1].strip()
                    return {
                        "messages": [HumanMessage(content=f"[自动反馈] {feedback}，请重新回答")],
                        "correction_count": state.get("correction_count", 0) + 1,
                    }
                return {}

            def route_after_critic(state: WorkflowState):
                last = state["messages"][-1]
                if isinstance(last, HumanMessage) and str(last.content).startswith("[自动反馈]"):
                    return "agent"
                return END

            graph.add_node("critic", critic_node)
            graph.add_conditional_edges("critic", route_after_critic, ["agent", END])

        return graph.compile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_new_session(self, model: Optional[str] = None) -> str:
        return SessionMemory.create_session()

    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        return SessionMemory(session_id).get_history_dicts(limit=limit)

    async def stream_chat(self, session_id: str, user_input: str, skip_save_context: bool = False):
        """
        流式对话，使用 LangGraph astream_events v2 API。
        支持语义记忆（enable_vector_memory）、自我修正（critic_prompt）、思维链标签解析。
        """
        history = await self._build_history(session_id, user_input)

        messages = list(history)
        if messages and isinstance(messages[-1], AIMessage) and not messages[-1].content.strip():
            messages = messages[:-1]
        if not (messages and isinstance(messages[-1], HumanMessage) and messages[-1].content == user_input):
            messages.append(HumanMessage(content=user_input))

        inputs = {"messages": messages, "session_id": session_id, "correction_count": 0}

        START_TAGS = ["<thought>", "<think>"]
        END_TAGS = ["</thought>", "</think>"]
        is_thinking = False
        tag_buffer = ""

        async for event in self.workflow.astream_events(inputs, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                raw = _extract_text(event["data"]["chunk"].content)
                if not raw:
                    continue

                tag_buffer += raw

                while tag_buffer:
                    matched = False

                    for tag in START_TAGS:
                        if tag in tag_buffer:
                            before, _, after = tag_buffer.partition(tag)
                            if before:
                                yield self._make_chunk(before, is_thinking)
                            is_thinking = True
                            tag_buffer = after
                            matched = True
                            break
                    if matched:
                        continue

                    for tag in END_TAGS:
                        if tag in tag_buffer:
                            before, _, after = tag_buffer.partition(tag)
                            if before:
                                yield self._make_chunk(before, True)
                            is_thinking = False
                            yield {"type": "thought", "thought": "", "tool": "reasoning", "status": "success"}
                            tag_buffer = after
                            matched = True
                            break
                    if matched:
                        continue

                    partial_len = 0
                    for tag in START_TAGS + END_TAGS:
                        for i in range(len(tag) - 1, 0, -1):
                            if tag_buffer.endswith(tag[:i]):
                                partial_len = max(partial_len, i)
                                break

                    if partial_len:
                        safe = tag_buffer[:-partial_len]
                        if safe:
                            yield self._make_chunk(safe, is_thinking)
                            tag_buffer = tag_buffer[-partial_len:]
                        break
                    else:
                        yield self._make_chunk(tag_buffer, is_thinking)
                        tag_buffer = ""
                        break

            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                display = self.config.tool_display_names.get(tool_name, tool_name)
                yield {"type": "thought", "thought": f"正在{display}...", "tool": tool_name, "status": "loading"}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                display = self.config.tool_display_names.get(tool_name, tool_name)
                yield {"type": "thought", "thought": f"已完成{display}", "tool": tool_name, "status": "success"}

        if tag_buffer:
            yield self._make_chunk(tag_buffer, is_thinking)

    async def _build_history(self, session_id: str, user_input: str) -> List[BaseMessage]:
        """
        构建对话历史。
        普通模式：取最近 10 条。
        向量记忆模式：最近 5 条 + 语义相关的更早消息（去重）。
        """
        memory = await sync_to_async(SessionMemory)(session_id)

        if not self.config.enable_vector_memory:
            return await sync_to_async(memory.get_messages)(limit=10)

        # 最近 5 条（带 DB id 用于去重）
        from .models import ChatMessage
        recent_db = await sync_to_async(
            lambda: list(
                ChatMessage.objects
                .filter(session__session_id=session_id)
                .order_by('-created_at')[:5]
                .values('id', 'role', 'content')
            )
        )()
        recent_ids = {r['id'] for r in recent_db}
        recent_messages = []
        for r in reversed(recent_db):
            if r['role'] == 'user':
                recent_messages.append(HumanMessage(content=r['content']))
            elif r['role'] == 'assistant':
                recent_messages.append(AIMessage(content=r['content']))

        # 语义相关的更早消息
        from .memory import VectorMemory
        vector_mem = await sync_to_async(VectorMemory)(session_id)
        semantic = await sync_to_async(vector_mem.search)(user_input, k=5, exclude_ids=list(recent_ids))

        extra: List[BaseMessage] = []
        for r in semantic:
            if r['role'] == 'user':
                extra.append(HumanMessage(content=r['content']))
            elif r['role'] == 'assistant':
                extra.append(AIMessage(content=r['content']))

        # 语义上下文在前，最近消息在后
        return extra + recent_messages

    def _make_chunk(self, content: str, is_thinking: bool) -> dict:
        if is_thinking:
            return {"type": "thought", "thought": content, "tool": "reasoning", "status": "loading"}
        return {"type": "token", "content": content, "status": "streaming"}


def create_engine(namespace: str, model_name: str = None):
    """
    工厂函数：根据 AgentConfig.sub_namespaces 决定返回 SupervisorEngine 还是 AIAgentEngine。
    """
    config = AgentRegistry.get_config(namespace)
    if config and config.sub_namespaces:
        from .supervisor import SupervisorEngine
        return SupervisorEngine(namespace)
    return AIAgentEngine(namespace, model_name=model_name)
