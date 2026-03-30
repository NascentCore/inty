# RESULTS

## Run metadata

- Run ID: `20260330T110255Z`
- Generated at: `2026-03-30T11:03:51.505325+00:00`
- Model ID: `deepseek/deepseek-v3.2`
- Mode: `dry-run` (synthetic response simulation)
- Trials per cell: `10`
- Matrix size: `9 utilizations * 9 instruction counts * 3 profiles = 243 cells`
- Total trials: `2430`

Source artifacts:

- `research/llms_contextual_instructions_capacity/results/20260330T110255Z/trial_results.jsonl`
- `research/llms_contextual_instructions_capacity/results/20260330T110255Z/cell_summary.csv`
- `research/llms_contextual_instructions_capacity/results/20260330T110255Z/failure_taxonomy.md`
- `research/llms_contextual_instructions_capacity/results/20260330T110255Z/limit_recommendation.json`
- `research/llms_contextual_instructions_capacity/results/20260330T110255Z/summary.json`
- `research/llms_contextual_instructions_capacity/results/20260330T110255Z/summary.md`

## Thresholds used

- IA >= `0.95`
- RSR >= `0.85`
- Effectiveness >= `0.92`
- Format error rate <= `0.02`

## Quantitative result summary

From `limit_recommendation.json`:

- `<=8` instructions: `U_rec = None`, `U_hard = 0.25`
- `<=16` instructions: `U_rec = None`, `U_hard = 0.25`
- `<=32` instructions: `U_rec = None`, `U_hard = 0.25`
- `<=64` instructions: `U_rec = None`, `U_hard = 0.25`

Interpretation for this run:

- Under current synthetic stress profile and strict CI-gated thresholds, no utilization level qualified as a recommended safe zone.
- The hard-limit detector first triggered at utilization `0.25` for all instruction buckets.

## Qualitative failure summary

From `failure_taxonomy.md`:

- `wrong_value`: `1217`
- `omission_or_partial`: `234`
- `global_override_or_non_json`: `62`
- `unknown`: `0`

Observed failure pattern:

1. Wrong-value errors dominate, indicating value fidelity degrades before full schema collapse.
2. Omission/partial outputs become visible as instruction count grows.
3. Non-JSON/global-override failures appear in higher-load regions and larger instruction counts.

## Conclusions

1. The benchmark pipeline is working end-to-end and can produce both quantitative limits and qualitative failure classes.
2. This specific run is a **dry-run synthetic baseline**, so its numeric limits are calibration output for the harness, not production model truth.
3. For production guidance, run the exact same matrix in live mode (set `OPENROUTER_API_KEY`) and then treat `U_rec` as operating target and `U_hard` as fail-fast boundary.

## Recommended next step for production-grade guideline

Run live benchmark with at least `30` trials per cell:

`python3 research/llms_contextual_instructions_capacity/run_benchmark.py --model deepseek/deepseek-v3.2 --trials-per-cell 30 --output-dir research/llms_contextual_instructions_capacity/results`

Then update this file with the live run ID and final recommended context utilization limits per instruction bucket.
