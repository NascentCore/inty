# PIANO Agentic Prototype: Current Experiment Setup and Results

## Experiment Task

The current experiment evaluates whether a modular "PIANO-style" agentic loop can solve a constrained planning problem more reliably than a naive baseline.

The task is a toy navigation MDP:

- Start state: `A`
- Goal state: `D`
- Transitions:
  - `A` -> `safe_bridge` -> `B`
  - `A` -> `risky_tunnel` -> `C`
  - `B` -> `finish` -> `D`
  - `B` -> `retreat` -> `A`
  - `C` -> `loop` -> `C`
  - `C` -> `recover` -> `A`

The actor is intentionally constrained to propose one invalid shortcut action as its first candidate each step, to stress-test monitoring behavior.

## Test Setup

- Runtime entry: `researches/piano_agentic_model/main.py`
- Config source for key: `devops/config.yaml.dev` (`agent.api_key`)
- Model: `google/gemini-2.5-flash-lite`
- Command used:

`/workspace/.venv/bin/python /workspace/researches/piano_agentic_model/main.py run --config-yaml-path devops/config.yaml.dev --model-id google/gemini-2.5-flash-lite --max-steps 4 --actor-temperature 0.3`

- Output artifacts:
  - JSON trace: `researches/piano_agentic_model/results/latest_run.json`
  - Markdown summary: `researches/piano_agentic_model/docs/LAST_EXPERIMENT.md`
  - Run log: `/opt/cursor/artifacts/piano_agentic_run.log`

## Conditions

1. `baseline_no_monitor`
   - Executes first actor proposal directly.
   - No monitor gating.

2. `piano_with_monitor_and_evaluator`
   - Monitor filters actor proposals against valid transitions.
   - Evaluator selects from valid candidates.
   - Orchestrator decides subgoal progression.

## Result Snapshot

- Baseline: failed with invalid action on step 1.
  - `success=false`
  - `reached_goal=false`
  - `invalid_actions=1`
- PIANO modular run: reached goal without invalid actions.
  - `success=true`
  - `reached_goal=true`
  - `invalid_actions=0`
  - `steps=2`

## Interpretation

This run demonstrates the expected qualitative advantage of the modular loop: explicit monitoring prevents invalid shortcuts and allows evaluator-guided valid progression.

## Limits

- Single model, single run, single toy environment.
- Useful as a behavioral smoke test, not a statistical performance benchmark.

## Added Complex Test Case (Problem-Solving Showcase)

To better showcase problem-solving capability, a second task was added:

- Task id: `complex_supply_chain`
- Start: `Dock`
- Goal: `Completed`
- Required checkpoint sequence:
  1. `BadgeRoom`
  2. `SecureGate`
  3. `TransferBay`
  4. `AuditDesk`
  5. `Completed`
- Environment includes trap/loop states (`IncidentLoop`) and reset actions, making planning depth and sequencing more demanding than the simple bridge case.

Command:

`/workspace/.venv/bin/python /workspace/researches/piano_agentic_model/main.py run --config-yaml-path devops/config.yaml.dev --model-id google/gemini-2.5-flash-lite --task-id complex_supply_chain --max-steps 10 --actor-temperature 0.3 --output-json-path researches/piano_agentic_model/results/complex_supply_chain_run.json --output-markdown-path researches/piano_agentic_model/docs/COMPLEX_SUPPLY_CHAIN_EXPERIMENT.md`

Result snapshot:

- Baseline (`baseline_no_monitor`):
  - `success=false`
  - `reached_goal=false`
  - `invalid_actions=1`
  - `steps=1`
- Modular (`piano_with_monitor_and_evaluator`):
  - `success=true`
  - `reached_goal=true`
  - `invalid_actions=0`
  - `steps=7`

Interpretation:

The complex case preserves the same qualitative pattern as the simple task, but under a deeper, multi-checkpoint route with loops and regressions. The modular stack remains robust by filtering invalid shortcuts and choosing valid progress actions stage-by-stage.
