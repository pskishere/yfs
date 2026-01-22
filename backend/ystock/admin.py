"""
Django 管理后台模块
"""
from django.contrib import admin

from .models import (
    ChatSession, 
    ChatMessage,
    Stock,
    StockProfile,
    StockQuote,
    StockKLine
)


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """股票基础信息管理"""
    list_display = ("symbol", "name", "exchange", "asset_type", "is_active", "updated_at")
    search_fields = ("symbol", "name")
    list_filter = ("exchange", "asset_type", "is_active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StockProfile)
class StockProfileAdmin(admin.ModelAdmin):
    """股票基本面管理"""
    list_display = ("stock", "sector", "industry", "market_cap", "pe_ratio", "updated_at")
    search_fields = ("stock__symbol", "stock__name", "sector", "industry")
    list_filter = ("sector",)
    readonly_fields = ("updated_at",)


@admin.register(StockQuote)
class StockQuoteAdmin(admin.ModelAdmin):
    """股票实时行情管理"""
    list_display = ("stock", "price", "change_pct", "volume", "updated_at")
    search_fields = ("stock__symbol",)
    readonly_fields = ("updated_at",)


@admin.register(StockKLine)
class StockKLineAdmin(admin.ModelAdmin):
    """股票K线数据管理"""
    list_display = ("stock", "date", "period", "open", "close", "volume")
    list_filter = ("period", "date")
    search_fields = ("stock__symbol",)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """AI 聊天会话管理"""
    list_display = ("session_id", "summary_preview", "message_count", "created_at", "updated_at")
    search_fields = ("session_id", "summary")
    readonly_fields = ("session_id", "created_at", "updated_at")
    list_filter = ("created_at",)
    
    def summary_preview(self, obj):
        """显示摘要预览"""
        if obj.summary:
            return obj.summary[:50] + "..." if len(obj.summary) > 50 else obj.summary
        return "-"
    summary_preview.short_description = "摘要预览"
    
    def message_count(self, obj):
        """显示消息数量"""
        return obj.messages.count()
    message_count.short_description = "消息数"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """AI 聊天消息管理"""
    list_display = ("id", "session", "role", "content_preview", "status", "created_at")
    list_filter = ("role", "status", "created_at")
    search_fields = ("content", "session__session_id")
    readonly_fields = ("created_at", "updated_at")
    
    def content_preview(self, obj):
        """显示内容预览"""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "内容预览"
