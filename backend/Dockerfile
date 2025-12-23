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

# 复制启动脚本并设置执行权限
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

EXPOSE 8080

# 使用启动脚本，在启动 gunicorn 之前自动运行数据库迁移
# 使用 bash 执行，避免卷挂载导致的权限问题
ENTRYPOINT ["bash", "/app/entrypoint.sh"]
