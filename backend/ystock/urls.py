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
    path("institutional/<str:symbol>", views.institutional, name="ystock-institutional"),
    path("insider/<str:symbol>", views.insider, name="ystock-insider"),
    path("recommendations/<str:symbol>", views.recommendations, name="ystock-recommendations"),
    path("earnings/<str:symbol>", views.earnings, name="ystock-earnings"),
    path("news/<str:symbol>", views.news, name="ystock-news"),
    path("options/<str:symbol>", views.options, name="ystock-options"),
    path("comprehensive/<str:symbol>", views.comprehensive, name="ystock-comprehensive"),
    path("all-data/<str:symbol>", views.all_data, name="ystock-all-data"),
    path("stocks/<str:symbol>", views.delete_stock, name="ystock-delete-stock"),
]
