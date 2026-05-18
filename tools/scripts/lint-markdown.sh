#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
npm install --prefix tools/markdownlint
exec npx --prefix tools/markdownlint markdownlint-cli2
