# TEST_STEPS_PROMPT_INSTRUCTION_POSITION_SWEEP

## Goal

Measure instruction-following effectiveness for a single instruction placed at different token offsets in a 200k-token prompt body, using OpenRouter `deepseek/deepseek-v3.2`.

## Scope

- Single-placement sweep only.
- Positions: `0`, `1k`, `2k`, `4k`, `8k`, ... , `end`.
- Trials: `30` per position.
- Metric: strict follow rate (`response == expected token`) and contains follow rate.

## Setup

```bash
cd experimental/context_window_test
pip install -r requirements.txt
export OPENROUTER_API_KEY="<your-openrouter-api-key>"
```

## Run

```bash
python instruction_position_sweep.py \
  --model deepseek/deepseek-v3.2 \
  --placeholder-tokens 200000 \
  --trials-per-position 30
```

## Outputs

Per run, files are generated in:

`experimental/context_window_test/results/instruction_position_sweep/<run_id>/`

- `trial_results.jsonl`
- `position_summary.csv`
- `summary.json`
- `summary.md`

`latest` symlink points to the newest run.

## Validation checks

1. `summary.json` config matches requested model/position sweep/trial count.
2. Total trial count equals `positions * 30`.
3. `position_summary.csv` includes all expected position labels including `end`.
4. `summary.md` table reports strict rates and Wilson 95% CI.
