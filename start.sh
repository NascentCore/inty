#!/bin/bash -e

DEV=false

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
# 初始化管理员用户 user-01JWZ34Y4D1C92GD86A5R6EWYJ，这个算是预置的用户。
# 所有预置角色均由这个用户创建。也支持管理系统的登录。
# 只能手动运行下面的命令，因为其与后面的 alembic upgrade head 命令冲突。
# 即：init_admin_user.py 需要 users 表存在。所以要先运行 alembic upgrade head。
# 但 alembic upgrade head 需要 init_admin_user.py 运行完成生成的默认管理员 id。
# python scripts/init_admin_user.py
alembic upgrade head

# 初始化订阅计划，写入信息会提供给 app 作为向 google play 查询订阅计划详情到依据。
python scripts/init_subscription_plans_simple.py

if [ "$DEV" = true ]; then
  echo "Starting in development mode..."
  python scripts/init_admin_user.py --user-id user-testing --is-superuser false
  ./build_evaluation.sh
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  echo "Starting in normal mode without reloading..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
