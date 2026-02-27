#!/bin/bash -e

DEV=false
TEST=false
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
      echo "  --dev   Dev mode: build evaluation frontend, seed test user/data, uvicorn --reload"
      echo "  --test  Test mode: like --dev but skip evaluation frontend build (e.g. for CI)"
      echo "Run from repository root. Listens on PORT (default 8001). Cloud Run sets PORT=8080."
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
python scripts/init_subscription_plans_simple.py

OPS_PORT="${PORT:-8001}"

if [ "$DEV" = true ]; then
  if [ "$TEST" = true ]; then
    echo "Starting ops in test mode (skip evaluation frontend build)..."
  else
    echo "Starting ops in dev mode..."
    echo "Building evaluation frontend..."
    ./evaluation/build.sh
  fi
  python scripts/init_admin_user.py --user-id user-testing --is-superuser=true
  python scripts/seed_report_test_data.py
  uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT" --reload
else
  echo "Starting ops in normal mode on port $OPS_PORT..."
  uvicorn backend.ops.main:app --host 0.0.0.0 --port "$OPS_PORT"
fi
