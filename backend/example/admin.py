from django.contrib import admin
from .models import ExampleItem

@admin.register(ExampleItem)
class ExampleItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'item_type', 'created_at')
    list_filter = ('item_type',)
    search_fields = ('name', 'value')
    readonly_fields = ('created_at', 'updated_at')
