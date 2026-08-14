import logging
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import ChatSession
from .serializers import ChatSessionSerializer

logger = logging.getLogger(__name__)
User = get_user_model()

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


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        if not username or not password:
            return Response({'error': '用户名和密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 6:
            return Response({'error': '密码至少6位'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'error': '用户名已存在'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=username, password=password)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'username': user.username,
        }, status=status.HTTP_201_CREATED)


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        logger.info(f"FileUploadView received request: FILES={request.FILES.keys()}")
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
                "size": file_obj.size,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModelListView(APIView):
    def get(self, request):
        from .registry import AgentRegistry
        models = []
        seen = set()
        for ns in AgentRegistry.get_all_namespaces():
            config = AgentRegistry.get_config(ns)
            if config and config.model_name not in seen:
                seen.add(config.model_name)
                provider = config.model_name.split("/")[0] if "/" in config.model_name else "anthropic"
                models.append({
                    "id": config.model_name,
                    "name": config.model_name,
                    "provider": provider,
                    "namespace": ns,
                })
        return Response(models)


class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    lookup_field = 'session_id'

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
