"""
SupervisorEngine — 多 Agent 路由器。

注册方式：
    AgentRegistry.register(
        namespace="assistant",
        config=AgentConfig(
            model_name="claude-sonnet-4-6",
            tools=[],
            system_prompt="...",
            sub_namespaces=["research", "code", "data"],  # 触发 Supervisor 模式
        ),
    )

工作流：
  用户消息 → Supervisor LLM 选择子 Agent → 子 Agent 流式回答
"""
import logging
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage
from asgiref.sync import sync_to_async

from .registry import AgentRegistry
from .memory import SessionMemory

logger = logging.getLogger(__name__)


class SupervisorEngine:
    """
    Supervisor 把用户请求路由到最合适的子 Agent，然后直接流式转发其输出。
    对外接口与 AIAgentEngine 完全相同（stream_chat / create_new_session / get_session_history）。
    """

    def __init__(self, namespace: str):
        self.config = AgentRegistry.get_config(namespace)
        if not self.config:
            raise ValueError(f"No config for supervisor namespace: {namespace}")
        if not self.config.sub_namespaces:
            raise ValueError(f"Namespace '{namespace}' has no sub_namespaces — cannot act as Supervisor")

        self.namespace = namespace
        self.model_name = self.config.model_name
        self._sub_engines: Dict[str, 'AIAgentEngine'] = {}

    # ------------------------------------------------------------------
    # Lazy sub-engine cache
    # ------------------------------------------------------------------

    def _get_sub_engine(self, ns: str):
        from .engine import AIAgentEngine
        if ns not in self._sub_engines:
            self._sub_engines[ns] = AIAgentEngine(ns)
        return self._sub_engines[ns]

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _build_router_llm(self):
        from langchain_litellm import ChatLiteLLM
        kwargs = {"model": self.config.model_name, "temperature": 0.0}
        if self.config.base_url:
            kwargs["api_base"] = self.config.base_url
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        return ChatLiteLLM(**kwargs)

    async def _route(self, user_input: str) -> str:
        """返回最合适的子命名空间名称。"""
        lines = []
        for ns in self.config.sub_namespaces:
            sub = AgentRegistry.get_config(ns)
            desc = (sub.system_prompt[:120].replace('\n', ' ') if sub else ns)
            lines.append(f"- {ns}: {desc}")

        prompt = (
            "根据用户请求，从以下智能体中选择最合适的一个。"
            "只输出命名空间名称，不要有任何解释或标点。\n\n"
            f"可用智能体：\n" + "\n".join(lines) +
            f"\n\n用户请求：{user_input}\n\n选择："
        )

        llm = self._build_router_llm()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        chosen = response.content.strip().lower().split()[0].rstrip('.,;:')

        if chosen not in self.config.sub_namespaces:
            # try substring match (LLM may include extra words)
            match = next((ns for ns in self.config.sub_namespaces if ns in chosen), None)
            if match:
                chosen = match
            else:
                logger.warning(f"Supervisor got unknown namespace '{chosen}', falling back to first")
                chosen = self.config.sub_namespaces[0]

        logger.info(f"[supervisor:{self.namespace}] routed '{user_input[:40]}' → {chosen}")
        return chosen

    # ------------------------------------------------------------------
    # Public API (mirrors AIAgentEngine)
    # ------------------------------------------------------------------

    def create_new_session(self, model=None) -> str:
        return SessionMemory.create_session()

    def get_session_history(self, session_id: str, limit: int = 50):
        return SessionMemory(session_id).get_history_dicts(limit=limit)

    async def stream_chat(self, session_id: str, user_input: str, skip_save_context: bool = False):
        # Step 1: emit routing thought
        yield {"type": "thought", "thought": "分析请求，选择最合适的智能体...", "tool": "router", "status": "loading"}

        # Step 2: route
        chosen_ns = await self._route(user_input)
        sub_config = AgentRegistry.get_config(chosen_ns)
        display = sub_config.system_prompt.split('\n')[0][:30] if sub_config else chosen_ns

        yield {"type": "thought", "thought": f"已选择「{chosen_ns}」智能体", "tool": "router", "status": "success"}

        # Step 3: delegate to sub-engine
        engine = self._get_sub_engine(chosen_ns)
        async for chunk in engine.stream_chat(session_id, user_input, skip_save_context):
            yield chunk
