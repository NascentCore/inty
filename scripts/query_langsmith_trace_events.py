#!/usr/bin/env python3
"""
最小 LangSmith 查询脚本：
- 查询指定 project 的 runs（默认 run_type=llm）
- 按 metadata 中的用户字段筛选（默认 metadata.user_id）
- 可选加载每个 run 的 events（read_run）
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Annotated, Any

import cyclopts
from loguru import logger

app = cyclopts.App(help="查询 LangSmith trace events 并筛选指定用户的 LLM 调用")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _read_dotted_key(data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _collect_event_summaries(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list):
        return []

    summaries: list[dict[str, Any]] = []
    for event in events:
        if isinstance(event, dict):
            event_name = event.get("name") or event.get("event")
            event_time = event.get("time") or event.get("timestamp")
            event_message = event.get("message")
        else:
            event_name = getattr(event, "name", None) or getattr(event, "event", None)
            event_time = getattr(event, "time", None) or getattr(event, "timestamp", None)
            event_message = getattr(event, "message", None)

        summaries.append(
            {
                "name": _json_safe(event_name),
                "timestamp": _json_safe(event_time),
                "message_preview": (
                    str(event_message)[:160] if event_message is not None else None
                ),
            }
        )
    return summaries


def _extract_model_name(run: Any) -> str | None:
    inputs = getattr(run, "inputs", None)
    if isinstance(inputs, dict):
        model = inputs.get("model")
        if model:
            return str(model)
    return None


@app.default
def main(
    project_name: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--project-name",
            help="LangSmith project 名称；未传时读取环境变量 LANGSMITH_PROJECT",
        ),
    ] = None,
    run_type: Annotated[
        str,
        cyclopts.Parameter(name="--run-type", help="run 类型，默认 llm"),
    ] = "llm",
    user_id: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name="--user-id",
            help="按用户筛选（可重复传入，例如 --user-id u1 --user-id u2）",
            required=False,
        ),
    ] = None,
    metadata_key: Annotated[
        str,
        cyclopts.Parameter(
            name="--metadata-key",
            help="用户字段在 metadata 里的键，支持点路径（默认 user_id）",
        ),
    ] = "user_id",
    limit: Annotated[
        int,
        cyclopts.Parameter(name="--limit", help="最多拉取多少条 run"),
    ] = 100,
    offset: Annotated[
        int,
        cyclopts.Parameter(name="--offset", help="分页偏移量"),
    ] = 0,
    filter_expr: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--filter",
            help='LangSmith 原生过滤表达式，例如 and(eq(status, "error"), gt(latency, 1.0))',
            required=False,
        ),
    ] = None,
    include_events: Annotated[
        bool,
        cyclopts.Parameter(
            name="--include-events",
            help="是否对命中的 run 调用 read_run，并输出 events 摘要",
        ),
    ] = False,
    output_json: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--output-json",
            help="可选：将结果写入 JSON 文件",
            required=False,
        ),
    ] = None,
) -> None:
    """
    示例：

    1) 按用户筛选最近 50 条 llm runs
       PYTHONPATH=. python scripts/query_langsmith_trace_events.py \\
         --project-name my-app-production \\
         --user-id user_123 \\
         --limit 50

    2) 叠加 LangSmith 服务器端过滤表达式
       PYTHONPATH=. python scripts/query_langsmith_trace_events.py \\
         --project-name my-app-production \\
         --filter 'eq(status, "error")' \\
         --include-events
    """
    try:
        from langsmith import Client
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "未安装 langsmith。请先执行：pip install -r scripts/requirements.txt"
        ) from e

    project_name_final = project_name or os.getenv("LANGSMITH_PROJECT")
    if not project_name_final:
        raise ValueError(
            "缺少 project_name。请传 --project-name，或设置 LANGSMITH_PROJECT。"
        )
    if limit <= 0:
        raise ValueError("--limit 必须 > 0")
    if offset < 0:
        raise ValueError("--offset 必须 >= 0")

    target_user_ids = {
        candidate.strip() for candidate in (user_id or []) if candidate.strip()
    }

    logger.debug(
        "LangSmith 查询参数: project_name={}, run_type={}, limit={}, offset={}, filter={}, metadata_key={}, target_user_ids={}",
        project_name_final,
        run_type,
        limit,
        offset,
        filter_expr,
        metadata_key,
        sorted(target_user_ids),
    )

    client = Client()
    list_run_kwargs: dict[str, Any] = {
        "project_name": project_name_final,
        "run_type": run_type,
        "limit": limit,
        "offset": offset,
    }
    if filter_expr:
        list_run_kwargs["filter"] = filter_expr

    # 关键步骤：
    # 1) list_runs 做批量粗筛；
    # 2) 再按 metadata.user_id（可配置）做二次筛选；
    # 3) 需要 trace events 时，再对命中的 run 调 read_run 补全细节。
    matched: list[dict[str, Any]] = []
    for run in client.list_runs(**list_run_kwargs):
        metadata = getattr(run, "metadata", None)
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        user_value = _read_dotted_key(metadata_dict, metadata_key)
        user_value_str = str(user_value) if user_value is not None else None

        if target_user_ids and user_value_str not in target_user_ids:
            continue

        run_for_details = client.read_run(run.id) if include_events else run
        events = getattr(run_for_details, "events", None) if include_events else None
        event_summaries = _collect_event_summaries(events) if include_events else []

        result = {
            "run_id": str(getattr(run, "id", "")),
            "name": _json_safe(getattr(run, "name", None)),
            "run_type": _json_safe(getattr(run, "run_type", None)),
            "status": _json_safe(getattr(run, "status", None)),
            "error": _json_safe(getattr(run, "error", None)),
            "start_time": _json_safe(getattr(run, "start_time", None)),
            "end_time": _json_safe(getattr(run, "end_time", None)),
            "latency": _json_safe(getattr(run, "latency", None)),
            "model": _extract_model_name(run),
            "metadata_user_value": user_value_str,
            "event_count": len(event_summaries),
            "event_summaries": event_summaries,
        }
        matched.append(result)

    print(
        f"Matched {len(matched)} runs in project '{project_name_final}' "
        f"(run_type={run_type}, requested_limit={limit}, offset={offset})"
    )
    for item in matched:
        print(
            "- run_id={run_id} user={user} model={model} status={status} events={events}".format(
                run_id=item["run_id"],
                user=item["metadata_user_value"],
                model=item["model"],
                status=item["status"],
                events=item["event_count"],
            )
        )

    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(matched, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved JSON results to: {output_path}")


if __name__ == "__main__":
    app()
