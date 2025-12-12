"""
Django 管理后台模块
"""
from django.contrib import admin

from .models import StockAnalysis, StockInfo


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
