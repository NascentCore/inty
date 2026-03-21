# TEST STEPS — Model Essense Study Framework

## Scope
This document validates framework scaffolding only (not full experiment execution).

## Preconditions
- Run from repo root (`/workspace`).
- `config.yaml` exists.
- Python environment includes dependencies from:
  - `requirements.txt`
  - `research/model_essense_study/requirements.txt`

## 1) CLI Help
Command:
```bash
PYTHONPATH=. python research/model_essense_study/main.py --help
```
Expected:
- Command exits 0.
- Subcommands are listed:
  - `extract-personas`
  - `build-stimuli-dataset`
  - `build-manifest-file`
  - `run-inference`
  - `analyze`
  - `report`

## 2) Persona Scaffold (Mock Mode)
Command:
```bash
PYTHONPATH=. python research/model_essense_study/main.py extract-personas --use-mock-data
```
Expected:
- File created: `research/model_essense_study/data/personas/personas_v1.json`
- `selected_count` equals configured target (default 10).

## 3) Stimulus Scaffold (Mock Mode)
Command:
```bash
PYTHONPATH=. python research/model_essense_study/main.py build-stimuli-dataset --use-mock-data
```
Expected:
- File created: `research/model_essense_study/data/stimuli/stimuli_v1.jsonl`
- Summary created: `research/model_essense_study/data/stimuli/stimuli_v1_summary.json`
- Summary `selected_count` is close to configured target (default 100).

## 4) Manifest Generation
Command:
```bash
PYTHONPATH=. python research/model_essense_study/main.py build-manifest-file
```
Expected:
- File created: `research/model_essense_study/data/manifests/manifest_v1.json`
- `total_cells = model_count * persona_count * stimulus_count * repeats_per_cell`

## 5) Inference Scaffold (No Real Calls)
Command:
```bash
PYTHONPATH=. python research/model_essense_study/main.py run-inference --max-records 12
```
Expected:
- JSONL created: `research/model_essense_study/results/latest/raw/responses_scaffold.jsonl`
- Summary created: `research/model_essense_study/results/latest/run_summary.json`
- All records are in error status with clear "not implemented" message (framework-stage behavior).

## 6) Analysis Scaffold
Command:
```bash
PYTHONPATH=. python research/model_essense_study/main.py analyze
```
Expected:
- File created: `research/model_essense_study/results/latest/analysis/analysis_summary.json`
- Summary contains:
  - `records_total`
  - `records_success`
  - `records_refusal`
  - `records_error`

## 7) Report Scaffold
Command:
```bash
PYTHONPATH=. python research/model_essense_study/main.py report
```
Expected:
- Report created: `research/model_essense_study/results/latest/report.md`
- Figure placeholders created in:
  - `research/model_essense_study/results/latest/figures/`

## 8) Quick Structural Assertions
- Persona file includes fields:
  - `persona_id`, `source_agent_id`, `gender`, `age_band`, `personality_cluster`
- Stimulus file includes fields:
  - `stimulus_id`, `text`, `source_chat_id_hash`, `english_ratio`, `topic_bucket`
- Manifest item includes fields:
  - `task_id`, `model_id`, `persona`, `stimulus`, `repeat_index`

