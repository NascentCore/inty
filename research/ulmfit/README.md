# ULMFiT Reproduction (arXiv:1801.06146)

This directory contains a runnable ULMFiT-style reproduction experiment implemented with a modern mainstream framework: **PyTorch**.

## Implemented ULMFiT ideas

1. **General-domain LM pretraining** (`pretrain_lm`)
2. **Target-task LM fine-tuning** (`finetune_lm`)
3. **Classifier fine-tuning** with:
   - concat pooling head
   - slanted triangular learning rates (STLR)
   - discriminative layer-wise learning rates
   - gradual unfreezing

The implementation is intentionally minimal and reproducible-first for research iteration.

## Directory structure

- `main.py`: Cyclopts CLI entrypoint
- `config.py`: Pydantic config schema
- `data.py`: dataset loading + vocab/tokenization utilities
- `modeling.py`: AWD-LSTM-like encoder + LM + classifier
- `trainer.py`: 3-stage training pipeline
- `configs/smoke.yaml`: CPU/offline smoke config
- `configs/imdb_wikitext2_full.yaml`: external dataset config (IMDb + WikiText-2)

## Quick start (smoke run)

From repo root:

1. Install dependencies:
   - `source .venv/bin/activate && pip install -r research/ulmfit/requirements.txt`
2. Run:
   - `source .venv/bin/activate && python3 research/ulmfit/main.py run --config research/ulmfit/configs/smoke.yaml`
   - or `source .venv/bin/activate && python3 -m research.ulmfit.main run --config research/ulmfit/configs/smoke.yaml`

Outputs are written to the configured `output_dir`, including:

- `metrics_summary.json`
- `lm_pretrained.pt`
- `lm_finetuned.pt`
- `classifier.pt`
- `vocab.txt`

## Full reproduction setting

Use `configs/imdb_wikitext2_full.yaml` to approximate the paper-style setup with:

- LM corpus: WikiText-2 (via `datasets`)
- Task: IMDb sentiment (via `datasets`)

Then run the same CLI command with that config file.
