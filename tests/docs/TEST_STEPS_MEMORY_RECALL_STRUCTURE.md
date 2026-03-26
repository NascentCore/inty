# TEST_STEPS_MEMORY_RECALL_STRUCTURE

## Goal

Compare memory recall quality between:

- `flat` memory injection (legacy-style unstructured blob)
- `layered` memory injection (`core/profile/episodic/tool_affinity`)

Model is fixed to `google/gemini-2.5-flash`.

## Test Setup

### Script under test

- `experimental/memory_prompt_benchmark/memory_recall_benchmark.py`

### Recall case design

Total 8 recall questions (multiple choice A/B/C/Z):

- 6 **known-memory** cases (`is_known_memory=true`)
- 2 **unknown-memory** cases (`is_known_memory=false`, expected `Z=UNKNOWN`)

The known-memory cases intentionally include conflict scenarios (old vs current values), so the benchmark can measure whether the memory structure helps pick canonical/current facts.

### Fixed runtime parameters (main comparison)

- model: `google/gemini-2.5-flash`
- samples-per-case: `8`
- temperature: `0.9`
- max-completion-tokens: `120`
- timeout-seconds: `90`

### Key source

- Config: `devops/config.yaml.dev`
- API key source priority:
  1. `OPENROUTER_API_KEY` / `OPENAI_API_KEY`
  2. fallback to `agent.api_key` in `devops/config.yaml.dev`

## Commands Executed

### 1) Smoke run

`/workspace/.venv/bin/python experimental/memory_prompt_benchmark/memory_recall_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 2 --temperature 0.4 --max-completion-tokens 120 --timeout-seconds 90`

Output directory:

- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121058/`

Summary:

- flat overall accuracy: `100.00%`
- layered overall accuracy: `100.00%`

### 2) Full run (original cases, higher randomness)

`/workspace/.venv/bin/python experimental/memory_prompt_benchmark/memory_recall_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 6 --temperature 0.7 --max-completion-tokens 120 --timeout-seconds 90`

Output directory:

- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121139/`

Summary:

- flat overall accuracy: `100.00%`
- layered overall accuracy: `100.00%`

### 3) Full run (original cases, temperature=0.9)

`/workspace/.venv/bin/python experimental/memory_prompt_benchmark/memory_recall_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 8 --temperature 0.9 --max-completion-tokens 120 --timeout-seconds 90`

Output directory:

- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121318/`

Summary:

- flat overall accuracy: `100.00%`
- layered overall accuracy: `100.00%`

### 4) Main comparison run (challenging conflict-focused cases)

After strengthening recall case difficulty (conflicting/decoy values + strict unknown handling):

`/workspace/.venv/bin/python experimental/memory_prompt_benchmark/memory_recall_benchmark.py --config devops/config.yaml.dev --model "google/gemini-2.5-flash" --samples-per-case 8 --temperature 0.9 --max-completion-tokens 120 --timeout-seconds 90`

Output directory:

- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121559/`

## Main Result Snapshot (run `20260326_121559`)

From `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121559/report.md`:

- overall accuracy: `flat 50.00%` -> `layered 100.00%`
- known-memory accuracy: `flat 33.33%` -> `layered 100.00%`
- unknown-case hallucination: `flat 0.00%` -> `layered 0.00%`

Key per-case gaps:

- `r01_codename`: `flat 0.00%` vs `layered 100.00%`
- `r02_wakeup_weekday`: `flat 0.00%` vs `layered 100.00%`
- `r03_drink`: `flat 0.00%` vs `layered 100.00%`
- `r05_city`: `flat 0.00%` vs `layered 100.00%`

## Expected Outcome (Acceptance Criteria)

For the main comparison setting (`samples-per-case=8`, `temperature=0.9`, same model/query set):

1. **Layered should not reduce known-memory accuracy**
   - `layered.known_case_accuracy >= flat.known_case_accuracy`

2. **Layered should not increase unknown-memory hallucination**
   - `layered.unknown_hallucination_rate <= flat.unknown_hallucination_rate`

3. **Layered should improve or keep overall recall**
   - `layered.overall_accuracy >= flat.overall_accuracy`

4. **Primary target**
   - `layered.known_case_accuracy >= 0.90`

## Verdict for this record

Using run `20260326_121559`:

- Criteria 1: PASS (`100.00% >= 33.33%`)
- Criteria 2: PASS (`0.00% <= 0.00%`)
- Criteria 3: PASS (`100.00% >= 50.00%`)
- Criteria 4: PASS (`100.00% >= 90.00%`)

## Artifacts

- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121058/report.md`
- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121058/raw_data.json`
- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121139/report.md`
- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121139/raw_data.json`
- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121318/report.md`
- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121318/raw_data.json`
- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121559/report.md`
- `experimental/memory_prompt_benchmark/results/memory_recall_20260326_121559/raw_data.json`

## Notes

- The first three runs produced no difference (both variants 100%), so recall cases were made harder to surface structural differences.
- Keep model, case set, and runtime params fixed when doing regression comparisons.
