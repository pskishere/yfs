from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class AgentConfig:
    """
    Agent 配置对象
    """
    def __init__(
        self,
        model_name: str,
        tools: List[Any],
        system_prompt: str,
        base_url: Optional[str] = None,
        tool_display_names: Optional[Dict[str, str]] = None,
        provider: str = 'ollama',
        api_key: Optional[str] = None,
    ):
        self.model_name = model_name
        self.tools = tools
        self.system_prompt = system_prompt
        self.base_url = base_url
        self.tool_display_names = tool_display_names or {}
        # 'ollama' or 'openai' (any OpenAI-compatible endpoint, e.g. DeepSeek, Qwen)
        self.provider = provider
        self.api_key = api_key


class AgentRegistry:
    """
    Agent 注册中心 (单例)
    """
    _agents: Dict[str, AgentConfig] = {}

    @classmethod
    def register(cls, namespace: str, config: AgentConfig):
        if namespace in cls._agents:
            logger.warning(f"Agent namespace '{namespace}' already registered. Overwriting.")
        cls._agents[namespace] = config
        logger.info(f"Registered agent for namespace: {namespace} (provider={config.provider})")

    @classmethod
    def get_config(cls, namespace: str) -> Optional[AgentConfig]:
        return cls._agents.get(namespace)

    @classmethod
    def get_all_namespaces(cls) -> List[str]:
        return list(cls._agents.keys())
