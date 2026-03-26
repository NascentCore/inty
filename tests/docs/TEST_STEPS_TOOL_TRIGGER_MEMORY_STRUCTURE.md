# TEST_STEPS_TOOL_TRIGGER_MEMORY_STRUCTURE

## Goal

Persist reproducible benchmark evidence for tool trigger probability under two memory structures:

- `flat` memory injection
- `layered` memory injection (`core/profile/episodic/tool_affinity`)

Model is fixed to `google/gemini-2.5-flash`.

## Script Under Test

- `experimental/memory_prompt_benchmark/tool_trigger_benchmark.py`

## Environment + Key Source

- Config file: `devops/config.yaml.dev`
- API key source priority:
  1. `OPENROUTER_API_KEY` / `OPENAI_API_KEY` env vars
  2. fallback to `agent.api_key` in `devops/config.yaml.dev`

## Commands Executed

### 1) Smoke run

`/workspace/.venv/bin/python experimental/memory_prompt_benchmark/tool_trigger_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 2 --temperature 0.7 --max-completion-tokens 200 --timeout-seconds 90`

Output directory:

- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_100604/`

Headline:

- needed trigger: `flat 100.00%` -> `layered 100.00%`
- false trigger (not needed): `flat 0.00%` -> `layered 12.50%`

### 2) Full run (temperature=0.7)

`/workspace/.venv/bin/python experimental/memory_prompt_benchmark/tool_trigger_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 4 --temperature 0.7 --max-completion-tokens 200 --timeout-seconds 90`

Output directory:

- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_100917/`

Headline:

- needed trigger: `flat 93.75%` -> `layered 93.75%`
- false trigger (not needed): `flat 6.25%` -> `layered 0.00%`
- expected tool match (needed): `flat 93.75%` -> `layered 93.75%`

### 3) Full run (temperature=0.4) — Main Comparison Record

`/workspace/.venv/bin/python experimental/memory_prompt_benchmark/tool_trigger_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 4 --temperature 0.4 --max-completion-tokens 200 --timeout-seconds 90`

Output directory:

- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_101048/`

## Main Result Snapshot (temperature=0.4)

From `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_101048/report.md`:

- trigger rate when tool needed: `flat 87.50%` -> `layered 93.75%`
- false trigger rate when tool not needed: `flat 25.00%` -> `layered 0.00%`
- expected tool match when needed: `flat 87.50%` -> `layered 93.75%`

Per-case trigger highlights:

- `c02_calendar` (should trigger): `flat 50.00%` vs `layered 75.00%`
- `c06_general_knowledge` (should NOT trigger): `flat 100.00%` vs `layered 0.00%`

## Artifacts (raw benchmark outputs)

- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_100604/report.md`
- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_100604/raw_data.json`
- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_100917/report.md`
- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_100917/raw_data.json`
- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_101048/report.md`
- `experimental/memory_prompt_benchmark/results/tool_trigger_20260326_101048/raw_data.json`

## Notes

- The benchmark is probabilistic (sampling with temperature), so keep `samples-per-case`, `temperature`, and model fixed when comparing runs.
- This test record intentionally captures both intermediate and final runs to preserve experiment history.
