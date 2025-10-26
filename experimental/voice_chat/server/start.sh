#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
export PYTHONUNBUFFERED=1
export PYTHONPATH="$SCRIPT_DIR/../..:$PYTHONPATH"

if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
  source "$SCRIPT_DIR/.venv/bin/activate"
fi

if ! python -c "import fastapi, aiortc, google.genai" >/dev/null 2>&1; then
  python -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

exec uvicorn experimental.voice_chat.server.main:app --host 0.0.0.0 --port 9001 --reload
