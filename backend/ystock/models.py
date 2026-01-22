"""
数据模型模块 - 定义数据库模型
"""
from typing import Dict, Optional

from django.db import models
from django.utils import timezone

from .utils import clean_nan_values


class Stock(models.Model):
    """
    股票基础信息表 (核心索引表)
    仅存储最基础的身份信息，用于外键关联
    """
    symbol = models.CharField(primary_key=True, max_length=20, verbose_name="股票代码")
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="股票名称")
    exchange = models.CharField(max_length=50, null=True, blank=True, verbose_name="交易所")
    asset_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="资产类型")  # EQUITY, ETF
    is_active = models.BooleanField(default=True, verbose_name="是否有效")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收录时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ("symbol",)
        verbose_name = "股票基础信息"
        verbose_name_plural = "股票基础信息"

    def __str__(self):
        return f"{self.symbol} ({self.name})"


class StockProfile(models.Model):
    """
    股票基本面与详细资料表
    存储变化频率较低的数据（行业、简介、财务摘要等）
    """
    stock = models.OneToOneField(Stock, on_delete=models.CASCADE, related_name='profile', verbose_name="股票")
    
    # 核心筛选字段 (独立列，方便 SQL 查询和排序)
    sector = models.CharField(max_length=100, null=True, blank=True, db_index=True, verbose_name="板块")
    industry = models.CharField(max_length=100, null=True, blank=True, db_index=True, verbose_name="细分行业")
    market_cap = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="市值")
    pe_ratio = models.FloatField(null=True, blank=True, verbose_name="市盈率(TTM)")
    forward_pe = models.FloatField(null=True, blank=True, verbose_name="预测市盈率")
    employees = models.IntegerField(null=True, blank=True, verbose_name="员工数")
    website = models.URLField(null=True, blank=True, verbose_name="公司官网")
    
    # 完整数据存储 (使用 JSON 保存所有字段，防止遗漏)
    description = models.TextField(null=True, blank=True, verbose_name="公司简介")
    raw_info = models.JSONField(null=True, blank=True, verbose_name="原始Info数据")
    financial_data = models.JSONField(null=True, blank=True, verbose_name="结构化财务数据")
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name="上次更新时间")

    class Meta:
        verbose_name = "股票基本面"
        verbose_name_plural = "股票基本面"

    def is_stale(self, hours: int = 24) -> bool:
        """检查数据是否过期"""
        return (timezone.now() - self.updated_at).total_seconds() > hours * 3600


class StockQuote(models.Model):
    """
    股票实时行情表
    存储高频更新的价格数据
    """
    stock = models.OneToOneField(Stock, on_delete=models.CASCADE, related_name='quote', verbose_name="股票")
    
    price = models.FloatField(verbose_name="当前价格")
    change = models.FloatField(null=True, blank=True, verbose_name="涨跌额")
    change_pct = models.FloatField(null=True, blank=True, verbose_name="涨跌幅(%)")
    volume = models.BigIntegerField(null=True, blank=True, verbose_name="成交量")
    prev_close = models.FloatField(null=True, blank=True, verbose_name="昨收")
    open_price = models.FloatField(null=True, blank=True, verbose_name="开盘")
    day_high = models.FloatField(null=True, blank=True, verbose_name="最高")
    day_low = models.FloatField(null=True, blank=True, verbose_name="最低")
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name="行情时间")

    class Meta:
        verbose_name = "股票实时行情"
        verbose_name_plural = "股票实时行情"

    def is_stale(self, minutes: int = 1) -> bool:
        """检查行情是否过期"""
        return (timezone.now() - self.updated_at).total_seconds() > minutes * 60


class StockKLine(models.Model):
    """
    股票K线数据 (支持多周期)
    """
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='klines', verbose_name="股票")
    date = models.DateTimeField(db_index=True, verbose_name="时间")
    period = models.CharField(max_length=10, default="1d", db_index=True, verbose_name="周期")
    
    open = models.FloatField(verbose_name="开盘价")
    high = models.FloatField(verbose_name="最高价")
    low = models.FloatField(verbose_name="最低价")
    close = models.FloatField(verbose_name="收盘价")
    volume = models.BigIntegerField(verbose_name="成交量")
    
    class Meta:
        verbose_name = "股票K线"
        verbose_name_plural = verbose_name
        unique_together = ("stock", "date", "period")
        indexes = [
            models.Index(fields=['stock', 'period', 'date']),
        ]

    def __str__(self):
        return f"{self.stock.symbol} - {self.period} - {self.date}"



class ChatSession(models.Model):
    """
    AI 聊天会话模型，用于股票分析对话
    """
    session_id = models.CharField(max_length=100, unique=True, verbose_name='会话ID')
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
    聊天消息记录
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
