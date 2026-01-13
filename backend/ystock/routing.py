"""
WebSocket 路由配置
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/stock-chat/<str:session_id>/', consumers.StockChatConsumer.as_asgi()),
    path('ws/stock-chat/', consumers.StockChatConsumer.as_asgi()),  # 支持不提供 session_id 的情况
]
