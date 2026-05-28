#!/usr/bin/env bash
# Stop Inty CI/test uvicorn on a TCP port (default 8000). Only targets backend.inty.main.
set -euo pipefail

port="${1:-8000}"
stopped=0

stop_matching_pids() {
  local sig="$1"
  for pid in $(lsof -ti ":${port}" 2>/dev/null || true); do
    local cmd
    cmd=$(ps -p "$pid" -o args= 2>/dev/null || true)
    case "$cmd" in
      *backend.inty.main*)
        echo "Sending ${sig} to PID ${pid}"
        kill "-${sig}" "$pid" 2>/dev/null || true
        stopped=$((stopped + 1))
        ;;
    esac
  done
}

stop_matching_pids TERM

if [ "$stopped" -gt 0 ]; then
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if ! lsof -ti ":${port}" >/dev/null 2>&1; then
      echo "Port ${port} is free."
      exit 0
    fi
    sleep 1
  done
  echo "Port ${port} still in use; sending KILL to remaining backend.inty.main PIDs" >&2
  stop_matching_pids KILL
fi

if lsof -ti ":${port}" >/dev/null 2>&1; then
  echo "WARN: port ${port} still has listeners (may be non-Inty processes)" >&2
  lsof -i ":${port}" 2>/dev/null || true
  exit 1
fi
