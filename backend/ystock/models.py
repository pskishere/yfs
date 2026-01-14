"""
数据模型模块 - 定义数据库模型
"""
from typing import Dict, Optional

from django.db import models

from .utils import clean_nan_values


class StockAnalysis(models.Model):
    """
    保存单个股票、周期与周期粒度的分析结果以及执行状态
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    symbol = models.CharField(max_length=20, db_index=True)
    duration = models.CharField(max_length=20, default="5y")
    bar_size = models.CharField(max_length=20, default="1 day")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    task_result_id = models.CharField(max_length=128, null=True, blank=True)
    indicators = models.JSONField(null=True, blank=True)
    signals = models.JSONField(null=True, blank=True)
    candles = models.JSONField(null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True)
    ai_analysis = models.TextField(null=True, blank=True)
    ai_prompt = models.TextField(null=True, blank=True)
    model = models.CharField(max_length=128, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    cached_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("symbol", "duration", "bar_size")
        ordering = ("-updated_at",)

    def mark_running(self, task_result_id: Optional[str] = None) -> None:
        """
        将记录标记为运行中，便于接口层避免重复触发
        
        Args:
            task_result_id: 任务结果ID（可选）
        """
        self.status = self.Status.RUNNING
        self.task_result_id = task_result_id
        self.error_message = None
        self.save(update_fields=["status", "task_result_id", "error_message", "updated_at"])

    def mark_success(self, payload: Dict) -> None:
        """
        将分析结果落库并标记成功
        
        Args:
            payload: 包含分析结果的字典
        """
        # 清洗数据中的 NaN/inf 值，确保 JSON 字段有效
        self.indicators = clean_nan_values(payload.get("indicators"))
        self.candles = clean_nan_values(payload.get("candles"))
        self.extra_data = clean_nan_values(payload.get("extra_data"))
        self.ai_analysis = payload.get("ai_analysis")
        self.ai_prompt = payload.get("ai_prompt")
        self.model = payload.get("model")
        self.status = self.Status.SUCCESS
        self.cached_at = payload.get("cached_at")
        self.save()

    def mark_failed(self, message: str) -> None:
        """
        记录错误信息并标记失败
        
        Args:
            message: 错误消息
        """
        self.status = self.Status.FAILED
        self.error_message = message
        self.save(update_fields=["status", "error_message", "updated_at"])


class StockInfo(models.Model):
    """
    缓存股票基本信息（代码与名称）
    """

    symbol = models.CharField(primary_key=True, max_length=20)
    name = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("symbol",)


class ChatSession(models.Model):
    """
    AI 聊天会话模型，用于股票分析对话
    """
    session_id = models.CharField(max_length=100, unique=True, verbose_name='会话ID')
    summary = models.TextField(blank=True, null=True, verbose_name='会话摘要')
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name='模型名称')
    context_symbols = models.JSONField(default=list, blank=True, verbose_name='会话关注的股票代码列表')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'AI聊天会话'
        verbose_name_plural = 'AI聊天会话'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        return f"会话 {self.session_id}"


class ChatMessage(models.Model):
    """
    AI 聊天消息模型，用于存储会话中的消息
    """
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', 'AI助手'),
        ('system', '系统'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('streaming', '生成中'),
        ('completed', '已完成'),
        ('error', '错误'),
        ('cancelled', '已取消'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', verbose_name='会话')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='角色')
    content = models.TextField(verbose_name='消息内容')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', verbose_name='状态')
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='父消息')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    feedback = models.IntegerField(default=0, verbose_name='反馈')  # -1: 点踩, 0: 无, 1: 点赞
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据（如引用的股票代码、指标数据等）')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'AI聊天消息'
        verbose_name_plural = 'AI聊天消息'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['session', 'status']),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
