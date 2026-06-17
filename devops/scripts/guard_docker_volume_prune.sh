#!/usr/bin/env bash
# Refuse docker volume prune when IntelliMate Postgres data volumes exist.
# CREATED_BY_AGENT
#
# Usage:
#   devops/scripts/guard_docker_volume_prune.sh          # exits 1 if prune would be unsafe
#   devops/scripts/guard_docker_volume_prune.sh --explain

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local_postgres_lib.sh
source "${SCRIPT_DIR}/local_postgres_lib.sh"

EXPLAIN="false"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --explain)
        EXPLAIN="true"
        shift
        ;;
      -h | --help)
        sed -n '2,7p' "$0" | sed 's/^# \?//'
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        exit 1
        ;;
    esac
  done
}

parse_args "$@"
require_docker

if volume_exists; then
  if [[ "${EXPLAIN}" == "true" ]]; then
    echo "Protected volume ${INTY_PG_VOLUME} exists."
    echo "Do not run: docker volume prune"
    echo "If the Postgres container was removed, recreate with:"
    echo "  devops/scripts/ensure_inty_dev_postgres_container.sh"
  fi
  echo "REFUSE: protected volume ${INTY_PG_VOLUME} is present" >&2
  exit 1
fi

echo "No protected IntelliMate Postgres volumes found; docker volume prune is not blocked by this guard."
