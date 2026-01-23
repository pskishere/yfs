import logging
from rest_framework import viewsets
from .models import ChatSession
from .serializers import ChatSessionSerializer

logger = logging.getLogger(__name__)

class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    通用聊天会话 ViewSet
    """
    queryset = ChatSession.objects.all().order_by('-updated_at')
    serializer_class = ChatSessionSerializer
    lookup_field = 'session_id'
