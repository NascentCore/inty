#!/usr/bin/env bash
# Probe IntelliMate local Docker Postgres logical database readiness.
# CREATED_BY_AGENT
#
# Prefers host psql on localhost:5432; falls back to docker exec via docker_cmd.
#
# Usage (from repo root, on the VM):
#   devops/scripts/probe_inty_pg_logical_database.sh inty-dev
#   devops/scripts/probe_inty_pg_logical_database.sh inty

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local_postgres_lib.sh
source "${SCRIPT_DIR}/local_postgres_lib.sh"

usage() {
  sed -n '2,9p' "$0" | sed 's/^# \?//'
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 1
fi

case "$1" in
  -h | --help)
    usage
    exit 0
    ;;
esac

probe_logical_database "$1"
