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
alembic upgrade head

if [ "$DEV" = true ]; then
  echo "Starting in development mode..."
  python scripts/init_admin_user.py
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  echo "Starting in normal mode without reloading..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
