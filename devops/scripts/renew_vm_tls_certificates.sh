#!/usr/bin/env bash
# Idempotent Let's Encrypt renewal on the IntelliMate VM; reload nginx when certs change.
# CREATED_BY_AGENT
#
# Usage (on the VM, from repo root):
#   devops/scripts/renew_vm_tls_certificates.sh
#   devops/scripts/renew_vm_tls_certificates.sh --check-only

set -euo pipefail

MODE="renew"

usage() {
  sed -n '2,7p' "$0" | sed 's/^# \?//'
  echo
  echo "Options:"
  echo "  --check-only   report cert expiry; do not renew or reload nginx"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check-only)
        MODE="check"
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

assert_certbot_available() {
  if ! command -v certbot >/dev/null 2>&1; then
    echo "ERROR: certbot is not installed on this host." >&2
    exit 1
  fi
}

report_expiring_certs() {
  certbot certificates 2>/dev/null || true
}

renew_certificates() {
  local renewed="false"
  if certbot renew --quiet --no-random-sleep-on-renew; then
    renewed="true"
  fi
  if [[ "${renewed}" == "true" ]]; then
    nginx -t
    systemctl reload nginx
    echo "TLS certificates renewed; nginx reloaded."
    return
  fi
  echo "No TLS certificates required renewal."
}

parse_args "$@"
assert_certbot_available

if [[ "${MODE}" == "check" ]]; then
  report_expiring_certs
  exit 0
fi

renew_certificates
