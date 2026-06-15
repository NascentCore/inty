#!/usr/bin/env bash
# Point this repo at .githooks/ (pre-commit runs uv run black on staged app/ backend/ .py).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

chmod +x .githooks/pre-commit
chmod +x tools/scripts/git-black-staged.sh

git config core.hooksPath .githooks
echo "Git hooks enabled: core.hooksPath=.githooks"
