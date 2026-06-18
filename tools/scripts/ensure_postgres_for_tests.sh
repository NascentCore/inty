#!/usr/bin/env bash
# Ensure Postgres 16 on :5432 for pytest (CI parity: postgres/sxwl666!/inty).
# Prefers Docker postgres:16; falls back to distro postgresql when Docker overlayfs is blocked.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-sxwl666!}"
PG_DB="${PG_DB:-inty}"
PG_PORT="${PG_PORT:-5432}"
CONTAINER_NAME="${INTY_PG_CONTAINER:-pg-inty}"

wait_pg() {
  for _ in $(seq 1 60); do
    if PGPASSWORD="${PG_PASSWORD}" psql -h localhost -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -c 'SELECT 1' >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_dockerd_if_needed() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi
  if sudo docker info >/dev/null 2>&1; then
    return 0
  fi
  command -v dockerd >/dev/null 2>&1 || return 1
  if ! pgrep -x dockerd >/dev/null 2>&1; then
    sudo nohup dockerd --iptables=false --ip6tables=false --storage-driver=vfs \
      >/tmp/dockerd-inty.log 2>&1 &
    sleep 4
  fi
  sudo docker info >/dev/null 2>&1
}

docker_pg() {
  start_dockerd_if_needed || return 1
  local -a DOCKER=(docker)
  if ! docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  fi
  if ! "${DOCKER[@]}" inspect --type=image postgres:16 >/dev/null 2>&1; then
    "${DOCKER[@]}" pull postgres:16
  fi
  if ! "${DOCKER[@]}" ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    "${DOCKER[@]}" run -d \
      --name "${CONTAINER_NAME}" \
      -p "${PG_PORT}:5432" \
      -e "POSTGRES_USER=${PG_USER}" \
      -e "POSTGRES_PASSWORD=${PG_PASSWORD}" \
      -e "POSTGRES_DB=${PG_DB}" \
      postgres:16
  elif ! "${DOCKER[@]}" ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    "${DOCKER[@]}" start "${CONTAINER_NAME}"
  fi
  wait_pg
}

apt_pg() {
  if ! command -v psql >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq postgresql postgresql-contrib
  fi
  sudo pg_ctlcluster 16 main start 2>/dev/null || sudo service postgresql start
  sudo -u postgres psql -tc "ALTER USER ${PG_USER} PASSWORD '${PG_PASSWORD}';" >/dev/null 2>&1 || true
  if ! sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1; then
    sudo -u postgres createdb "${PG_DB}"
  fi
  wait_pg
}

if docker_pg; then
  echo "Postgres ready (Docker container ${CONTAINER_NAME} on :${PG_PORT})"
elif apt_pg; then
  echo "Postgres ready (local postgresql on :${PG_PORT})"
else
  echo "error: could not start Postgres on :${PG_PORT}" >&2
  exit 1
fi

if [[ -f .venv/bin/python ]]; then
  export PYTHONPATH=.
  export ALEMBIC_CONFIG=backend/alembic/alembic.ini
  # TODO(INTY_CONFIG_YAML): export INTY_CONFIG_YAML=devops/config.yaml.test instead of cp
  if [[ ! -f config.yaml ]]; then
    cp devops/config.yaml.test config.yaml
  fi
  .venv/bin/python -m alembic upgrade head
fi
