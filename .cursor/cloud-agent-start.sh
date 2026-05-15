#!/usr/bin/env bash
# Cloud Agent machine start: Docker daemon + Postgres on :5432 matching DatabaseSettings / CI defaults.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

sudo service docker start 2>/dev/null || true

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
else
  echo "error: docker is not available; install Docker in the Cloud Agent image or Dockerfile" >&2
  exit 1
fi

CONTAINER_NAME="${INTY_CLOUD_AGENT_PG_CONTAINER:-inty-cloudagent-pg}"

if ! "${DOCKER[@]}" inspect --type=image postgres:16 >/dev/null 2>&1; then
  "${DOCKER[@]}" pull postgres:16
fi

if ! "${DOCKER[@]}" ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  "${DOCKER[@]}" run -d \
    --name "${CONTAINER_NAME}" \
    -p 5432:5432 \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=sxwl666! \
    -e POSTGRES_DB=inty \
    postgres:16
fi

if ! "${DOCKER[@]}" ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  "${DOCKER[@]}" start "${CONTAINER_NAME}"
fi

for _ in $(seq 1 60); do
  if "${DOCKER[@]}" exec "${CONTAINER_NAME}" pg_isready -U postgres >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

echo "error: Postgres did not become ready in time" >&2
exit 1
