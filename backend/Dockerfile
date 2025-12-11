FROM python:3.14-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Python 镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 设置 protobuf 使用纯 Python 实现（必须在安装前设置）
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# 安装依赖
COPY requirements.txt .
# 先卸载可能存在的 protobuf C 扩展，然后重新安装纯 Python 版本
RUN pip uninstall -y protobuf || true && \
    pip install --no-cache-dir --no-binary protobuf protobuf==4.25.3 && \
    pip install --no-cache-dir -r requirements.txt && \
    find /usr/local/lib/python3.14/site-packages/google/_upb -name "*.so" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.14/site-packages/google/protobuf/pyext -name "*.so" -delete 2>/dev/null || true

# 复制项目
COPY . /app/

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

EXPOSE 8080

# 使用 gunicorn 启动 Django 应用
# workers: CPU核心数 * 2 + 1，这里使用 4 个 worker
# timeout: 300秒，适合 AI 分析等长时间请求
# bind: 监听所有接口的 8080 端口
# access-logfile: 访问日志输出到 stdout
# error-logfile: 错误日志输出到 stderr
# log-level: info 级别日志
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "backend.wsgi:application"]
