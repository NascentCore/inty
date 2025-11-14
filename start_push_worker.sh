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

# This is for launching the push worker service in docker container.

# Run database migrations
echo "Starting database migrations..."
export PYTHONPATH=.
alembic upgrade head


# 启动推送服务
echo "Starting push worker service..."
python -m app.services.push_worker

