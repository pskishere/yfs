#!/bin/bash
# Docker 容器启动脚本
# 在启动 gunicorn 之前自动运行数据库迁移

set -e

echo "正在运行数据库迁移..."
python manage.py migrate --noinput

echo "启动 gunicorn 服务器..."
exec gunicorn --bind 0.0.0.0:8080 --workers 4 --timeout 300 --access-logfile - --error-logfile - --log-level info backend.wsgi:application
