#!/usr/bin/env bash
# Render IntelliMate YAML for VM-native jobs (Alembic, cron, GH Actions on inty-prod-server-gcp).
# CREATED_BY_AGENT
#
# Why this script exists
# ----------------------
# Docker-deployed backends use database.host host.docker.internal (see devops/config.yaml.prod)
# with --add-host=host.docker.internal:host-gateway so containers reach inty-pg on the VM.
# Processes on the VM *host* (not in Docker) must use localhost:5432 instead.
#
# Subtle failure mode (2026-06 daily report outage)
# ---------------------------------------------------
# config.yaml.prod quotes the host: host: "host.docker.internal"
# Naive sed (host: host.docker.internal -> localhost) does NOT match quoted YAML.
# The render then silently no-ops; the job still loads host.docker.internal and fails with
# "[Errno -2] Name or service not known" on the VM — not a Postgres auth or schema error.
#
# More principled long-term options (see issues/3530)
# -----------------------------------------------------
# 1. devops/config.yaml.prod.vm — explicit localhost host, no transform (best clarity).
# 2. INTY_CONFIG_YAML= that file in workflows; drop sed entirely.
# Interim: structured sed below + fail-fast assert if host.docker.internal remains.
#
# Usage:
#   devops/scripts/render_vm_database_config.sh devops/config.yaml.prod /tmp/config.prod.vm.yaml

set -euo pipefail

assert_non_empty() {
  if [[ -z "$1" ]]; then
    echo "$2" >&2
    exit 1
  fi
}

assert_no_host_docker_internal() {
  local yaml_path="$1"
  if grep -q 'host\.docker\.internal' "${yaml_path}"; then
    echo "ERROR: ${yaml_path} still references host.docker.internal after VM render." >&2
    echo "VM host jobs require database.host localhost. Check YAML quoting in source." >&2
    exit 1
  fi
}

render_vm_database_config() {
  local source_yaml="$1"
  local dest_yaml="$2"
  assert_non_empty "${source_yaml}" "SOURCE_YAML required"
  assert_non_empty "${dest_yaml}" "DEST_YAML required"
  if [[ ! -f "${source_yaml}" ]]; then
    echo "Source config not found: ${source_yaml}" >&2
    exit 1
  fi
  sed -E \
    -e 's/(^[[:space:]]*host:[[:space:]]*)"host\.docker\.internal"/\1"localhost"/' \
    -e 's/(^[[:space:]]*host:[[:space:]]*)host\.docker\.internal/\1localhost/' \
    "${source_yaml}" > "${dest_yaml}"
  assert_no_host_docker_internal "${dest_yaml}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if [[ $# -ne 2 ]]; then
    echo "Usage: $0 SOURCE_YAML DEST_YAML" >&2
    exit 1
  fi
  render_vm_database_config "$1" "$2"
fi
