from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class StockConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stock'

    def ready(self):
        try:
            from ai.registry import AgentRegistry, AgentConfig
            from .tools import STOCKS_TOOLS
            from .prompts import ANALYST_PROMPT

            # 定义工具显示名称映射
            TOOL_DISPLAY_NAMES = {
                "get_stock_data": "获取股票数据",
                "search_stock_symbol": "搜索股票代码",
                "internet_search": "联网搜索",
                "load_document": "加载本地文档",
            }

            AgentRegistry.register(
                namespace="stock",
                config=AgentConfig(
                    model_name="deepseek-v3.1:671b-cloud",
                    tools=STOCKS_TOOLS,
                    system_prompt=ANALYST_PROMPT,
                    tool_display_names=TOOL_DISPLAY_NAMES
                )
            )
            logger.info("Stock agent registered successfully.")
        except ImportError as e:
            logger.warning(f"AI framework not found or import error in tools/prompts: {e}. Stock agent registration skipped.")
        except Exception as e:
            logger.error(f"Failed to register stock agent: {e}")
