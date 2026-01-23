from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ChatSessionViewSet, ModelListView

router = SimpleRouter()
router.register(r'sessions', ChatSessionViewSet)

urlpatterns = [
    path('models/', ModelListView.as_view(), name='model-list'),
    path('', include(router.urls)),
]
