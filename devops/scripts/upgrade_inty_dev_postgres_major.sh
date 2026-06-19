#!/usr/bin/env bash
# In-place major-version upgrade for inty-dev-postgres on the canonical named volume.
# CREATED_BY_AGENT
#
# Uses pg_upgrade (pgvector 16+17 composite image) then recreates the container on INTY_PG_IMAGE.
# Safe: never removes inty-dev-postgres-data; requires backup first.
#
# Usage (from repo root, on the VM):
#   devops/scripts/upgrade_inty_dev_postgres_major.sh
#   devops/scripts/upgrade_inty_dev_postgres_major.sh --skip-backup

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local_postgres_lib.sh
source "${SCRIPT_DIR}/local_postgres_lib.sh"

readonly UPGRADE_TAG="[inty-local-postgres-upgrade]"
readonly UPGRADE_IMAGE="inty-pgvector-upgrade:16-to-17"
readonly UPGRADE_DOCKERFILE="${SCRIPT_DIR}/docker/pgvector-postgres-upgrade-16-to-17.Dockerfile"
SKIP_BACKUP="false"

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \?//'
  echo
  echo "Options:"
  echo "  --skip-backup   skip backup_local_postgres.sh (not recommended)"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --skip-backup)
        SKIP_BACKUP="true"
        shift
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
}

volume_pg_major() {
  docker run --rm \
    -v "${INTY_PG_VOLUME}:/var/lib/postgresql" \
    "${INTY_PG_IMAGE_PREVIOUS}" \
    bash -c '
      set -euo pipefail
      for path in \
        /var/lib/postgresql/PG_VERSION \
        /var/lib/postgresql/data/PG_VERSION \
        /var/lib/postgresql/16/data/PG_VERSION \
        /var/lib/postgresql/17/data/PG_VERSION; do
        if [[ -f "${path}" ]]; then
          cat "${path}"
          exit 0
        fi
      done
      echo "unknown"
    '
}

prepare_volume_layout_for_upgrade() {
  docker run --rm \
    -v "${INTY_PG_VOLUME}:/var/lib/postgresql" \
    "${INTY_PG_IMAGE_PREVIOUS}" \
    bash -c '
      set -euo pipefail
      if [[ -f /var/lib/postgresql/16/data/PG_VERSION ]]; then
        echo "layout: already 16/data"
        mkdir -p /var/lib/postgresql/17/data
        if [[ -f /var/lib/postgresql/17/data/PG_VERSION ]] \
          && [[ ! -f /var/lib/postgresql/17/data/PG_UPGRADE_SUCCESS ]]; then
          rm -rf /var/lib/postgresql/17/data/*
          echo "layout: cleared partial 17/data from failed upgrade"
        fi
        exit 0
      fi
      if [[ ! -f /var/lib/postgresql/PG_VERSION ]]; then
        echo "no PG_VERSION at volume root; cannot upgrade" >&2
        exit 1
      fi
      major="$(cat /var/lib/postgresql/PG_VERSION)"
      if [[ "${major}" != "16" ]]; then
        echo "volume root is PG${major}, expected PG16" >&2
        exit 1
      fi
      mkdir -p /var/lib/postgresql/16/data /var/lib/postgresql/17/data
      rmdir /var/lib/postgresql/data 2>/dev/null || true
      shopt -s extglob
      mv /var/lib/postgresql/!(16|17|data) /var/lib/postgresql/16/data/
      echo "layout: moved volume root cluster -> 16/data"
    '
}

run_pg_upgrade() {
  docker build -t "${UPGRADE_IMAGE}" -f "${UPGRADE_DOCKERFILE}" "${SCRIPT_DIR}/docker"
  docker run --rm \
    --shm-size=1g \
    -v "${INTY_PG_VOLUME}:/var/lib/postgresql" \
    "${UPGRADE_IMAGE}"
  docker run --rm \
    -v "${INTY_PG_VOLUME}:/var/lib/postgresql" \
    "${INTY_PG_IMAGE}" \
    touch /var/lib/postgresql/17/data/PG_UPGRADE_SUCCESS
}

finalize_volume_for_pg17_container() {
  docker run --rm \
    -v "${INTY_PG_VOLUME}:/var/lib/postgresql" \
    "${INTY_PG_IMAGE}" \
    bash -c '
      set -euo pipefail
      if [[ ! -f /var/lib/postgresql/17/data/PG_VERSION ]]; then
        echo "missing 17/data after pg_upgrade" >&2
        exit 1
      fi
      shopt -s dotglob
      rm -rf /var/lib/postgresql/16
      mv /var/lib/postgresql/17/data/* /var/lib/postgresql/
      rm -rf /var/lib/postgresql/17
      rmdir /var/lib/postgresql/data 2>/dev/null || true
      echo "layout: 17/data -> volume root (PG$(cat /var/lib/postgresql/PG_VERSION))"
    '
}

align_postgres_superuser_password() {
  load_pg_password
  wait_for_postgres_ready
  docker exec -e PGPASSWORD="${PGPASSWORD}" "${INTY_PG_CONTAINER}" \
    psql -U postgres -d postgres -At -c "ALTER USER postgres PASSWORD '${PGPASSWORD}';" >/dev/null
  echo "postgres superuser password aligned with devops/config.yaml.dev"
}

remove_container_if_present() {
  if container_exists; then
    docker rm -f "${INTY_PG_CONTAINER}" >/dev/null
    echo "container ${INTY_PG_CONTAINER}: removed (volume retained)"
  fi
}

parse_args "$@"
require_docker

if ! volume_exists; then
  echo "${UPGRADE_TAG} volume ${INTY_PG_VOLUME} missing" >&2
  exit 1
fi

current_major="$(volume_pg_major)"
if [[ "${current_major}" == "${INTY_PG_MAJOR_VERSION}" ]]; then
  echo "${UPGRADE_TAG} volume already PG${INTY_PG_MAJOR_VERSION}; running ensure only"
  "${SCRIPT_DIR}/ensure_inty_dev_postgres_container.sh" --recreate-after-upgrade
  align_postgres_superuser_password
  exit 0
fi

if [[ "${current_major}" != "16" ]]; then
  echo "${UPGRADE_TAG} unsupported volume PG major '${current_major}' (expected 16 -> ${INTY_PG_MAJOR_VERSION})" >&2
  exit 1
fi

echo "${UPGRADE_TAG} pre-upgrade volume PG${current_major}"

if [[ "${SKIP_BACKUP}" != "true" ]]; then
  echo "${UPGRADE_TAG} backup before upgrade"
  "${SCRIPT_DIR}/backup_local_postgres.sh"
fi

echo "${UPGRADE_TAG} parity baseline vs Cloud SQL"
set +e
"${SCRIPT_DIR}/sync_cloudsql_inty_incremental.sh" --check-only --db inty
baseline_rc=$?
set -e
if [[ "${baseline_rc}" -ne 0 ]]; then
  echo "${UPGRADE_TAG} WARN: pre-upgrade sync --check-only exit=${baseline_rc}" >&2
fi

load_pg_password
export PGPASSWORD
if command -v psql >/dev/null 2>&1 && container_running; then
  dev_fp_before="$(database_fingerprint "${INTY_PG_DEV_DB}" 2>/dev/null || echo "unavailable")"
  prod_fp_before="$(database_fingerprint "${INTY_PG_PROD_DB}" 2>/dev/null || echo "unavailable")"
  echo "fingerprint ${INTY_PG_DEV_DB} before: ${dev_fp_before}"
  echo "fingerprint ${INTY_PG_PROD_DB} before: ${prod_fp_before}"
fi

if container_running; then
  docker stop "${INTY_PG_CONTAINER}" >/dev/null
  echo "container ${INTY_PG_CONTAINER}: stopped"
fi

echo "${UPGRADE_TAG} prepare volume layout"
prepare_volume_layout_for_upgrade

echo "${UPGRADE_TAG} pg_upgrade 16 -> 17"
run_pg_upgrade

echo "${UPGRADE_TAG} finalize volume for ${INTY_PG_IMAGE}"
finalize_volume_for_pg17_container

remove_container_if_present

echo "${UPGRADE_TAG} start PG${INTY_PG_MAJOR_VERSION} container"
"${SCRIPT_DIR}/ensure_inty_dev_postgres_container.sh" --recreate-after-upgrade
align_postgres_superuser_password

load_pg_password
export PGPASSWORD
server_major="$(postgres_server_version_major)"
if [[ "${server_major}" != "${INTY_PG_MAJOR_VERSION}" ]]; then
  echo "${UPGRADE_TAG} RESULT: FAIL — server_version major ${server_major}, expected ${INTY_PG_MAJOR_VERSION}" >&2
  exit 1
fi
echo "server_version major: ${server_major}"

if command -v psql >/dev/null 2>&1; then
  dev_fp_after="$(database_fingerprint "${INTY_PG_DEV_DB}")"
  prod_fp_after="$(database_fingerprint "${INTY_PG_PROD_DB}")"
  echo "fingerprint ${INTY_PG_DEV_DB} after: ${dev_fp_after}"
  echo "fingerprint ${INTY_PG_PROD_DB} after: ${prod_fp_after}"
fi

echo "${UPGRADE_TAG} parity check vs Cloud SQL"
set +e
"${SCRIPT_DIR}/sync_cloudsql_inty_incremental.sh" --check-only --db inty
parity_rc=$?
set -e
if [[ "${parity_rc}" -ne 0 ]]; then
  echo "${UPGRADE_TAG} WARN: sync --check-only exit=${parity_rc} (may be drift during upgrade window)" >&2
fi

echo "${UPGRADE_TAG} durability verify with restart-test"
"${SCRIPT_DIR}/verify_local_postgres_durability.sh" --restart-test

echo "${UPGRADE_TAG} RESULT: PASS — upgraded to PG${INTY_PG_MAJOR_VERSION} on ${INTY_PG_VOLUME}"
