#!/bin/bash -e
# CREATED_BY_AGENT
# IntyEval 启动脚本

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

# IntyEval 使用与主应用相同的数据库配置
# 确保数据库迁移已完成
echo "检查数据库迁移状态..."
export PYTHONPATH=.
alembic upgrade head

if [ "$DEV" = true ]; then
  echo "Starting IntyEval in development mode..."
  # 在开发模式下，构建 evaluation 前端
  if [ -f "evaluation/build.sh" ]; then
    echo "构建 evaluation 前端..."
    ./evaluation/build.sh
  fi
  uvicorn eval_app.main:app --host 0.0.0.0 --port 8001 --reload
else
  echo "Starting IntyEval in production mode..."
  uvicorn eval_app.main:app --host 0.0.0.0 --port 8001
fi

