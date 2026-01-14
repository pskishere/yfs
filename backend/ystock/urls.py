from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="ystock-index"),
    path("health", views.health, name="ystock-health"),
    path("analyze/<str:symbol>", views.analyze, name="ystock-analyze"),
    path("refresh-analyze/<str:symbol>", views.refresh_analyze, name="ystock-refresh"),
    path("ai-analyze/<str:symbol>", views.ai_analyze, name="ystock-ai"),
    path("hot-stocks", views.hot_stocks, name="ystock-hot"),
    path("indicator-info", views.indicator_info, name="ystock-indicator-info"),
    path("analysis-status/<str:symbol>", views.analysis_status, name="ystock-analysis-status"),
    path("fundamental/<str:symbol>", views.fundamental, name="ystock-fundamental"),
    path("options/<str:symbol>", views.options, name="ystock-options"),
    path("news/<str:symbol>", views.news, name="ystock-news"),
    path("stocks/<str:symbol>", views.delete_stock, name="ystock-delete-stock"),
    
    # AI 聊天会话管理
    path("chat/sessions", views.chat_sessions, name="ystock-chat-sessions"),
    path("chat/sessions/<str:session_id>", views.chat_session_detail, name="ystock-chat-session-detail"),
    path("chat/sessions/<str:session_id>/delete", views.delete_chat_session, name="ystock-delete-chat-session"),
]
