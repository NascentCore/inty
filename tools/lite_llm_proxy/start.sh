#!/usr/bin/env bash
# Run LiteLLM proxy for https://api.funcloud.ai/v1/official (Docker)
# Requires: Docker. Image: docker.litellm.ai/berriai/litellm:main-latest
# Env: FUNCLOUD_API_KEY (required), LITELLM_MASTER_KEY (required for auth), DATABASE_URL (optional, default: localhost:5432/lite-llm)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.yaml"

if [[ -z "${FUNCLOUD_API_KEY:-}" ]]; then
  echo "FUNCLOUD_API_KEY is not set. Export it before running:" >&2
  echo "  export FUNCLOUD_API_KEY='your-key'" >&2
  exit 1
fi
# Funcloud requires Authorization: Bearer; LiteLLM config reads full header from env.
export FUNCLOUD_AUTH_HEADER="${FUNCLOUD_AUTH_HEADER:-Bearer ${FUNCLOUD_API_KEY}}"

if [[ -z "${LITELLM_MASTER_KEY:-}" ]]; then
  echo "LITELLM_MASTER_KEY not set; proxy requires it for master-key auth." >&2
  exit 1
fi

# Default DB for local dev (matches backend/inty Postgres from AGENTS.md)
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:sxwl666!@localhost:5432/lite-llm}"

# Create lite-llm database if missing (connect to default 'postgres' DB to run CREATE DATABASE)
if command -v psql &>/dev/null; then
  db_exists=$(psql "postgresql://postgres:sxwl666!@localhost:5432/postgres" -tAc "SELECT 1 FROM pg_database WHERE datname='lite-llm'" 2>/dev/null || true)
  if [[ -z "${db_exists}" ]]; then
    psql "postgresql://postgres:sxwl666!@localhost:5432/postgres" -c 'CREATE DATABASE "lite-llm";'
    echo "Created database lite-llm."
  fi
fi

# LiteLLM proxy with database_url requires Prisma. Ensure prisma is installed and client generated
# (generated client lives in litellm/proxy/prisma/; we add proxy dir to PYTHONPATH so "from prisma" works)
RUN_PY="python3"
if command -v uv &>/dev/null; then
  RUN_PY="uv run python"
fi
LITELLM_PROXY_DIR=$($RUN_PY -c "import litellm.proxy; import os; print(os.path.dirname(litellm.proxy.__file__))")
if ! $RUN_PY -c "from prisma import Prisma" 2>/dev/null; then
  $RUN_PY -m pip install prisma --quiet
  (cd "$LITELLM_PROXY_DIR" && $RUN_PY -m prisma generate --schema=schema.prisma)
fi
export PYTHONPATH="${LITELLM_PROXY_DIR}:${PYTHONPATH}"

if command -v uv &>/dev/null; then
  exec uv run litellm --config "$CONFIG" --port 4000 "$@"
else
  exec litellm --config "$CONFIG" --port 4000 "$@"
fi

# exec docker run --rm -it \
#   -v "${CONFIG}:/app/config.yaml:ro" \
#   -e FUNCLOUD_API_KEY \
#   -e LITELLM_MASTER_KEY \
#   -p 4000:4000 \
#   docker.litellm.ai/berriai/litellm:main-latest \
#   --config /app/config.yaml --port 4000 "$@"
