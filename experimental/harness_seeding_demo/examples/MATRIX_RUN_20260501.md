# Harness matrix run record (rerun 2026-05-01)

Prior outputs under `experimental/harness_seeding_demo/results/` were removed; this documents the fresh matrix after harness fixes (status-line tool disabled by default, rubric `non_empty_visible_reply`, etc.).

## How it was run

- Repo root, `source .venv/bin/activate`, `export PYTHONPATH=.`
- Unset `OPENROUTER_API_KEY` and `OPENAI_API_KEY`; key from `devops/config.yaml.local` (`agent.api_key` -> `OPENAI_API_KEY`).
- Command:

```bash
rm -rf experimental/harness_seeding_demo/results/*
python experimental/harness_seeding_demo/scripts/run_matrix.py \
  --output-dir experimental/harness_seeding_demo/results/matrix_rerun_20260501_162708 \
  --defer-memory-ms 300
```

- User script: `fixtures/work_stress_script.json` (3 turns).
- Threshold: `0.85`.
- Model (from `summary.json`): `deepseek/deepseek-v3.2`, OpenRouter `https://openrouter.ai/api/v1`.
- `matrix_errors.json`: `[]` (all seeds completed).

## Raw summary (`matrix_summary.json`)

| seed         | first_pass_turn | turns_executed |
|--------------|-----------------|----------------|
| baseline     | 1               | 3              |
| empathic     | 1               | 3              |
| functional   | 1               | 3              |
| teammate_off | 1               | 3              |
| teammate_on  | 1               | 3              |

Artifacts: `experimental/harness_seeding_demo/results/matrix_rerun_20260501_162708/`

## Analysis

1. **Compared to the earlier snapshot** (before disabling `tool_update_agent_status_line` and before empty-reply handling): baseline moved from turn **2** to **1**; teammate_on moved from **null** to **1**. Empty assistant bodies and Postgres tool failures were the main confounders in that older run.
2. **On this run**, every seed hits the rubric threshold on **turn 1** with the fixed 3-line stress script. The primary KPI (`first_pass_turn`) **does not separate seeds** here.
3. **Secondary signals** (not in `matrix_summary.json`): read per-seed `turns.jsonl` for reply length, tone, and later-turn scores. Example: baseline turn 1 already scores `1.0` on all checks; differentiation would need longer scripts, lower thresholds, human eval, or metrics beyond this heuristic.

## Conclusions

1. **Fair technical baseline**: With DB-backed status updates out of the default harness path and non-empty replies enforced for passes, matrix runs are **repeatable** without local Postgres for this experiment shape.
2. **Hypothesis for this rubric + script**: **Seed effects are not visible** when all variants quickly satisfy keyword-style emotional validation; earlier apparent differences were largely **artifacts**.
3. **Next steps for seed experiments**: lengthen user scripts, run **k repeated trials** and report distribution, tighten rubric or add human labels, or measure **user tokens to criterion** under constrained budgets.
