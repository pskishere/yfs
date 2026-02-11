from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 股票实时数据订阅路由: /ws/stock/
    re_path(r'ws/stock/$', consumers.StockConsumer.as_asgi()),
]
