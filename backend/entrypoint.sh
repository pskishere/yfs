#!/bin/bash
# Docker 容器启动脚本
# 在启动 daphne 之前自动运行数据库迁移

set -e

echo "等待 Redis 就绪..."
until nc -z redis 6379; do
    echo "等待 Redis..."
    sleep 2
done
echo "✓ Redis 已就绪"

echo "检查本地 Ollama 服务..."
if curl -s http://host.docker.internal:11434/api/tags > /dev/null 2>&1; then
    echo "✓ 本地 Ollama 服务可访问"
else
    echo "⚠️  警告: 本地 Ollama 服务不可访问"
    echo "   请确保本地 Ollama 正在运行: ollama serve"
    echo "   继续启动，但 AI 聊天功能可能不可用"
fi

echo "正在运行数据库迁移..."
python manage.py migrate --noinput

echo "正在收集静态文件..."
python manage.py collectstatic --noinput || true

echo "启动 Daphne ASGI 服务器（支持 WebSocket）..."
exec daphne -b 0.0.0.0 -p 8080 backend.asgi:application
