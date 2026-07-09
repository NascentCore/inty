#!/usr/bin/env bash
# Bootstrap MemDoc eval matrix orchestrator (#3606).
# Each cell requires restarting Ops with matching bootstrap_memdoc_policy in
# devops/config.yaml.bootstrap_memdoc_eval.yaml.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
export INTY_CONFIG_YAML=devops/config.yaml.bootstrap_memdoc_eval.yaml
uv run python .cursor/skills/scripts/run_bootstrap_memdoc_eval.py --dry-run --all-scenarios --output "tmp/bootstrap-memdoc-eval-matrix-plan.json"
echo "[bootstrap-memdoc-eval-matrix] Plan written. For live cells, edit bootstrap_memdoc_policy in config, restart Ops, then:"
echo "  uv run python .cursor/skills/scripts/run_bootstrap_memdoc_eval.py --run-live --policy <policy> --scenario-id <id>"
