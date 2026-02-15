#!/bin/bash -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find repo root (directory containing alembic/alembic.ini). Works when script lives in
# backend/push_worker/ (local) or when copied to / in Docker.
ROOT="$SCRIPT_DIR"
while [ ! -f "$ROOT/alembic/alembic.ini" ] && [ "$ROOT" != "/" ]; do
  ROOT="$(cd "$ROOT/.." && pwd)"
done
if [ ! -f "$ROOT/alembic/alembic.ini" ]; then
  echo "ERROR: alembic/alembic.ini not found (searched from $SCRIPT_DIR)"
  exit 1
fi
cd "$ROOT"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --help|-h)
      echo "Usage: $0 [--help]"
      echo "  Run DB migrations then start the push worker (local or Docker)."
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# For launching the push worker service (local or Docker).

# Run database migrations
echo "Starting database migrations..."
export PYTHONPATH=.
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-$ROOT/alembic/alembic.ini}"
alembic -c "$ALEMBIC_CONFIG" upgrade head


# 启动推送服务
echo "Starting push worker service..."
python -m backend.push_worker.main
