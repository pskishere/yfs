import logging
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import ChatSession
from .serializers import ChatSessionSerializer

logger = logging.getLogger(__name__)

_ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'text/plain', 'text/csv', 'text/markdown',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


class FileUploadView(APIView):
    """
    文件上传接口
    """
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        logger.info(f"FileUploadView received request: FILES={request.FILES.keys()}, DATA={request.data.keys()}")
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size > _MAX_UPLOAD_BYTES:
            return Response({"error": "File too large (max 20 MB)"}, status=status.HTTP_400_BAD_REQUEST)

        content_type = file_obj.content_type or ''
        if content_type not in _ALLOWED_MIME_TYPES:
            return Response({"error": f"File type not allowed: {content_type}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            file_path = default_storage.save(os.path.join('uploads', file_obj.name), ContentFile(file_obj.read()))
            full_path = default_storage.path(file_path)

            return Response({
                "name": file_obj.name,
                "url": request.build_absolute_uri(settings.MEDIA_URL + file_path),
                "path": full_path,
                "size": file_obj.size
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ModelListView(APIView):
    """
    从 AgentRegistry 动态读取已注册的模型列表
    """
    def get(self, request):
        from .registry import AgentRegistry
        models = []
        seen = set()
        for ns in AgentRegistry.get_all_namespaces():
            config = AgentRegistry.get_config(ns)
            if config and config.model_name not in seen:
                seen.add(config.model_name)
                # model_name 格式如 "ollama/deepseek-v3" 或 "claude-sonnet-4-6"
                provider = config.model_name.split("/")[0] if "/" in config.model_name else "anthropic"
                models.append({
                    "id": config.model_name,
                    "name": config.model_name,
                    "provider": provider,
                    "namespace": ns,
                })
        return Response(models)

class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    通用聊天会话 ViewSet
    """
    queryset = ChatSession.objects.all().order_by('-updated_at')
    serializer_class = ChatSessionSerializer
    lookup_field = 'session_id'
