# structured_agentic_brain demo

Minimal runnable demo of a brain-like structured multi-agent entity.

## What is included

- A compact multi-agent pipeline:
  - `TA` (thalamus routing)
  - `INA` (state estimation)
  - `AMA` (risk sentinel)
  - `HCA` (episodic retrieval, local deterministic)
  - `PFCA` (planning)
  - `ACCA` (conflict monitor, local deterministic)
  - `OFA` (value scoring, local deterministic)
  - `BGA` (action selection, local deterministic)
  - `LCA` (final response realization)
- Per-agent pedantic wrappers (PAU style): every agent output is validated.
- Realistic scenario runner with Gemini 2.5 Flash (`google/gemini-2.5-flash` via OpenRouter-compatible API).

## Requirements

- Python venv is available in repo root (`.venv`).
- OpenRouter-compatible credentials:
  - `OPENROUTER_API_KEY`, or
  - fallback to repo `config.yaml` (`agent.api_key` + `agent.base_url`)

Only the `LCA` agent calls Gemini 2.5 Flash; other agents are deterministic to keep the demo stable and minimal while preserving the structured architecture.

## Run

From repo root:

```bash
source .venv/bin/activate
python researches/structured_agentic_brain/main.py run-cases
```

Optional:

```bash
python researches/structured_agentic_brain/main.py run-cases --output-json /tmp/brain_demo_results.json
```

The command prints concise per-case summaries and writes full structured traces to JSON.

## Experiment conclusions

### Scenarios covered

- `case_anxiety_interview`: high interview anxiety with immediate planning need.
- `case_loneliness_evening`: loneliness plus social withdrawal.
- `case_boundary_risk`: high-risk hopelessness cues requiring safety-first behavior.

### Observed behavior of the structured multi-agent brain

- In the high-risk case, the system explicitly escalates safety by:
  - routing `safety` with high priority,
  - setting threat level to `high`,
  - selecting the action `Immediate safety resources`,
  - producing a final response with crisis contact guidance and grounding steps.
- In medium-risk cases, the system prefers practical micro-actions and lower-friction next steps rather than emergency escalation.
- Full internal state is persisted (`route`, `insula_state`, `amygdala_threat`, `memory_evidence`, `plan`, `conflict_report`, `value_assessment`, `action_decision`, `final_response`) so decisions are auditable.

### Comparison with simplified single-agent baseline

- A simplified single-turn baseline with the same model (`google/gemini-2.5-flash`) can produce empathetic and sometimes safety-aware text.
- However, the baseline does not expose intermediate state, conflict reasoning, action utility, or selected-vs-rejected policy options.
- The structured brain design provides stronger controllability and explainability because safety and planning are explicit internal stages, not hidden inside one final generation step.

### Practical conclusion

- For this prototype, a hybrid approach is effective:
  - deterministic internal agents for routing/risk/planning/decision,
  - Gemini 2.5 Flash for final language realization.
- This keeps the system minimal and stable while preserving core benefits of a brain-like structured architecture.
