"""
CORS 中间件模块 - 处理跨域请求
"""
from django.http import HttpRequest, HttpResponse


class SimpleCorsMiddleware:
    """
    极简 CORS 中间件，允许所有来源，适合本地开发
    """

    def __init__(self, get_response):
        """
        初始化中间件
        
        Args:
            get_response: Django 的 get_response 函数
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求，添加 CORS 头
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            HTTP 响应对象
        """
        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

