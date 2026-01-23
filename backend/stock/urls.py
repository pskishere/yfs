from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'stocks', views.StockAnalysisViewSet, basename='stock-stocks')

urlpatterns = [
    path("", views.index, name="stock-index"),
    path("health", views.health, name="stock-health"),
    path("", include(router.urls)),
]
