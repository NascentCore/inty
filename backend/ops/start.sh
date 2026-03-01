#!/bin/bash -e

DEV=false
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
    --local)
      LOCAL=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--local]"
      echo "  --local   Local mode: run ops locally"
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

if [ "$LOCAL" = true ]; then
  echo "Seeding report test data..."
  python scripts/seed_report_test_data.py
  echo "Starting ops in dev mode on port $OPS_PORT..."
  uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT" --reload &>/dev/null &
  echo "Initializing admin user ..."
  python scripts/init_admin_user.py --user-id user-testing --is-superuser=true
  echo "Starting evaluation frontend in dev mode..."
  evaluation/build.sh # 安装依赖库并构建前端
  cd evaluation && npm run dev
else
  echo "Starting ops in normal mode on port $OPS_PORT..."
  uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT"
fi
