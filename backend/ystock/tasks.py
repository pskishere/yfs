"""
后台任务模块 - 异步执行股票分析任务
"""
from django.utils import timezone

from .models import StockAnalysis
from .services import perform_analysis


def run_analysis(record_id: int, symbol: str, duration: str, bar_size: str, use_cache: bool = True) -> dict:
    """
    后台任务：执行单只股票的分析并写入数据库
    
    Args:
        record_id: 分析记录ID
        symbol: 股票代码
        duration: 数据周期
        bar_size: K线周期
        use_cache: 是否使用缓存
        
    Returns:
        任务执行结果字典
    """
    record = StockAnalysis.objects.get(id=record_id)
    try:
        payload, error = perform_analysis(symbol, duration, bar_size, use_cache=use_cache)
        if error:
            raise RuntimeError(error[0].get("message", "分析失败"))
        payload["cached_at"] = timezone.now()
        record.mark_success(payload)
        return {"status": "success", "record_id": record.id}
    except Exception as exc:  # noqa: BLE001
        record.mark_failed(str(exc))
        return {"status": "failed", "record_id": record.id, "error": str(exc)}
