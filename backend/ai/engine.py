import os
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


class AIAgentEngine:
    """
    通用 AI Agent 引擎，支持 Ollama 和 OpenAI 兼容接口
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
        provider = self.config.provider
        base_url = self.config.base_url

        if provider == 'openai':
            from langchain_openai import ChatOpenAI
            api_key = (
                self.config.api_key
                or os.getenv('OPENAI_API_KEY', 'sk-placeholder')
            )
            kwargs: Dict[str, Any] = dict(
                model=self.model_name,
                temperature=0.7,
                api_key=api_key,
            )
            if base_url:
                kwargs['base_url'] = base_url
            logger.info(f"[{self.namespace}] LLM: OpenAI-compatible {self.model_name} @ {base_url}")
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(**kwargs)

        # default: ollama
        from langchain_ollama import ChatOllama
        ollama_url = (base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')).rstrip('/')
        logger.info(f"[{self.namespace}] LLM: Ollama {self.model_name} @ {ollama_url}")
        return ChatOllama(model=self.model_name, base_url=ollama_url, temperature=0.7)

    def _build_workflow(self):
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

        if self.config.tools:
            graph.add_node("tools", ToolNode(self.config.tools))
            graph.add_edge(START, "agent")

            def should_continue(state: WorkflowState):
                return "tools" if state["messages"][-1].tool_calls else END

            graph.add_conditional_edges("agent", should_continue)
            graph.add_edge("tools", "agent")
        else:
            graph.add_edge(START, "agent")
            graph.add_edge("agent", END)

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
        支持 <think>/<thought> 思维链标签解析。
        """
        memory = await sync_to_async(SessionMemory)(session_id)
        history = await sync_to_async(memory.get_messages)(limit=10)

        messages = list(history)
        if messages and isinstance(messages[-1], AIMessage) and not messages[-1].content.strip():
            messages = messages[:-1]
        if not (messages and isinstance(messages[-1], HumanMessage) and messages[-1].content == user_input):
            messages.append(HumanMessage(content=user_input))

        inputs = {"messages": messages, "session_id": session_id}

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

                    # Partial tag at buffer end — wait for more data
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

        # Flush remaining buffer
        if tag_buffer:
            yield self._make_chunk(tag_buffer, is_thinking)

    def _make_chunk(self, content: str, is_thinking: bool) -> dict:
        if is_thinking:
            return {"type": "thought", "thought": content, "tool": "reasoning", "status": "loading"}
        return {"type": "token", "content": content, "status": "streaming"}
