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
                "get_all_stock_data": "获取股票全量数据",
                "get_technical_indicators": "分析技术指标",
                "get_stock_news": "获取新闻资讯",
                "get_fundamental_data": "分析基本面",
                "get_cycle_analysis": "分析周期规律",
                "get_options_data": "获取期权数据",
                "search_stock_symbol": "搜索股票代码",
                "internet_search": "联网搜索"
            }

            AgentRegistry.register(
                namespace="stock",
                config=AgentConfig(
                    model_name="deepseek-v3.2:cloud",
                    tools=STOCKS_TOOLS,
                    system_prompt=ANALYST_PROMPT,
                    tool_display_names=TOOL_DISPLAY_NAMES
                )
            )
            logger.info("Stock agent registered successfully.")
        except ImportError:
            logger.warning("AI framework not found. Stock agent registration skipped.")
