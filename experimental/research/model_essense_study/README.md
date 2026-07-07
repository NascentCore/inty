# Model Essence Study (Scaffold + Real Execution Entry)

This directory contains the initial framework for studying model "personality essence"
under roleplay persona variation.

Current stage supports both scaffold mode and real invocation entry:

1. Extract/select personas (target: 10)
2. Curate English stimuli from user chat history (target: 100)
3. Build cartesian manifest across models/personas/stimuli/repeats
4. Run inference in either scaffold mode or real model mode
5. Produce analysis/report/figure placeholders

## Why framework-first

The first implementation step intentionally prioritizes:

- reproducible data contracts
- clean CLI workflow
- auditable artifacts
- readiness for later full-scale experiment runs

## Directory layout

- `main.py`: cyclopts CLI entry
- `config.py`: typed config loader
- `schema.py`: shared Pydantic schemas
- `db.py`: DB candidate loaders
- `persona_builder.py`: persona selection logic
- `stimulus_builder.py`: English curation + dedup logic
- `manifest_builder.py`: experiment cell generation
- `model_client.py`: availability probe + real OpenRouter client
- `runner.py`: inference executor (scaffold/real)
- `analysis.py`: analysis summary scaffold
- `figures.py`: placeholder artifact generation
- `report.py`: markdown report scaffold
- `config.yaml`: local study configuration

## CLI commands

Run from repo root:

```bash
PYTHONPATH=. python research/model_essense_study/main.py --help
```

Core commands:

```bash
# 1) personas
PYTHONPATH=. python research/model_essense_study/main.py extract-personas --config research/model_essense_study/config.yaml

# 2) stimuli (English-only curation)
PYTHONPATH=. python research/model_essense_study/main.py build-stimuli-dataset --config research/model_essense_study/config.yaml

# 3) manifest
PYTHONPATH=. python research/model_essense_study/main.py build-manifest-file --config research/model_essense_study/config.yaml

# 4) inference scaffold (no API calls)
PYTHONPATH=. python research/model_essense_study/main.py run-inference --config research/model_essense_study/config.yaml --max-records 30

# 4b) real inference (OpenRouter-compatible)
# Requires OPENROUTER_API_KEY (or OPENAI_API_KEY) in env.
PYTHONPATH=. python research/model_essense_study/main.py run-inference \
  --config research/model_essense_study/config.yaml \
  --real-run \
  --max-records 30 \
  --requests-per-minute 20

# 5) analysis scaffold
PYTHONPATH=. python research/model_essense_study/main.py analyze --config research/model_essense_study/config.yaml

# 6) report + figure placeholders
PYTHONPATH=. python research/model_essense_study/main.py report --config research/model_essense_study/config.yaml

# 7) model availability probe (includes Claude TODO baseline by default)
PYTHONPATH=. python research/model_essense_study/main.py probe-model-availability --config research/model_essense_study/config.yaml

# 8) run budget and execution-window estimation
PYTHONPATH=. python research/model_essense_study/main.py plan-run-budget --config research/model_essense_study/config.yaml
```

## Notes

- Stimulus source policy: real IntelliMate user history, English-only, no manual semantic rewriting.
- Privacy: textual sanitization for email/phone/url is applied before export.
- This repository environment currently does not have an accessible populated IntelliMate DB snapshot.
  If DB extraction yields empty persona/stimulus sets, use `--use-mock-data` to validate pipeline behavior,
  then rerun against a populated environment for full-scale execution.
- Real execution output paths:
  - `research/model_essense_study/results/latest/raw/responses_real.jsonl`
  - `research/model_essense_study/results/latest/run_summary_real.json`
- Claude availability remains TODO for cross-family full run stage, and is now tracked by `probe-model-availability` output:
  - `research/model_essense_study/docs/MODEL_AVAILABILITY_LATEST.json`
- Budget and execution window estimates are now tracked by `plan-run-budget` output:
  - `research/model_essense_study/docs/RUN_PLAN_LATEST.json`
