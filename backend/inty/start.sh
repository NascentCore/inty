#!/bin/bash -e

DEV=false
TEST=false
API_ONLY=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 当脚本位于 backend/inty 时从仓库根目录运行，以便 alembic/scripts/evaluation 等路径正确；Docker 中 COPY 到 / 时 SCRIPT_DIR=/ 仍 cd /
if [[ -f "$SCRIPT_DIR/../../alembic/alembic.ini" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
  cd "$REPO_ROOT"
else
  REPO_ROOT="$SCRIPT_DIR"
  cd "$REPO_ROOT"
fi

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
    --api-only)
      API_ONLY=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--dev] [--test] [--api-only]"
      echo "  --dev   Dev mode: build evaluation frontend, seed test user/data, uvicorn --reload"
      echo "  --test  Test mode: like --dev but skip evaluation frontend build (e.g. for CI)"
      echo "  --api-only  API only mode: disable serving /evaluation web UI"
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
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-${REPO_ROOT}/alembic/alembic.ini}"
# 初始化管理员用户 user-01JWZ34Y4D1C92GD86A5R6EWYJ，这个算是预置的用户。
# 所有预置角色均由这个用户创建。也支持管理系统的登录。
# 只能手动运行下面的命令，因为其与后面的 alembic upgrade head 命令冲突。
# 即：init_admin_user.py 需要 users 表存在。所以要先运行 alembic upgrade head。
# 但 alembic upgrade head 需要 init_admin_user.py 运行完成生成的默认管理员 id。
# python scripts/init_admin_user.py
alembic -c "$ALEMBIC_CONFIG" upgrade head

# 初始化订阅计划，写入信息会提供给 app 作为向 google play 查询订阅计划详情到依据。
python scripts/init_subscription_plans_simple.py

if [ "$API_ONLY" = true ]; then
  echo "API only mode enabled: /evaluation web UI will not be served."
  export INTY_API_ONLY=true
else
  export INTY_API_ONLY=false
fi

if [ "$DEV" = true ]; then
  if [ "$TEST" = true ]; then
    echo "Starting in test mode (dev backend, skip evaluation frontend build)..."
    echo "Skipping evaluation frontend build in test mode."
  elif [ "$API_ONLY" = true ]; then
    echo "Starting in dev mode with API only enabled..."
    echo "Skipping evaluation frontend build in API only mode."
  else
    echo "Starting in dev mode..."
    echo "Building evaluation frontend..."
    ./evaluation/build.sh
  fi
  python scripts/init_admin_user.py --user-id user-testing --is-superuser=true
  python scripts/seed_report_test_data.py
  uvicorn backend.inty.main:app --host 0.0.0.0 --port 8000 --reload
else
  echo "Starting in normal mode without reloading..."
  uvicorn backend.inty.main:app --host 0.0.0.0 --port 8000
fi
