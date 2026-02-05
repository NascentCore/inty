#!/bin/bash -e

DEV=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dev)
      DEV=true
      shift
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
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-${SCRIPT_DIR}/alembic/alembic.ini}"
# 初始化管理员用户 user-01JWZ34Y4D1C92GD86A5R6EWYJ，这个算是预置的用户。
# 所有预置角色均由这个用户创建。也支持管理系统的登录。
# 只能手动运行下面的命令，因为其与后面的 alembic upgrade head 命令冲突。
# 即：init_admin_user.py 需要 users 表存在。所以要先运行 alembic upgrade head。
# 但 alembic upgrade head 需要 init_admin_user.py 运行完成生成的默认管理员 id。
# python scripts/init_admin_user.py
alembic -c "$ALEMBIC_CONFIG" upgrade head

# 初始化订阅计划，写入信息会提供给 app 作为向 google play 查询订阅计划详情到依据。
python scripts/init_subscription_plans_simple.py

if [ "$DEV" = true ]; then
  echo "Starting in dev mode..."
  # 构建 evaluation 前端并拷贝到 app/static/evaluation（CI 中跳过，后端测试不依赖静态资源）
  # CI 由 GitHub Actions 自动设为 true，见：
  # https://docs.github.com/zh/actions/reference/workflows-and-actions/variables
  if [ -z "${CI:-}" ]; then
    echo "Building evaluation frontend..."
    ./evaluation/build.sh
  else
    echo "CI detected, skipping evaluation frontend build."
    echo "CI 环境不需要提供评测 web UI"
  fi
  python scripts/init_admin_user.py --user-id user-testing --is-superuser=true
  python scripts/seed_report_test_data.py
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  echo "Starting in normal mode without reloading..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
