from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AgentConfig:
    """
    Agent 配置对象。

    model_name 遵循 LiteLLM 命名规范：
      Ollama 本地：  "ollama/deepseek-v3.1:671b-cloud"
      Anthropic：   "claude-sonnet-4-6"
      OpenAI：      "gpt-4o"
      DeepSeek API："deepseek/deepseek-chat"
      自定义接口：   "openai/model-name"（配合 base_url）
    """

    def __init__(
        self,
        model_name: str,
        tools: List[Any],
        system_prompt: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tool_display_names: Optional[Dict[str, str]] = None,
        litellm_params: Optional[Dict[str, Any]] = None,
        # 语义记忆：启用后历史消息按相关性检索而非截断
        enable_vector_memory: bool = False,
        # 自我修正：提供 critic 提示词后每次生成都会评估并重试
        critic_prompt: Optional[str] = None,
        max_correction_retries: int = 2,
        # 多 Agent 路由：填入子命名空间列表后此 namespace 变为 Supervisor
        sub_namespaces: Optional[List[str]] = None,
    ):
        self.model_name = model_name
        self.tools = tools
        self.system_prompt = system_prompt
        self.base_url = base_url
        self.api_key = api_key
        self.tool_display_names = tool_display_names or {}
        self.litellm_params = litellm_params or {}
        self.enable_vector_memory = enable_vector_memory
        self.critic_prompt = critic_prompt
        self.max_correction_retries = max_correction_retries
        self.sub_namespaces = sub_namespaces or []


class AgentRegistry:
    """Agent 注册中心（单例）"""

    _agents: Dict[str, AgentConfig] = {}

    @classmethod
    def register(cls, namespace: str, config: AgentConfig):
        if namespace in cls._agents:
            logger.warning(f"Namespace '{namespace}' already registered. Overwriting.")
        cls._agents[namespace] = config
        logger.info(f"Registered agent: namespace={namespace} model={config.model_name}")

    @classmethod
    def get_config(cls, namespace: str) -> Optional[AgentConfig]:
        return cls._agents.get(namespace)

    @classmethod
    def get_all_namespaces(cls) -> List[str]:
        return list(cls._agents.keys())
