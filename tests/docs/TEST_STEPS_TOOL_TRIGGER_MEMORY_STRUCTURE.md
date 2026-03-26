# TEST_STEPS_TOOL_TRIGGER_MEMORY_STRUCTURE

## Goal

Persist reproducible benchmark evidence for tool trigger probability under two memory structures:

- `flat` memory injection
- `layered` memory injection (`core/profile/episodic/tool_affinity`)

Model is fixed to `google/gemini-2.5-flash`.

## Test Setup

### Tool set under evaluation

The benchmark exposes 4 tools through OpenAI-compatible function calling:

- `get_weather`
- `create_calendar_event`
- `web_search`
- `create_support_ticket`

### Query set

Total 8 queries:

- 4 queries where tool call is expected (`should_trigger_tool=true`)
- 4 queries where tool call is NOT expected (`should_trigger_tool=false`)

### Memory variants under test

- `flat`: unstructured memory blob with mixed profile/tool hints
- `layered`: structured memory with explicit blocks:
  - `core_memory`
  - `profile_memory`
  - `episodic_memory`
  - `tool_affinity_memory`

### Fixed runtime parameters (for main comparison)

- model: `google/gemini-2.5-flash`
- samples-per-case: `4`
- temperature: `0.4`
- max-completion-tokens: `200`
- timeout-seconds: `90`

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

## Expected Outcome (Acceptance Criteria)

For the main comparison setting (`samples-per-case=4`, `temperature=0.4`, same query set/model):

1. **No regression on needed-tool triggering**
   - `layered.trigger_rate_when_needed >= flat.trigger_rate_when_needed`

2. **Strict improvement on false triggers**
   - `layered.trigger_rate_when_not_needed < flat.trigger_rate_when_not_needed`

3. **No regression on expected tool match**
   - `layered.expected_tool_match_rate_when_needed >= flat.expected_tool_match_rate_when_needed`

4. **Primary target for non-tool scenarios**
   - Prefer `layered.trigger_rate_when_not_needed <= 0.05`
   - If `> 0.05`, mark as warning and inspect prompts/query distribution.

## Verdict for this record

Using run `20260326_101048`:

- Criteria 1: PASS (`93.75% >= 87.50%`)
- Criteria 2: PASS (`0.00% < 25.00%`)
- Criteria 3: PASS (`93.75% >= 87.50%`)
- Criteria 4: PASS (`0.00% <= 5.00%`)

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
