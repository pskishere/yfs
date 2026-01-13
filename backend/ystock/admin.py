"""
Django 管理后台模块
"""
from django.contrib import admin

from .models import StockAnalysis, StockInfo, ChatSession, ChatMessage


@admin.register(StockAnalysis)
class StockAnalysisAdmin(admin.ModelAdmin):
    """股票分析记录管理"""
    list_display = ("symbol", "duration", "bar_size", "status", "cached_at", "updated_at")
    list_filter = ("status", "duration", "bar_size")
    search_fields = ("symbol",)
    readonly_fields = ("created_at", "updated_at", "cached_at")


@admin.register(StockInfo)
class StockInfoAdmin(admin.ModelAdmin):
    """股票信息管理"""
    list_display = ("symbol", "name", "updated_at")
    search_fields = ("symbol", "name")
    readonly_fields = ("updated_at",)


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
