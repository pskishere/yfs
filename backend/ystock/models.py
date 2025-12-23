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
        self.signals = clean_nan_values(payload.get("signals"))
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
