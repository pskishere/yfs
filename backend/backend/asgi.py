"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# 初始化 Django ASGI 应用
django_asgi_app = get_asgi_application()

# 导入 WebSocket 路由
from ai import routing as ai_routing
from django.conf import settings

_ws_stack = AuthMiddlewareStack(
    URLRouter(ai_routing.websocket_urlpatterns)
)

# DEBUG 环境跳过 Origin 校验，方便本地前端（任意端口）直连
_ws_handler = _ws_stack if settings.DEBUG else AllowedHostsOriginValidator(_ws_stack)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": _ws_handler,
})
