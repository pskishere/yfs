import logging
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ChatSession
from .serializers import ChatSessionSerializer

logger = logging.getLogger(__name__)

class ModelListView(APIView):
    """
    获取可用 AI 模型列表
    """
    def get(self, request):
        models = [
            {"id": "deepseek-v3.1:671b-cloud", "name": "DeepSeek V3.1 (671B)", "provider": "DeepSeek"},
            {"id": "deepseek-v3.2:cloud", "name": "DeepSeek V3.2 (Cloud)", "provider": "DeepSeek"},
            {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
            {"id": "qwen3:32b", "name": "Qwen3 32B", "provider": "Alibaba"},
        ]
        return Response(models)

class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    通用聊天会话 ViewSet
    """
    queryset = ChatSession.objects.all().order_by('-updated_at')
    serializer_class = ChatSessionSerializer
    lookup_field = 'session_id'
