import uuid
from django.db import models

class ChatSession(models.Model):
    """
    通用 AI 聊天会话模型
    """
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4, verbose_name='会话ID')
    title = models.CharField(max_length=200, null=True, blank=True, verbose_name="会话标题")
    summary = models.TextField(null=True, blank=True, verbose_name="会话摘要")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "聊天会话"
        verbose_name_plural = "聊天会话"

    def __str__(self):
        return self.session_id


class ChatMessage(models.Model):
    """
    通用聊天消息记录
    """
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', verbose_name="所属会话")
    role = models.CharField(max_length=20, choices=Role.choices, verbose_name="角色")
    content = models.TextField(verbose_name="消息内容")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS, verbose_name="状态")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    thoughts = models.JSONField(null=True, blank=True, verbose_name="思维链")
    metadata = models.JSONField(null=True, blank=True, verbose_name="元数据")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ("created_at",)
        verbose_name = "聊天消息"
        verbose_name_plural = "聊天消息"

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "thoughts": self.thoughts,
            "error_message": self.error_message,
        }
