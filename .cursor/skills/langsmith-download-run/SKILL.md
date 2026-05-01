---
name: langsmith-download-run
description: >-
  Fetches one LangSmith run (and optionally nested child runs) by run ID and
  saves JSON locally. Use when the user gives a LangSmith run UUID, asks to
  download/export/archive a trace run from LangSmith, or debugs companion LLM
  spans via langsmith_trace_id.
---

# LangSmith: download run by ID

## Prerequisites

- Install `langsmith` and `PyYAML` (repo root `requirements.txt` already pins both).

### What `config.yaml` drives (aligned with backend)

The helper script applies the same LangSmith-related process env as [`app/core/config.py`](../../../app/core/config.py) `set_langsmith_environment_variables`:

| Process env | Source in `config.yaml` |
|-------------|-------------------------|
| `LANGCHAIN_API_KEY` | `agent.langchain_api_key`, else shell `LANGCHAIN_API_KEY` / `LANGSMITH_API_KEY` |
| `LANGSMITH_PROJECT` | `{app.name}-{app.environment}`, plus `-{local_username_slug}` when `app.environment` is `local`; defaults mirror [`AppConfig`](../../../app/utils/config.py): `name` defaults to `inty-backend`, `environment` to `dev` if omitted |
| `LANGSMITH_TRACING_V2` | `true` / `false` from `agent.langsmith_tracing_enabled` (default `true` if omitted) |

Inty YAML does **not** define LangSmith API host; for EU / self-hosted, set **`LANGCHAIN_ENDPOINT`** or **`LANGSMITH_ENDPOINT`** in the shell before running (SDK reads those).

## Preferred: repo helper script

Run from **repo root** so default `--config config.yaml` resolves.

```bash
source .venv/bin/activate

python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> -o tmp/langsmith_runs/<RUN_ID>.json

python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> --verbose -o tmp/langsmith_runs/<RUN_ID>.json

python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> --config /path/to/config.yaml -o tmp/langsmith_runs/<RUN_ID>.json

python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> --load-child-runs -o tmp/langsmith_runs/<RUN_ID>.json
```

`-o -` prints JSON to stdout. **`--verbose`** logs resolved `LANGSMITH_PROJECT` and `LANGSMITH_TRACING_V2` to stderr (never the API key).

If `--config` file is missing or not a mapping YAML, only the API key is taken from the environment; project / tracing vars are left unchanged.

## Inline Python (single run)

Prefer running the script so project naming stays identical to the backend. Minimal equivalent:

```python
import json
import os
from pathlib import Path

import yaml
from langsmith import Client

# After loading config.yaml, set os.environ["LANGCHAIN_API_KEY"], LANGSMITH_PROJECT,
# LANGSMITH_TRACING_V2 the same way as app/core/config.py:set_langsmith_environment_variables,
# then:
run_id = "..."
client = Client()
run = client.read_run(run_id, load_child_runs=False)
print(json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False))
```

## Full trace (many runs under one trace_id)

`read_run` returns one row. To pull **all runs sharing the same trace** (offline replay, diff), reuse the logic in [`scripts/replay_chat_to_image_trace.py`](../../../scripts/replay_chat_to_image_trace.py): `Client.read_run(run_id)` to resolve `trace_id`, then `list_runs` filtered by `trace_id`, normalize, and write `TraceRecord` JSON.

## Troubleshooting

- **`read_run` exits 1**: script prints `LangSmith read_run failed for '<uuid>': ...` to stderr (no Python traceback).
- **401 / unauthorized**: wrong or empty `agent.langchain_api_key` in `config.yaml`, or env fallback key does not match the LangSmith workspace for this run.
- **404**: wrong run id, different workspace/project than the key, or run expired per org retention.
