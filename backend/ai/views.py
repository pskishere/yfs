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
        
        # 简单保存到 media 目录 (需配置 MEDIA_ROOT)
        # 这里为了演示，假设 MEDIA_ROOT 已配置或使用默认
        # 实际生产环境建议使用对象存储
        
        try:
            # 确保目录存在
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            file_path = default_storage.save(os.path.join('uploads', file_obj.name), ContentFile(file_obj.read()))
            full_path = default_storage.path(file_path)
            
            # 返回文件信息
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
    获取可用 AI 模型列表
    """
    def get(self, request):
        models = [
            {"id": "deepseek-v3.1:671b-cloud", "name": "DeepSeek V3.1 (671B)", "provider": "DeepSeek"},
            {"id": "deepseek-v3.2:cloud", "name": "DeepSeek V3.2 (Cloud)", "provider": "DeepSeek"},
            {"id": "gpt-oss:120b-cloud", "name": "GPT-OSS 120B (Cloud)", "provider": "OpenAI"}
        ]
        return Response(models)

class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    通用聊天会话 ViewSet
    """
    queryset = ChatSession.objects.all().order_by('-updated_at')
    serializer_class = ChatSessionSerializer
    lookup_field = 'session_id'
