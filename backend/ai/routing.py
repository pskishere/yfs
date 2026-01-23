"""
WebSocket 路由配置
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 通用 AI 聊天路由: /ws/chat/<namespace>/<session_id>/
    # namespace: 业务命名空间 (如 stock)
    # session_id: 会话 ID
    re_path(r'ws/chat/(?P<namespace>\w+)/(?P<session_id>[\w-]+)/$', consumers.AIChatConsumer.as_asgi()),
]
