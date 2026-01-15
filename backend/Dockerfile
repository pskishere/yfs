FROM python:3.14-slim

WORKDIR /app

# 配置 Debian 镜像源（使用阿里云镜像）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; \
    fi

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libffi-dev \
        curl \
        netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Python 镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 设置 protobuf 使用纯 Python 实现（必须在安装前设置）
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目
COPY . /app/

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

EXPOSE 8080

CMD ["bash", "-lc", "set -e; echo '等待 Redis 就绪...'; until nc -z redis 6379; do echo '等待 Redis...'; sleep 2; done; echo '✓ Redis 已就绪'; if curl -s http://host.docker.internal:11434/api/tags > /dev/null 2>&1; then echo '✓ 本地 Ollama 服务可访问'; else echo '⚠️  警告: 本地 Ollama 服务不可访问'; echo '   请确保本地 Ollama 正在运行: ollama serve'; echo '   继续启动，但 AI 聊天功能可能不可用'; fi; echo '正在运行数据库迁移...'; python manage.py migrate --noinput; echo '正在收集静态文件...'; python manage.py collectstatic --noinput || true; echo '启动 Daphne ASGI 服务器（支持 WebSocket）...'; exec daphne -b 0.0.0.0 -p 8080 backend.asgi:application"]
