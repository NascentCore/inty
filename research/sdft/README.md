# SDFT Reproduction (arXiv:2601.19897)

Research sandbox to reproduce **Self-Distillation Fine-Tuning (SDFT)** using the official implementation:

**https://github.com/idanshen/Self-Distillation**

Paper: [Self-Distillation Enables Continual Learning](https://arxiv.org/abs/2601.19897)

## Reproducibility (upstream pin)

| Field | Value |
|-------|--------|
| Repository | `https://github.com/idanshen/Self-Distillation.git` |
| Pin (commit) | `d77573212fa0a3ae2eeb64b9b44db1c251f75e3e` |
| Tree | https://github.com/idanshen/Self-Distillation/tree/d77573212fa0a3ae2eeb64b9b44db1c251f75e3e |

Clone into `research/sdft/upstream/`:

```bash
bash research/sdft/scripts/clone_upstream.sh
```

## Paper vs official code

- The paper discusses reverse KL; **pinned upstream** uses on-policy sampling with **forward KL** (`DistilConfig.alpha=0.0`). See upstream README changelog.
- Training defaults match upstream [`main.py`](https://github.com/idanshen/Self-Distillation/blob/d77573212fa0a3ae2eeb64b9b44db1c251f75e3e/main.py): teacher EMA `ref_model_mixup_alpha=0.01`, `sync_ref_model=True`, vLLM colocate for 7B.

## No GPU on this host (expected)

Many checks run on **CPU-only** machines. Failures involving CUDA, GPU OOM, or vLLM are **expected** and recorded in [`results/validation_log.md`](results/validation_log.md) with `expected: true`.

**Merging this scaffold does not require a successful GPU train.** A full smoke/P1 run needs a **cloud GPU server** (see Follow-up below).

## Install

From **repository root**:

```bash
bash research/sdft/scripts/clone_upstream.sh
pip install -r research/sdft/requirements-smoke.txt
```

For P1 (7B + vLLM), on a GPU host:

```bash
pip install -r research/sdft/requirements.txt
```

(`requirements.txt` includes `upstream/requirements.txt` after clone.)

## Data

See `research/sdft/scripts/download_data.sh`. Paths are relative to `upstream/`:

- `data/tooluse_data/train_data`
- `data/science_data/train_data`
- `data/science_data/eval_data`

P1 train/eval is **blocked** until data exists on the GPU machine.

## Commands

```bash
# CPU: config + dataset wiring only
python3 research/sdft/main.py train --config research/sdft/configs/smoke.yaml --dry-run

# GPU: smoke toy train (single small model, use_vllm=false in yaml)
python3 research/sdft/main.py train --config research/sdft/configs/smoke.yaml

# GPU: P1 (official-equivalent settings in yaml)
python3 research/sdft/main.py train --config research/sdft/configs/tooluse_7b.yaml
python3 research/sdft/main.py eval --config research/sdft/configs/tooluse_7b.yaml
python3 research/sdft/main.py train --config research/sdft/configs/science_7b.yaml
python3 research/sdft/main.py eval --config research/sdft/configs/science_7b.yaml

# CPU: run checklist and rewrite validation_log.md
PYTHONPATH=. python3 research/sdft/main.py validate
```

Eval invokes upstream `eval_tooluse.py` or `eval_science.py` with `cwd=upstream/`.

Official equivalents (inside `upstream/` after clone):

```bash
python main.py --dataset_name tooluse --model_name Qwen/Qwen2.5-7B-Instruct --output_dir <out> --learning_rate 5e-5 --num_train_epochs 2
python eval_tooluse.py --model_path <out> --output_dir <out>
python main.py --dataset_name science --model_name Qwen/Qwen2.5-7B-Instruct --output_dir <out> --learning_rate 5e-5 --num_train_epochs 2
python eval_science.py --model_path <out> --output_dir <out>
```

## Validation log

[`results/validation_log.md`](results/validation_log.md) stores command, exit code, `expected`, `reason`, and stderr excerpts.

Reasons for expected CPU failures include: `EXPECTED_GPU_MISSING`, `EXPECTED_CUDA_NOT_AVAILABLE`, `EXPECTED_VLLM_NO_GPU`.

After a cloud GPU run, append a section `## Cloud GPU run` with `expected: false` and `exit_code: 0` entries.

## Follow-up / run checklist (not in first scaffold PR)

1. **Rent a cloud GPU** (official notes: one H200 for 7B; minimum try single GPU **≥24GB**).
2. Install full requirements, place datasets under `upstream/data/`.
3. Run smoke train, then P1 train + eval for tooluse and science.
4. Update `results/validation_log.md` and this README with artifact paths.

Later research follow-ups: SFT baseline (P2), sequential three-task + lm_eval forgetting (P3), Medical/Wiki when upstream publishes data.

## Layout

- `config.py` / `configs/*.yaml` — experiment settings
- `runner.py` — calls upstream `DistilTrainer` and eval scripts
- `data_toy.py` — tiny dataset for smoke only
- `upstream/` — pinned clone (gitignored)
