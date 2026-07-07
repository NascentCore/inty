#!/usr/bin/env bash
# Pin upstream Self-Distillation for SDFT reproduction.
# https://github.com/idanshen/Self-Distillation
set -euo pipefail

UPSTREAM_REPO="https://github.com/idanshen/Self-Distillation.git"
UPSTREAM_PIN="d77573212fa0a3ae2eeb64b9b44db1c251f75e3e"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDFT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET="${SDFT_ROOT}/upstream"

if [[ -d "${TARGET}/.git" ]]; then
  echo "Updating existing upstream at ${TARGET}"
  git -C "${TARGET}" fetch origin
  git -C "${TARGET}" checkout "${UPSTREAM_PIN}"
else
  echo "Cloning upstream into ${TARGET}"
  git clone "${UPSTREAM_REPO}" "${TARGET}"
  git -C "${TARGET}" checkout "${UPSTREAM_PIN}"
fi

echo "Upstream pinned at ${UPSTREAM_PIN}"
git -C "${TARGET}" rev-parse HEAD
