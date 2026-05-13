#!/bin/bash -e

LOCAL=false
DEBUG=false
BUILD_FRONTEND=true
LOG_FILE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../../alembic/alembic.ini" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
  cd "$REPO_ROOT"
else
  REPO_ROOT="$SCRIPT_DIR"
  cd "$REPO_ROOT"
fi

while [[ $# -gt 0 ]]; do
  case $1 in
    --local|--dev)
      LOCAL=true
      shift
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    --build-frontend)
      BUILD_FRONTEND=true
      shift
      ;;
    --no-build-frontend)
      BUILD_FRONTEND=false
      shift
      ;;
    --log-file)
      shift
      if [[ $# -eq 0 ]]; then echo "error: --log-file requires a path"; exit 1; fi
      LOG_FILE="$1"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--local|--dev] [--debug] [--log-file PATH] [--build-frontend|--no-build-frontend]"
      echo ""
      echo "  Always (before uvicorn): alembic upgrade head (see ALEMBIC_CONFIG / repo alembic/alembic.ini)."
      echo "  Listen port: \${PORT:-8001}."
      echo ""
      echo "  Flags (any mode):"
      echo "  --debug         Loguru + uvicorn DEBUG (INTY_LOGGING_LEVEL)"
      echo "  --log-file PATH UTF-8 file log at PATH (INTY_LOG_FILE); removed if it already exists at startup."
      echo "                  With --debug: console INFO (INTY_CONSOLE_LOGGING_LEVEL), file DEBUG."
      echo ""
      echo "  Flags (--local|--dev only):"
      echo "  --build-frontend     Run evaluation/build.sh before uvicorn (default: on)"
      echo "  --no-build-frontend  Skip that step; use existing app/static/evaluation"
      echo "  --local|--dev        Seed admin + report fixtures, uvicorn --reload;"
      echo "                       JWT for user-testing -> \${INTY_OPS_BEARER_TOKEN_FILE:-<repo>/.inty_ops_bearer_token}"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"; echo "Use --help for usage"; exit 1
      ;;
  esac
done

echo "Starting database migrations..."
export PYTHONPATH=.
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-${REPO_ROOT}/alembic/alembic.ini}"
alembic -c "$ALEMBIC_CONFIG" upgrade head

OPS_PORT="${PORT:-8001}"

if [ "$DEBUG" = true ]; then
  export INTY_LOGGING_LEVEL=DEBUG
fi

if [ -n "$LOG_FILE" ]; then
  if [[ -e "$LOG_FILE" || -L "$LOG_FILE" ]]; then
    rm -f "$LOG_FILE"
  fi
  export INTY_LOG_FILE="$LOG_FILE"
  if [ "$DEBUG" = true ]; then
    export INTY_CONSOLE_LOGGING_LEVEL=INFO
  fi
fi

UVICORN_LOG_LEVEL=()
if [ "$DEBUG" = true ]; then
  UVICORN_LOG_LEVEL=(--log-level debug)
fi

if [ "$LOCAL" = true ]; then
  if [ "$BUILD_FRONTEND" = true ]; then
    echo "Building evaluation static assets (npm install + build -> app/static/evaluation)..."
    ./evaluation/build.sh
  else
    echo "Skipping evaluation static build (--no-build-frontend)."
  fi

  OPS_BEARER_TOKEN_FILE="${INTY_OPS_BEARER_TOKEN_FILE:-$REPO_ROOT/.inty_ops_bearer_token}"
  echo "创建测试用管理员账户用于在 ops 平台登陆访问"
  python tools/scripts/init_admin_user.py --user-id user-testing --is-superuser=true --token-file "$OPS_BEARER_TOKEN_FILE"
  if ! chmod 600 "$OPS_BEARER_TOKEN_FILE" 2>/dev/null; then
    echo "warning: could not chmod 600 $OPS_BEARER_TOKEN_FILE" >&2
  fi
  echo "本地测试 JWT 已写入: $OPS_BEARER_TOKEN_FILE（可与 INTY_BEARER_TOKEN / INTY_ACCESS_TOKEN 互换使用）"

  echo "Seeding report test data..."
  python tools/scripts/seed_report_test_data.py

  echo "在另外一个 terminal 窗口运行下面的命令来启动评测平台 UI"
  echo "cd evaluation && npm run dev"
  echo "Starting ops backend server in dev mode on port $OPS_PORT..."
  python -m uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT" --reload "${UVICORN_LOG_LEVEL[@]}"
else
  echo "Starting ops in normal mode on port $OPS_PORT..."
  python -m uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT" "${UVICORN_LOG_LEVEL[@]}"
fi
