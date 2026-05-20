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

            # Provider selection via env:
            #   EXAMPLE_PROVIDER=openai  → OpenAI-compatible (DeepSeek, Qwen, etc.)
            #   EXAMPLE_PROVIDER=ollama  → local Ollama (default)
            provider = os.getenv('EXAMPLE_PROVIDER', 'ollama')

            AgentRegistry.register(
                namespace="example",
                config=AgentConfig(
                    model_name=os.getenv('EXAMPLE_MODEL', 'deepseek-v3.1:671b-cloud'),
                    tools=EXAMPLE_TOOLS,
                    system_prompt=EXAMPLE_AGENT_PROMPT,
                    tool_display_names=TOOL_DISPLAY_NAMES,
                    provider=provider,
                    base_url=os.getenv('EXAMPLE_BASE_URL'),
                    api_key=os.getenv('EXAMPLE_API_KEY'),
                ),
            )
            logger.info(f"Example agent registered (provider={provider}).")
        except ImportError as e:
            logger.warning(f"Example agent registration skipped: {e}")
