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
