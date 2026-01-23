from django.db import models

class ExampleItem(models.Model):
    """
    Example item model for demonstration.
    Stores random numbers and system logs.
    """
    name = models.CharField(max_length=100, verbose_name="名称")
    value = models.CharField(max_length=255, verbose_name="值")
    item_type = models.CharField(max_length=50, default="general", verbose_name="类型")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "示例项目"
        verbose_name_plural = "示例项目"

    def __str__(self):
        return f"{self.name} ({self.value})"
