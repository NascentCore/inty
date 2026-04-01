#!/usr/bin/env python3
"""
最小 LangSmith 查询脚本：
- 查询指定 project 的 runs（默认 run_type=llm）
- 按 metadata 中的用户字段筛选（默认 metadata.user_id）
- 可选加载每个 run 的 events（read_run）
"""

from __future__ import annotations

import csv
import inspect
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
            event_time = getattr(event, "time", None) or getattr(
                event, "timestamp", None
            )
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


def _escape_filter_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_user_id_filter(*, user_ids: set[str], metadata_key: str) -> str | None:
    if not user_ids:
        return None

    escaped_key = _escape_filter_string(metadata_key)
    clauses = [
        'and(eq(metadata_key, "{key}"), eq(metadata_value, "{value}"))'.format(
            key=escaped_key,
            value=_escape_filter_string(user_id),
        )
        for user_id in sorted(user_ids)
    ]
    if len(clauses) == 1:
        return clauses[0]
    return f"or({', '.join(clauses)})"


def _merge_filters(base_filter: str | None, extra_filter: str | None) -> str | None:
    if base_filter and extra_filter:
        return f"and({base_filter}, {extra_filter})"
    return base_filter or extra_filter


def _filter_supported_kwargs(
    callable_obj: Any, kwargs: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    signature = inspect.signature(callable_obj)
    parameters = signature.parameters
    has_var_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    if has_var_kwargs:
        return (kwargs, [])

    supported_names = set(parameters.keys())
    accepted: dict[str, Any] = {}
    dropped: list[str] = []
    for key, value in kwargs.items():
        if key in supported_names:
            accepted[key] = value
        else:
            dropped.append(key)
    return (accepted, dropped)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    csv_fields = [
        "run_id",
        "name",
        "run_type",
        "status",
        "error",
        "start_time",
        "end_time",
        "latency",
        "model",
        "metadata_user_value",
        "event_count",
        "event_summaries_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "run_id": row.get("run_id"),
                    "name": row.get("name"),
                    "run_type": row.get("run_type"),
                    "status": row.get("status"),
                    "error": row.get("error"),
                    "start_time": row.get("start_time"),
                    "end_time": row.get("end_time"),
                    "latency": row.get("latency"),
                    "model": row.get("model"),
                    "metadata_user_value": row.get("metadata_user_value"),
                    "event_count": row.get("event_count"),
                    "event_summaries_json": json.dumps(
                        row.get("event_summaries", []), ensure_ascii=False
                    ),
                }
            )


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
    trace_filter: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--trace-filter",
            help='作用于根 run 的过滤表达式（示例：and(eq(feedback_key, "user_score"), eq(feedback_score, 1)))',
            required=False,
        ),
    ] = None,
    tree_filter: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--tree-filter",
            help="作用于同一 trace 中其它节点（child/sibling）的过滤表达式",
            required=False,
        ),
    ] = None,
    is_root: Annotated[
        bool | None,
        cyclopts.Parameter(
            name="--is-root",
            help="仅查询根 run（true）或非根 run（false）；不传则不过滤",
            required=False,
        ),
    ] = None,
    select: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name="--select",
            help="仅返回指定字段（可重复传入，参考 run data format 字段名）",
            required=False,
        ),
    ] = None,
    query: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--query",
            help="自然语言查询（experimental，SDK 支持时生效）",
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
    output_csv: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--output-csv",
            help="可选：将结果写入 CSV 文件（适合导出分析）",
            required=False,
        ),
    ] = None,
) -> None:
    """
    示例：

    1) 按用户筛选最近 50 条 llm runs（自动拼接 metadata_key/metadata_value 过滤）
       PYTHONPATH=. python scripts/query_langsmith_trace_events.py \\
         --project-name my-app-production \\
         --user-id user_123 \\
         --limit 50

    2) 使用 trace query syntax 过滤表达式
       PYTHONPATH=. python scripts/query_langsmith_trace_events.py \\
         --project-name my-app-production \\
         --filter 'and(eq(metadata_key, "user_id"), eq(metadata_value, "user_123"))' \\
         --is-root \\
         --include-events
    """
    from langsmith import Client

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
    user_id_filter = _build_user_id_filter(
        user_ids=target_user_ids,
        metadata_key=metadata_key,
    )
    merged_filter_expr = _merge_filters(filter_expr, user_id_filter)

    logger.debug(
        "LangSmith 查询参数: project_name={}, run_type={}, limit={}, offset={}, filter={}, trace_filter={}, tree_filter={}, is_root={}, select={}, query={}, metadata_key={}, target_user_ids={}",
        project_name_final,
        run_type,
        limit,
        offset,
        merged_filter_expr,
        trace_filter,
        tree_filter,
        is_root,
        select,
        query,
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
    if merged_filter_expr:
        list_run_kwargs["filter"] = merged_filter_expr
    if trace_filter:
        list_run_kwargs["trace_filter"] = trace_filter
    if tree_filter:
        list_run_kwargs["tree_filter"] = tree_filter
    if is_root is not None:
        list_run_kwargs["is_root"] = is_root
    if select:
        list_run_kwargs["select"] = select
    if query:
        list_run_kwargs["query"] = query

    supported_kwargs, dropped_kwargs = _filter_supported_kwargs(
        client.list_runs,
        list_run_kwargs,
    )
    if dropped_kwargs:
        logger.warning(
            "当前 langsmith SDK 不支持以下参数，已忽略: {}",
            dropped_kwargs,
        )

    # 关键步骤：
    # 1) list_runs 做批量粗筛；
    # 2) 用户筛选优先走服务端 filter（metadata_key/metadata_value）；
    # 3) 需要 trace events 时，再对命中的 run 调 read_run 补全细节。
    matched: list[dict[str, Any]] = []
    for run in client.list_runs(**supported_kwargs):
        metadata = getattr(run, "metadata", None)
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        user_value = _read_dotted_key(metadata_dict, metadata_key)
        user_value_str = str(user_value) if user_value is not None else None

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

    if output_csv:
        output_csv_path = Path(output_csv)
        _write_csv(output_csv_path, matched)
        print(f"Saved CSV results to: {output_csv_path}")


if __name__ == "__main__":
    app()
