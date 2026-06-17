#!/usr/bin/env bash
# Render IntelliMate YAML for VM-native jobs (Alembic, cron) from Docker-baked config.
# CREATED_BY_AGENT
#
# Docker images bake database.host: host.docker.internal; processes on the VM
# host connect via localhost:5432 instead.
#
# Usage:
#   devops/scripts/render_vm_database_config.sh devops/config.yaml.prod /tmp/config.prod.vm.yaml

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 SOURCE_YAML DEST_YAML" >&2
  exit 1
fi

SOURCE_YAML="$1"
DEST_YAML="$2"

assert_non_empty() {
  if [[ -z "$1" ]]; then
    echo "$2" >&2
    exit 1
  fi
}

assert_non_empty "${SOURCE_YAML}" "SOURCE_YAML required"
assert_non_empty "${DEST_YAML}" "DEST_YAML required"

if [[ ! -f "${SOURCE_YAML}" ]]; then
  echo "Source config not found: ${SOURCE_YAML}" >&2
  exit 1
fi

sed 's/host: host.docker.internal/host: localhost/' "${SOURCE_YAML}" > "${DEST_YAML}"
