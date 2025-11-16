#!/bin/bash -e

DEV=false

# 这个脚本包办了全部的配置文件设置
CONFIG=${INTY_GLOBAL_CONFIG:-"config.yaml"}

function usage() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --dev              Start in development mode with auto-reload"
  echo "  --config PATH      Specify config file path (default: config.yaml)"
  echo "  --help             Show this help message"
  exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dev)
      DEV=true
      shift
      ;;
    --config)
      CONFIG="$2"
      shift 2
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

export PYTHONPATH=.
# 这里重置了环境变量，因为 app/core/config.py 中会读取这个环境变量。
export INTY_GLOBAL_CONFIG="$CONFIG"

echo "Migrating database..."
alembic upgrade head

# 用于记录一个复杂的边角问题：
# 初始化管理员用户 user-01JWZ34Y4D1C92GD86A5R6EWYJ，这个算是预置的用户。
# 所有预置角色均由这个用户创建。也支持管理系统的登录。
# 只能手动运行下面的命令，因为其与后面的 alembic upgrade head 命令冲突。
# 即：init_admin_user.py 需要 users 表存在。所以要先运行 alembic upgrade head。
# 但 alembic upgrade head 需要 init_admin_user.py 运行完成生成的默认管理员 id。
# python scripts/init_admin_user.py

# 初始化订阅计划，写入信息会提供给 app 作为向 google play 查询订阅计划详情到依据。
python scripts/init_subscription_plans_simple.py

if [ "$DEV" = true ]; then
  echo "Starting server in development mode..."
  python scripts/init_admin_user.py --user-id user-testing --is-superuser false
  # 在 CI 环境下下面的命令会导致服务器启动失败
  # ./build_evaluation.sh
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  echo "Starting in normal mode ..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
