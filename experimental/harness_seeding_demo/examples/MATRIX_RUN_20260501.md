# Harness matrix run record (2026-05-01)

Offline record of one full matrix execution. No API keys or secrets in this file.

## How it was run

- Repo root, `source .venv/bin/activate`, `export PYTHONPATH=.`
- Unset `OPENROUTER_API_KEY` and `OPENAI_API_KEY`; key injected from `devops/config.yaml.local` (`agent.api_key` -> process `OPENAI_API_KEY`) via `run_trial.py` default behavior.
- Command:

```bash
python experimental/harness_seeding_demo/scripts/run_matrix.py \
  --output-dir experimental/harness_seeding_demo/results/matrix_20260501_155404 \
  --defer-memory-ms 300
```

- User script: `fixtures/work_stress_script.json` (3 lines).
- Score threshold: `0.85` (`scorer/emotional_rubric.py`).
- Model (from logs): `deepseek/deepseek-v3.2` via OpenRouter.

## Raw summary (`matrix_summary.json`)

| seed          | first_pass_turn | turns_executed |
|---------------|-----------------|----------------|
| baseline      | 2               | 3              |
| empathic      | 1               | 3              |
| functional    | 1               | 3              |
| teammate_off  | 1               | 3              |
| teammate_on   | null            | 3              |

Artifacts on disk (gitignored under `results/`):  
`experimental/harness_seeding_demo/results/matrix_20260501_155404/`

## Caveats noted during run

- **Historical note (this snapshot):** PostgreSQL was not running; `tool_update_agent_status_line` failed and some turns had empty `assistant_text`, which skewed rubric scores.
- **Current harness:** `run_trial` / `run_matrix` default **`INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL=1`**, and the rubric requires **`non_empty_visible_reply`**; rerun the matrix for cleaner seed comparisons.

## Conclusions (same run)

1. Under this environment and script, empathic, functional, and teammate_off reached the rubric threshold on turn 1; baseline on turn 2; teammate_on never within 3 turns.
2. Treat teammate_on cautiously for this snapshot: empty replies and DB tool failures dominated; prefer reruns with the status-line tool disabled or Postgres up.
3. The rubric is heuristic; functional seed passing turn 1 does not imply equal empathic quality to humans.
