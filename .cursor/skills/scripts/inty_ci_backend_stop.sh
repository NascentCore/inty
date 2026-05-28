#!/usr/bin/env bash
# Stop Inty CI/test uvicorn on a TCP port (default 8000). Only targets backend.inty.main.
set -euo pipefail

port="${1:-8000}"
stopped=0

is_inty_main_cmd() {
  case "$1" in
    *backend.inty.main*) return 0 ;;
    *) return 1 ;;
  esac
}

# PIDs listening on $port whose command line includes backend.inty.main.
inty_main_pids_on_port() {
  local pid cmd
  for pid in $(lsof -ti ":${port}" 2>/dev/null || true); do
    cmd=$(ps -p "$pid" -o args= 2>/dev/null || true)
    if is_inty_main_cmd "$cmd"; then
      echo "$pid"
    fi
  done
}

inty_main_still_on_port() {
  local pids
  pids=$(inty_main_pids_on_port)
  [ -n "$pids" ]
}

# Poll until no backend.inty.main listener remains (or retries exhausted).
wait_inty_main_off_port() {
  local _
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if ! inty_main_still_on_port; then
      return 0
    fi
    sleep 1
  done
  return 1
}

stop_matching_pids() {
  local sig="$1" pid
  for pid in $(inty_main_pids_on_port); do
    echo "Sending ${sig} to PID ${pid}"
    kill "-${sig}" "$pid" 2>/dev/null || true
    stopped=$((stopped + 1))
  done
}

stop_matching_pids TERM

if [ "$stopped" -gt 0 ]; then
  if wait_inty_main_off_port; then
    echo "No backend.inty.main listener on port ${port}."
    exit 0
  fi
  echo "backend.inty.main still on port ${port}; sending KILL" >&2
  stop_matching_pids KILL
  if wait_inty_main_off_port; then
    echo "No backend.inty.main listener on port ${port}."
    exit 0
  fi
fi

if inty_main_still_on_port; then
  echo "ERROR: backend.inty.main still listening on port ${port}" >&2
  lsof -i ":${port}" 2>/dev/null || true
  exit 1
fi

if lsof -ti ":${port}" >/dev/null 2>&1; then
  echo "Note: port ${port} has non-Inty listeners (left unchanged)" >&2
fi
