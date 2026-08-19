#!/usr/bin/env bash
# Bootstrap MemDoc eval matrix orchestrator (#3606).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
export INTY_CONFIG_YAML=devops/config.yaml.bootstrap_memdoc_eval.yaml
OUTPUT="${1:-tmp/bootstrap-memdoc-eval-matrix-live.json}"
if [[ "${RUN_LIVE:-}" == "1" ]]; then
  uv run python .cursor/skills/scripts/run_bootstrap_memdoc_eval.py \
    --run-live-matrix \
    --output "$OUTPUT"
else
  uv run python .cursor/skills/scripts/run_bootstrap_memdoc_eval.py \
    --dry-run --all-scenarios \
    --output "tmp/bootstrap-memdoc-eval-matrix-plan.json"
  echo "[bootstrap-memdoc-eval-matrix] Plan written. Live matrix:"
  echo "  RUN_LIVE=1 ./.cursor/skills/scripts/run_bootstrap_memdoc_eval_matrix.sh"
fi
