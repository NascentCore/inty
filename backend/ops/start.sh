#!/bin/bash -e

LOCAL=false
DEBUG=false
BUILD_FRONTEND=true
WORKSPACE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../../backend/alembic/alembic.ini" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  REPO_ROOT="$SCRIPT_DIR"
fi
cd "$REPO_ROOT"

print_usage() {
  cat <<EOF
Usage: $0 [--local|--dev] [--debug] [--workspace DIR] [--build-frontend|--no-build-frontend]

  Ops (uvicorn backend.ops.main:app). Repo cwd is set to REPO_ROOT before migrations and server.

  Always (before uvicorn): alembic upgrade head (see ALEMBIC_CONFIG / backend/alembic/alembic.ini).
  Listen port: \${PORT:-8001}.

  Environment (common):
    INTY_CONFIG_YAML   Config path relative to repo root (e.g. devops/config.yaml.local).
    INTY_OPS_BEARER_TOKEN_FILE  Where to write the local JWT in --local mode (default: <repo>/.inty_ops_bearer_token).
    .inty-user-testing-agent-id  Local user-testing agent id written in --local mode.

  Flags (any mode):
    --debug              Loguru + uvicorn DEBUG (INTY_LOGGING_LEVEL).
    --workspace DIR      Local working directory for file log DIR/inty.log (INTY_LOG_FILE); default DIR is .inty under repo root.
                         Existing log file is removed at startup. With --debug: console INFO, file DEBUG.

  Flags (--local|--dev only):
    --local|--dev        Seed admin + report fixtures; uvicorn --reload; write JWT and agent id for user-testing.
    --build-frontend     Run evaluation/build.sh before uvicorn (default: on).
    --no-build-frontend  Skip that step; use existing app/static/evaluation.

  There is no --log-file; use --workspace DIR if you need logs outside the default .inty directory.
EOF
}

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
    --workspace)
      shift
      if [[ $# -eq 0 ]]; then echo "error: --workspace requires a directory path"; exit 1; fi
      WORKSPACE="$1"
      shift
      ;;
    --help|-h)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      print_usage >&2
      exit 1
      ;;
  esac
done

WORKSPACE="${WORKSPACE:-.inty}"
mkdir -p "$WORKSPACE"
LOG_FILE="$WORKSPACE/inty.log"

echo "Starting database migrations..."
export PYTHONPATH=.
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-${REPO_ROOT}/backend/alembic/alembic.ini}"
alembic -c "$ALEMBIC_CONFIG" upgrade head

OPS_PORT="${PORT:-8001}"

if [ "$DEBUG" = true ]; then
  export INTY_LOGGING_LEVEL=DEBUG
fi

if [[ -e "$LOG_FILE" || -L "$LOG_FILE" ]]; then
  rm -f "$LOG_FILE"
fi
export INTY_LOG_FILE="$LOG_FILE"
if [ "$DEBUG" = true ]; then
  export INTY_CONSOLE_LOGGING_LEVEL=INFO
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
  USER_TESTING_AGENT_ID_FILE="$REPO_ROOT/.inty-user-testing-agent-id"
  echo "创建测试用管理员账户用于在 ops 平台登陆访问"
  python tools/scripts/init_admin_user.py --user-id user-testing --is-superuser=true --token-file "$OPS_BEARER_TOKEN_FILE" --agent-id-file "$USER_TESTING_AGENT_ID_FILE"
  if ! chmod 600 "$OPS_BEARER_TOKEN_FILE" 2>/dev/null; then
    echo "warning: could not chmod 600 $OPS_BEARER_TOKEN_FILE" >&2
  fi
  echo "本地测试 JWT 已写入: $OPS_BEARER_TOKEN_FILE（可与 INTY_BEARER_TOKEN / INTY_ACCESS_TOKEN 互换使用）"
  if [[ -s "$USER_TESTING_AGENT_ID_FILE" ]]; then
    echo "本地测试 Agent ID 已写入: $USER_TESTING_AGENT_ID_FILE"
  else
    echo "未找到 user-testing 的本地测试 Agent，未写入: $USER_TESTING_AGENT_ID_FILE"
  fi

  echo "Seeding report test data..."
  python tools/scripts/seed_report_test_data.py

  echo "在另外一个 terminal 窗口运行下面的命令来启动评测平台 UI"
  echo "cd evaluation && npm run dev"

  echo "Starting ops backend server with reloading on port $OPS_PORT..."
  python -m uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT" --reload "${UVICORN_LOG_LEVEL[@]}"
else
  echo "Starting ops backend server on port $OPS_PORT..."
  python -m uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT" "${UVICORN_LOG_LEVEL[@]}"
fi
