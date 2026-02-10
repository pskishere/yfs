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
                "get_system_status": "查看系统状态"
            }

            AgentRegistry.register(
                namespace="example",
                config=AgentConfig(
                    model_name="deepseek-v3.1:671b-cloud",
                    tools=EXAMPLE_TOOLS,
                    system_prompt=EXAMPLE_AGENT_PROMPT,
                    tool_display_names=TOOL_DISPLAY_NAMES
                )
            )
            logger.info("Example agent registered successfully.")
        except ImportError:
            logger.warning("AI framework not found. Example agent registration skipped.")
