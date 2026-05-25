import os
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ExampleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'example'

    def ready(self):
        try:
            from ai.registry import AgentRegistry, AgentConfig
            from .tools import EXAMPLE_TOOLS
            from .prompts import EXAMPLE_AGENT_PROMPT

            TOOL_DISPLAY_NAMES = {
                "get_random_number": "生成随机数",
                "get_system_status": "查看系统状态",
            }

            # model_name 使用 LiteLLM 命名规范，通过环境变量覆盖：
            #   LLM_MODEL=claude-sonnet-4-6               → Anthropic
            #   LLM_MODEL=gpt-4o                          → OpenAI
            #   LLM_MODEL=deepseek/deepseek-chat          → DeepSeek API
            #   LLM_MODEL=ollama/deepseek-v3.1:671b-cloud → Ollama（默认）
            _model = os.getenv('LLM_MODEL', 'ollama/deepseek-v3.1:671b-cloud')
            AgentRegistry.register(
                namespace="example",
                config=AgentConfig(
                    model_name=_model,
                    tools=EXAMPLE_TOOLS,
                    system_prompt=EXAMPLE_AGENT_PROMPT,
                    tool_display_names=TOOL_DISPLAY_NAMES,
                    base_url=os.getenv('LLM_BASE_URL') or (
                        os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
                        if _model.startswith('ollama/')
                        else None
                    ),
                    api_key=os.getenv('LLM_API_KEY'),
                    # 语义记忆：设 LLM_VECTOR_MEMORY=true 启用
                    enable_vector_memory=os.getenv('LLM_VECTOR_MEMORY', 'false').lower() == 'true',
                    # 自我修正示例（取消注释即启用）：
                    # critic_prompt="你是质量评估员。检查回复是否完整准确。不合格回复 'RETRY: <原因>'，合格回复 'PASS'。",
                ),
            )
            logger.info("Example agent registered.")
        except ImportError as e:
            logger.warning(f"Example agent registration skipped: {e}")
