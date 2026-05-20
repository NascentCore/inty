# SDFT validation log

GPU/CUDA/vLLM failures on CPU-only hosts are **expected** (`expected: true`).
Cloud GPU runs should be appended under `## Cloud GPU run`.

### 2026-05-17T13:12:22Z

- **command**: `bash /workspace/research/sdft/scripts/clone_upstream.sh`
- **exit_code**: 0
- **expected**: false
- **reason**: OK
- **stderr_excerpt**:

```
HEAD is now at d775732 Update README.md
```

### 2026-05-17T13:12:24Z

- **command**: `/usr/bin/python3 -c "import torch; print(torch.cuda.is_available())"`
- **exit_code**: 0
- **expected**: true
- **reason**: EXPECTED_CUDA_NOT_AVAILABLE
- **stderr_excerpt**:

```
False
```

### 2026-05-17T13:12:25Z

- **command**: `import distil_trainer`
- **exit_code**: 1
- **expected**: true
- **reason**: EXPECTED_MISSING_VLLM_EXTRA
- **stderr_excerpt**:

```
ModuleNotFoundError: No module named 'trl.extras.vllm_client'
```

### 2026-05-17T13:12:29Z

- **command**: `PYTHONPATH=/workspace /usr/bin/python3 /workspace/research/sdft/main.py train -c /workspace/research/sdft/configs/smoke.yaml --dry-run`
- **exit_code**: 0
- **expected**: false
- **reason**: OK
- **stderr_excerpt**:

```
[transformers] warmup_ratio is deprecated and will be removed in v5.2. Use `warmup_steps` instead.
2026-05-17 13:12:28.690 | INFO     | research.sdft.runner:dry_run_train:104 - dry_run ok: dataset=toy rows=1 output_dir=/workspace/research/sdft/results/smoke
```

### 2026-05-17T13:12:32Z

- **command**: `PYTHONPATH=/workspace /usr/bin/python3 /workspace/research/sdft/main.py train -c /workspace/research/sdft/configs/smoke.yaml`
- **exit_code**: 1
- **expected**: true
- **reason**: EXPECTED_VLLM_NO_GPU
- **stderr_excerpt**:

```
Traceback (most recent call last):
  File "/workspace/research/sdft/main.py", line 273, in <module>
    app()
  File "/home/ubuntu/.local/lib/python3.12/site-packages/cyclopts/core.py", line 1947, in __call__
    result = _run_maybe_async_command(command, bound, resolved_backend)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ubuntu/.local/lib/python3.12/site-packages/cyclopts/_run.py", line 50, in _run_maybe_async_command
    return command(*bound.args, **bound.kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/workspace/research/sdft/main.py", line 104, in train
    run_train(cfg)
  File "/workspace/research/sdft/runner.py", line 118, in run_train
    from distil_trainer import DistilTrainer  # noqa: WPS433
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/workspace/research/sdft/upstream/distil_trainer.py", line 51, in <module>
    from trl.extras.vllm_client import VLLMClient
ModuleNotFoundError: No module named 'trl.extras.vllm_client'
```

### 2026-05-17T13:12:36Z

- **command**: `/usr/bin/python3 /workspace/research/sdft/upstream/eval_tooluse.py --help`
- **exit_code**: 1
- **expected**: true
- **reason**: EXPECTED_VLLM_NOT_INSTALLED
- **stderr_excerpt**:

```
Traceback (most recent call last):
  File "/workspace/research/sdft/upstream/eval_tooluse.py", line 8, in <module>
    from vllm import LLM, SamplingParams
ModuleNotFoundError: No module named 'vllm'
```

### 2026-05-17T13:12:39Z

- **command**: `/usr/bin/python3 /workspace/research/sdft/upstream/eval_science.py --help`
- **exit_code**: 1
- **expected**: true
- **reason**: EXPECTED_VLLM_NOT_INSTALLED
- **stderr_excerpt**:

```
Traceback (most recent call last):
  File "/workspace/research/sdft/upstream/eval_science.py", line 8, in <module>
    from vllm import LLM, SamplingParams
ModuleNotFoundError: No module named 'vllm'
```
