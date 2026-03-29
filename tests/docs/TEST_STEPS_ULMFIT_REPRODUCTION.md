# TEST_STEPS_ULMFIT_REPRODUCTION

## Goal

Validate that `research/ulmfit/` provides a runnable ULMFiT-style 3-stage experiment pipeline:

1. Language model pretraining (general corpus).
2. Target task language model fine-tuning (task unlabeled text).
3. Text classifier fine-tuning with ULMFiT tricks (discriminative LR, slanted triangular LR, gradual unfreezing).

## Success Criteria

1. A single CLI command runs the full 3-stage pipeline end-to-end.
2. The run writes checkpoints and metrics to the configured output directory.
3. The metrics file contains at least:
   - pretraining perplexity
   - target-task LM perplexity
   - classifier validation/test accuracy
4. A smoke config can run fully offline (toy data) on CPU.

## Commands

Run in repo root:

1. Install dependencies:
   - `source .venv/bin/activate && pip install -r research/ulmfit/requirements.txt`
2. Run smoke experiment:
   - `source .venv/bin/activate && python3 research/ulmfit/main.py run --config research/ulmfit/configs/smoke.yaml`
3. Inspect output artifacts:
   - `ls -la research/ulmfit/output/smoke`
   - `python3 -c "import json;print(json.dumps(json.load(open('research/ulmfit/output/smoke/metrics_summary.json')), indent=2))"`

## Evidence to Attach in PR / Handoff

1. Terminal output of smoke run.
2. `metrics_summary.json` content excerpt.
3. Output directory tree listing showing checkpoints.
