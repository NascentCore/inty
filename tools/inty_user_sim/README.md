# inty_user_sim: Long-term Synthetic User Simulator

Generated entirely by the coding agent.

Text-only app-ws client that simulates a free-form human user over a compressed
simulated calendar to grill the companion harness (bootstrap, absence-return,
rupture-repair, disclosure, complaint).

## Role vs REPL regression (testing)

- **`run_inty_repl_regression.py`** — **testing** infra gate: fixed script, minute-scale,
  CI-oriented phases (bootstrap, settled turn, GitHub issue, proactive, dreaming).
- **`inty_user_sim`** — **evaluation** only: free-form LLM user, compressed multi-week
  calendar, L1/L2 report-only JSON; **not** a CI gate and **not** imported by regression.

Shared transport lives in `tools/inty_v2_repl/sim_transport.py` (extracted from regression).
Changes there must keep regression unit tests green (`tests/cursor/skills/scripts/test_run_inty_repl_regression.py`).

## Prerequisites

- Local Ops on `:8001` with `INTY_CONFIG_YAML=devops/config.yaml.regression_tests`
- Postgres per `devops/config.yaml.regression_tests`
- `.inty_ops_bearer_token` at repo root
- `OPENAI_API_KEY` for UserAgent LLM

## Smoke (14 sim-days)

```bash
export INTY_CONFIG_YAML=devops/config.yaml.regression_tests
./backend/ops/start.sh --local --no-build-frontend

python3 -m tools.inty_user_sim run \
  --target local \
  --create-agent \
  --sim-days 14 \
  --minutes-per-sim-day 5 \
  --persona-file tools/inty_user_sim/personas/default_zh.yaml \
  --user-agent-model gpt-4o-mini
```

Report: `tmp/user-sim-<AGENT_ID>.json`

## Full grill (84 sim-days)

Add `--sim-days 84 --resume` after a successful smoke on the same bond.

## Architecture

- L1 `run_loop.py`: GrillDirector + SimSession + SimCalendar
- L2 `user_agent.py` + `tools/inty_v2_repl/sim_transport.py`
- L3 `run_store.py` + `report.py`
