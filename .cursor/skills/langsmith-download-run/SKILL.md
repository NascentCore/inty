---
name: langsmith-download-run
description: >-
  Download LangSmith data to JSON under repo-root `.inty/` (traces/runs
  subdirs): one run by UUID, or an entire trace (every run sharing trace_id;
  nested structure via parent_run_id). Triggers when the user asks to 下载
  langsmith trace、download langsmith trace、export/archive a LangSmith
  trace/run, or debug companion spans via langsmith_trace_id /
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

Helper: [`tools/scripts/download_run.py`](../../../tools/scripts/download_run.py)（**Cyclopts** CLI）。在**仓库根**执行，以便默认 **`--config config.yaml`** 能解析。

**智能体查路径与默认值**：先执行 **`python tools/scripts/download_run.py --help`**（说明省略 **`-o`/`--output`** 时写入 **`./.inty/`**；**`-o -`** 为 stdout）。**`RUN_ID`** 可位置参数传入，也可用显式参数（见 `--help`）。

常用调用（不传 `-o` 即落盘到默认路径）：

```bash
source .venv/bin/activate

python tools/scripts/download_run.py --trace-id "<TRACE_UUID>"
python tools/scripts/download_run.py --run-id "<ANY_RUN_UUID_IN_TRACE>" --entire-trace
python tools/scripts/download_run.py "<RUN_ID>"
```

**`--load-child-runs`**：仅单 run 的 `read_run`；勿与 `--trace-id` / `--entire-trace` 同用。

**Trace 模式**（`--trace-id` 或 `--entire-trace`）：可选 **`--project-name`** 覆盖 `LANGSMITH_PROJECT`（**若 trace 实际落在别的 project**——例如元数据里的 `inty-backend-local-<user>`——而 `config.yaml` 推出的是 `inty-backend-test` 等，则必须指定，否则 `list_runs` 可能 0 条）。省略 **`--max-runs`** 时由 LangSmith SDK **cursor 分页拉全 trace**；仅调试或限流时传 **`--max-runs N`** 做总条数上限。

Trace 模式输出 JSON 形状：

- **`download_kind`**: `"langsmith_trace"`
- **`trace_id`**, **`project_name`**, **`fetched_at`**, **`run_count`**
- **`runs`**: array of run objects (`model_dump` from LangSmith), same trace

若 **`--config`** 缺失或非 mapping YAML，仅从环境取 API key；`LANGSMITH_PROJECT` / tracing 变量不改。

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

For trace-wide listing in custom code, mirror this script: `Client.list_runs(trace_id=..., limit=..., project_name=...)` with the same fallback as [`tools/scripts/replay_chat_to_image_trace.py`](../../../tools/scripts/replay_chat_to_image_trace.py) when `trace_id` is unsupported.

## Troubleshooting

- **`read_run` / trace fetch exits 1**: script prints the LangSmith error to stderr (no Python traceback).
- **401 / unauthorized**: wrong or empty `agent.langchain_api_key` in `config.yaml`, or env fallback key does not match the LangSmith workspace for this run.
- **404**: wrong run id, different workspace/project than the key, or run expired per org retention.
- **Incomplete trace / 0 runs**：若传了 **`--max-runs`** 且 **`run_count`** 仍小于预期，是人为上限；若未传 **`--max-runs`** 仍偏少，核对 **`--project-name`** 是否与该 trace 所在 LangSmith 项目一致。
- **管道 / 只要 stdout**：显式 **`-o -`**（省略 `-o` 时会写入 `.inty/` 下默认文件）。
