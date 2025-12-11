#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="$ROOT_DIR/../.venv/bin/activate"
ENV_FILE="$ROOT_DIR/.env"
SITE_CUSTOMIZE=""

# ensure_protobuf_env: 确保 protobuf 在当前环境中使用纯 Python 实现，避免 C 扩展与新版 Python 不兼容。
ensure_protobuf_env() {
  export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
  export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=2

  if [ -f "$ENV_FILE" ]; then
    if ! grep -q "^PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python" "$ENV_FILE"; then
      echo "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python" >> "$ENV_FILE"
    fi
    if ! grep -q "^PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=2" "$ENV_FILE"; then
      echo "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=2" >> "$ENV_FILE"
    fi
  else
    echo "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python" > "$ENV_FILE"
    echo "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=2" >> "$ENV_FILE"
  fi
}

# locate_site_packages: 发现虚拟环境 site-packages 路径，用于写入 sitecustomize.py。
locate_site_packages() {
  if [ -f "$VENV_PATH" ]; then
    # shellcheck disable=SC1090
    source "$VENV_PATH"
  else
    echo "未找到虚拟环境：$VENV_PATH"
    return 1
  fi

  SITE_CUSTOMIZE=$(python - <<'PY'
import site
paths = site.getsitepackages() or []
print(paths[0] if paths else "")
PY
)
  if [ -z "$SITE_CUSTOMIZE" ]; then
    echo "无法定位 site-packages 路径"
    return 1
  fi
  SITE_CUSTOMIZE="$SITE_CUSTOMIZE/sitecustomize.py"
}

# write_sitecustomize: 写入强制环境变量的 sitecustomize，确保最早生效。
write_sitecustomize() {
  if [ -z "$SITE_CUSTOMIZE" ]; then
    echo "sitecustomize 路径未准备好"
    return 1
  fi

  cat > "$SITE_CUSTOMIZE" <<'PY'
import os
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION", "2")
PY
}

# reinstall_protobuf: 重新安装 protobuf，强制使用纯源码安装，避免 C 扩展构建。
reinstall_protobuf() {
  if [ -f "$VENV_PATH" ]; then
    # shellcheck disable=SC1090
    source "$VENV_PATH"
  else
    echo "未找到虚拟环境：$VENV_PATH"
    return 1
  fi

  pip install --no-binary=:all: --no-cache-dir --force-reinstall protobuf==4.25.3
}

# remove_upb_binaries: 删除 upb 二进制模块，确保不会被错误加载。
remove_upb_binaries() {
  if [ -z "$SITE_CUSTOMIZE" ]; then
    return 0
  fi
  local base_dir
  base_dir="$(dirname "$SITE_CUSTOMIZE")"
  find "$base_dir" -name "_message*.so" -delete 2>/dev/null || true
  find "$base_dir" -path "*/google/_upb/*" -type f -delete 2>/dev/null || true
}

# main: 执行环境修复。
main() {
  ensure_protobuf_env
  locate_site_packages
  write_sitecustomize
  reinstall_protobuf
  remove_upb_binaries
  echo "环境修复完成，可重新运行 django 命令。"
}

main "$@"

