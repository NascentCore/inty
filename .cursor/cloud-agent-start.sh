#!/usr/bin/env bash
# Cloud Agent machine start: Postgres on :15432 (Docker postgres:16 or apt fallback).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${ROOT}/tools/scripts/ensure_postgres_for_tests.sh"
