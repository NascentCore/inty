#!/bin/bash -e

DEV=false
TEST=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 当脚本位于 backend/inty 时从仓库根目录运行；Docker 中 COPY 到 / 时 SCRIPT_DIR=/ 仍 cd /
if [[ -f "$SCRIPT_DIR/../../backend/alembic/alembic.ini" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  REPO_ROOT="$SCRIPT_DIR"
fi
cd "$REPO_ROOT"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dev)
      DEV=true
      shift
      ;;
    --test)
      DEV=true
      TEST=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--dev] [--test]"
      echo "  --dev   Dev mode: seed test user/data, uvicorn --reload"
      echo "  --test  Test mode: same as --dev, intended for CI/testing"
      echo "Run from repository root. Default: run migrations and start uvicorn without reload."
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# This is for launching the backend server in docker container.
# You should use docker compose to launch the server locally.

# Run database migrations
echo "Starting database migrations..."
export PYTHONPATH=.
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-${REPO_ROOT}/backend/alembic/alembic.ini}"
# 初始化管理员用户 user-01JWZ34Y4D1C92GD86A5R6EWYJ，这个算是预置的用户。
# 所有预置角色均由这个用户创建。也支持管理系统的登录。
# 只能手动运行下面的命令，因为其与后面的 alembic upgrade head 命令冲突。
# 即：init_admin_user.py 需要 users 表存在。所以要先运行 alembic upgrade head。
# 但 alembic upgrade head 需要 init_admin_user.py 运行完成生成的默认管理员 id。
# python tools/scripts/init_admin_user.py
python -m alembic -c "$ALEMBIC_CONFIG" upgrade head

# 初始化订阅计划，写入信息会提供给 app 作为向 google play 查询订阅计划详情到依据。
python tools/scripts/init_subscription_plans_simple.py

UVICORN_LOG_ARGS=()
if [ -n "${UVICORN_LOG_LEVEL:-}" ]; then
  UVICORN_LOG_ARGS=(--log-level "${UVICORN_LOG_LEVEL}")
fi

if [ "$DEV" = true ]; then
  if [ "$TEST" = true ]; then
    echo "Starting in test mode..."
  else
    echo "Starting in dev mode..."
  fi
  # 生成测试用管理员账号，ops 平台与 inty 后端分离后，这个应该就不需要了，先注释掉保留来做记录。
  # python tools/scripts/init_admin_user.py --user-id user-testing --is-superuser=true
  # 生成测试用户用于本地 app 登陆
  python tools/scripts/create_email_password_user.py --email test@sxwl.ai --password test --yes
  python -m uvicorn backend.inty.main:app --host 0.0.0.0 --port 8000 --reload "${UVICORN_LOG_ARGS[@]}"
else
  echo "Starting in normal mode without reloading..."
  python -m uvicorn backend.inty.main:app --host 0.0.0.0 --port 8000 "${UVICORN_LOG_ARGS[@]}"
fi
