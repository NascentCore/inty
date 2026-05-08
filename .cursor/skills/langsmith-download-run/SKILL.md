---
name: langsmith-download-run
description: >-
  Download LangSmith data to JSON: one run by UUID, or an entire trace (every
  run sharing trace_id; nested structure via parent_run_id). Triggers when the
  user asks to 下载 langsmith trace、download langsmith trace、export/archive a
  LangSmith trace/run, or debug companion spans via langsmith_trace_id /
  langsmith_run_id.
---

# LangSmith: download run or full trace

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

### Full trace (default for「下载 / download LangSmith trace」)

Trace mode lists **all runs** with the same `trace_id` (every nested span is one row; hierarchy is `parent_run_id` on each row). This is the default interpretation when the user asks to download a **trace**, not a single run.

```bash
source .venv/bin/activate

python .cursor/skills/langsmith-download-run/scripts/download_run.py \
  --trace-id "<TRACE_UUID>" \
  -o tmp/langsmith_traces/<TRACE_UUID>.json
```

If the user only has **some run id** from the UI (any span in the trace):

```bash
python .cursor/skills/langsmith-download-run/scripts/download_run.py \
  "<ANY_RUN_UUID_IN_TRACE>" \
  --entire-trace \
  -o tmp/langsmith_traces/from_run_<ANY_RUN_UUID_IN_TRACE>.json
```

Optional: **`--project-name`** overrides `LANGSMITH_PROJECT` for `list_runs`. **`--max-runs N`** sets the requested batch size (default **100**). LangSmith **`/runs/query`** rejects `limit` above **100**; the script clamps larger values and prints a note to stderr. Traces with more than **100** spans require pagination (not implemented in this script yet); until then you only get the first batch.

Output JSON shape:

- **`download_kind`**: `"langsmith_trace"`
- **`trace_id`**, **`project_name`**, **`fetched_at`**, **`run_count`**
- **`runs`**: array of run objects (`model_dump` from LangSmith), same trace

### Single run (one UUID)

```bash
python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> \
  -o tmp/langsmith_runs/<RUN_ID>.json

python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> --verbose \
  -o tmp/langsmith_runs/<RUN_ID>.json

python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> \
  --config /path/to/config.yaml -o tmp/langsmith_runs/<RUN_ID>.json

python .cursor/skills/langsmith-download-run/scripts/download_run.py <RUN_ID> \
  --load-child-runs -o tmp/langsmith_runs/<RUN_ID>.json
```

**`--load-child-runs`** applies **only** to single-run `read_run`: API returns that run with nested child runs embedded. Do **not** combine with `--trace-id` / `--entire-trace`.

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

For trace-wide listing in custom code, mirror this script: `Client.list_runs(trace_id=..., limit=..., project_name=...)` with the same fallback as [`scripts/replay_chat_to_image_trace.py`](../../../scripts/replay_chat_to_image_trace.py) when `trace_id` is unsupported.

## Troubleshooting

- **`read_run` / trace fetch exits 1**: script prints the LangSmith error to stderr (no Python traceback).
- **401 / unauthorized**: wrong or empty `agent.langchain_api_key` in `config.yaml`, or env fallback key does not match the LangSmith workspace for this run.
- **404**: wrong run id, different workspace/project than the key, or run expired per org retention.
- **Incomplete trace**: LangSmith caps **`limit`** at **100** per query; this script does not page yet. If **`run_count`** equals **`max-runs`** and you expect more spans, the trace was truncated.
