from rest_framework import serializers
from .models import ChatSession, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    """
    聊天消息序列化器
    """
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'status', 'thoughts', 'error_message', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """
    聊天会话序列化器
    """
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ['session_id', 'title', 'summary', 'message_count', 'last_message', 'created_at', 'updated_at']
        read_only_fields = ['session_id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'role': last_msg.role,
                'content': last_msg.content[:100],
                'created_at': last_msg.created_at.isoformat()
            }
        return None


class ChatSessionDetailSerializer(serializers.ModelSerializer):
    """
    聊天会话详情序列化器（包含消息列表）
    """
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['session_id', 'title', 'summary', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['session_id', 'created_at', 'updated_at']
