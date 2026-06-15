#!/usr/bin/env bash
# Format staged Python files under app/ and backend/ with uv run black, then re-stage.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=tools/scripts/python-black.sh
source "$ROOT/tools/scripts/python-black.sh"

STAGED_PY=()
while IFS= read -r -d '' file; do
    case "$file" in
        *.py)
            if is_python_format_path "$file"; then
                STAGED_PY+=("$file")
            fi
            ;;
    esac
done < <(git diff --cached --name-only --diff-filter=ACMR -z)

if [ "${#STAGED_PY[@]}" -eq 0 ]; then
    exit 0
fi

run_black "${STAGED_PY[@]}"
git add -- "${STAGED_PY[@]}"
