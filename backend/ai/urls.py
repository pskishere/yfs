from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ChatSessionViewSet

router = SimpleRouter()
router.register(r'sessions', ChatSessionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
