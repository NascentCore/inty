#!/bin/bash -e

# 脚本所在目录的绝对路径：BASH_SOURCE[0] 为当前脚本路径，dirname 取目录，cd 再 pwd 得到绝对路径。
# 本地：脚本在 backend/push_worker/，SCRIPT_DIR 为仓库内该目录的绝对路径。
# Docker：Dockerfile 将本脚本 COPY 到镜像根目录，CMD 执行 /start.sh，故 SCRIPT_DIR=/。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 从 SCRIPT_DIR 向上查找包含 backend/alembic/alembic.ini 的目录作为仓库根 ROOT。
# 本地：backend/push_worker 下无 backend/alembic/，循环上一级到仓库根即找到。
# Docker：脚本在 /，镜像中已有 /backend/alembic/alembic.ini，ROOT 保持为 /。
ROOT="$SCRIPT_DIR"
while [ ! -f "$ROOT/backend/alembic/alembic.ini" ] && [ "$ROOT" != "/" ]; do
  ROOT="$(cd "$ROOT/.." && pwd)"
done
if [ ! -f "$ROOT/backend/alembic/alembic.ini" ]; then
  echo "ERROR: backend/alembic/alembic.ini not found (searched from $SCRIPT_DIR)"
  exit 1
fi
cd "$ROOT"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --help|-h)
      echo "Usage: $0 [--help]"
      echo "  Run DB migrations then start the push worker (local or Docker)."
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# For launching the push worker service (local or Docker).

# Run database migrations
echo "Starting database migrations..."
export PYTHONPATH=.
# TODO(INTY_CONFIG_YAML): require or inherit env from caller/CI (e.g. devops/config.yaml.test); no implicit default
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-$ROOT/backend/alembic/alembic.ini}"
python -m alembic -c "$ALEMBIC_CONFIG" upgrade head


# 启动推送服务
echo "Starting push worker service..."
python -m backend.push_worker.main
