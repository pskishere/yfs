"""
视图模块 - 处理 HTTP 请求和响应
使用 Django REST Framework ViewSets 重构
"""
import logging
from typing import Any, Dict

from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Stock
from .services import (
    perform_analysis,
    fetch_options,
    search_stocks as service_search_stocks,
)
from .utils import clean_nan_values

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """
    健康检查接口
    """
    return Response({
        "status": "ok",
        "service": "django-stock",
        "timestamp": timezone.now().isoformat(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def index(request):
    """
    首页列出可用接口
    """
    return Response({
        "service": "stock-api",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "stocks": "/api/stocks/ (include analyze, refresh, status, options, delete)",
            "subscriptions": "/api/stocks/subscriptions/",
            "search": "/api/stocks/search/?q=<query>",
        }
    })


class StockAnalysisViewSet(viewsets.ViewSet):
    """
    股票分析 ViewSet (无状态，实时计算)
    处理分析、刷新、状态查询、删除等操作
    """
    lookup_field = 'symbol'
    # 允许 symbol 包含特殊字符（虽然一般股票代码没有）
    lookup_value_regex = '[^/]+'

    def retrieve(self, request, symbol=None):
        """
        获取分析结果 (对应 /api/stocks/<symbol>/)
        支持 modules 参数过滤返回字段:
        - chart: 包含 K线数据 (candles)
        - cycle: 包含周期分析 (indicators)
        - technical: 包含技术指标 (indicators)
        默认: 包含所有数据
        """
        symbol = symbol.upper()
        duration = request.query_params.get("duration", "5y")
        bar_size = request.query_params.get("bar_size", "1 day")

        result, error = perform_analysis(symbol, duration, bar_size, use_cache=True)
        if error:
            return Response(clean_nan_values(error[0]), status=error[1])
        
        data = result
        
        # 处理 modules 参数过滤
        modules = request.query_params.get('modules', '').lower()
        if modules:
            module_list = modules.split(',')
            
            # 如果不包含 chart，移除 candles
            if 'chart' not in module_list and 'k线' not in module_list and '图表' not in module_list:
                data.pop('candles', None)
                
            # 如果不包含 chart, cycle, technical，移除 indicators
            # 注意: CycleAnalysis 组件需要 indicators 中的周期数据
            needed_indicators = {'chart', 'k线', '图表', 'cycle', '周期', 'technical', '技术', '技术分析'}
            if not any(m in needed_indicators for m in module_list):
                data.pop('indicators', None)

        return Response(data)

    @action(detail=True, methods=['post'], url_path='refresh')
    def refresh_analysis(self, request, symbol=None):
        """
        强制刷新分析 (对应 /api/refresh-analyze/<symbol>)
        """
        symbol = symbol.upper()
        duration = request.query_params.get("duration", "5y")
        bar_size = request.query_params.get("bar_size", "1 day")
        
        result, error = perform_analysis(symbol, duration, bar_size, use_cache=False)
        if error:
            return Response(clean_nan_values(error[0]), status=error[1])
            
        return Response(result)

    @action(detail=True, methods=['get'], url_path='status')
    def analysis_status(self, request, symbol=None):
        """
        查询状态 (对应 /api/analysis-status/<symbol>)
        现在直接返回分析结果，因为计算是实时的
        """
        return self.retrieve(request, symbol)

    @action(detail=True, methods=['get'])
    def options(self, request, symbol=None):
        """
        获取期权数据 (对应 /api/options/<symbol>)
        """
        symbol = symbol.upper()
        try:
            data = fetch_options(symbol)
            if not data:
                return Response({
                    "success": True, 
                    "symbol": symbol, 
                    "data": None, 
                    "message": f"{symbol} 没有期权数据"
                })
            return Response({"success": True, "symbol": symbol, "data": data})
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, symbol=None):
        """
        删除股票数据 (对应 /api/stocks/<symbol>)
        """
        symbol = symbol.upper()
        # 删除 Stock 会级联删除 Profile, Quote, KLine
        deleted_count, _ = Stock.objects.filter(symbol=symbol).delete()
        return Response({
            "success": True,
            "symbol": symbol,
            "deleted_count": deleted_count,
        })

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request):
        """
        订阅股票 (对应 /api/stocks/subscriptions)
        返回所有活跃的股票
        """
        # 使用 updated_at 排序
        stocks_qs = Stock.objects.all().order_by("-updated_at")
        stocks = []
        for s in stocks_qs:
            stocks.append({
                "symbol": s.symbol,
                "name": s.name,
                "category": "已订阅",
            })
        return Response({"success": True, "count": len(stocks), "stocks": stocks})

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        搜索股票 (对应 /api/search)
        """
        query = request.query_params.get("q", "").strip()
        try:
            results = service_search_stocks(query)
            return Response({"success": True, "query": query, "results": results})
        except Exception as exc:
            logger.error(f"搜索股票失败: {query}, 错误: {exc}")
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
