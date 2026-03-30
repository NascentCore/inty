# RESULTS

## Run metadata (live)

- Run ID: `20260330T150952Z`
- Generated at: `2026-03-30T15:11:39.145268+00:00`
- Model ID: `google/gemini-2.5-flash-lite`
- Mode: `live` (real model API)
- Trials per cell: `3` (quick live sweep)
- Matrix size: `4 utilizations * 3 instruction counts * 2 profiles = 24 cells`
- Total trials: `72`

Source artifacts:

- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/trial_results.jsonl`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/cell_summary.csv`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/failure_taxonomy.md`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/limit_recommendation.json`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/summary.json`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/summary.md`

## Thresholds used

- IA >= `0.95`
- RSR >= `0.85`
- Effectiveness >= `0.92`
- Format error rate <= `0.02`

## Quantitative result summary (live)

From live `limit_recommendation.json`:

- `<=8` instructions: `U_rec = None`, `U_hard = 0.55`
- `<=16` instructions: `U_rec = None`, `U_hard = 0.55`
- `<=32` instructions: `U_rec = None`, `U_hard = None`
- `<=64` instructions: `U_rec = None`, `U_hard = None`

Interpretation for this live quick sweep:

- Under strict CI-gated thresholds and only 3 trials per cell, no utilization level reached recommended safe zone (`U_rec=None`).
- For instruction buckets `<=8` and `<=16`, hard-limit detector first triggered at `U=0.55`.
- `<=32` and `<=64` buckets are not applicable in this quick sweep (instruction counts above 16 were not included), so hard limit stays `None`.

## Qualitative failure summary (live)

From live `failure_taxonomy.md`:

- `wrong_value`: `0`
- `omission_or_partial`: `0`
- `global_override_or_non_json`: `4`
- `unknown`: `0`

Observed failure pattern:

1. Main failure mode is formatting wrapper (` ```json ... ``` `), not wrong key-value mapping.
2. Current parser requires pure JSON; markdown code-fence output is counted as format error.
3. No wrong-value / omission seen in this quick live sweep, suggesting core instruction extraction is strong in sampled cells.

## Conclusions

1. Real-model run with `google/gemini-2.5-flash-lite` is successful; benchmark harness works end-to-end in live mode.
2. In this quick live sample, the model mainly fails on strict output format (code-fenced JSON), not on instruction correctness itself.
3. Because trials-per-cell is low (`3`) and matrix is reduced, current `U_hard=0.55` should be treated as provisional.

## Recommended next step for production-grade guideline

Run live benchmark with at least `30` trials per cell and full matrix:

`python3 research/llms_contextual_instructions_capacity/run_benchmark.py --model google/gemini-2.5-flash-lite --trials-per-cell 30 --output-dir research/llms_contextual_instructions_capacity/results`

Then update this file with final `U_rec` and `U_hard` per instruction bucket.

## Previous baseline (dry-run synthetic)

- Run ID: `20260330T110255Z`
- This baseline is retained in `results/20260330T110255Z` for harness calibration comparison.
