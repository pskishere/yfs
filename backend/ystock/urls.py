from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'stocks', views.StockAnalysisViewSet, basename='ystock-stocks')
router.register(r'chat/sessions', views.ChatSessionViewSet, basename='ystock-chat-sessions')

urlpatterns = [
    path("", views.index, name="ystock-index"),
    path("health", views.health, name="ystock-health"),
    path("", include(router.urls)),
]
