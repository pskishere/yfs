"""
Django 管理后台模块
"""
from django.contrib import admin

from .models import (
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
