from django.tasks import task
from django.utils import timezone

from .models import StockAnalysis
from .services import perform_analysis


@task()
def run_analysis(record_id: int, symbol: str, duration: str, bar_size: str, use_cache: bool = True) -> dict:
    """
    后台任务：执行单只股票的分析并写入数据库
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
