"""Text Turn Orchestrator：唯一将助手回复写入 transcript.jsonl 的入口。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .client import default_model, get_client
from .file_store import append_jsonl, read_text
from .memory_update import memory_update_after_turn, schedule_memory_update_after_turn
from .models import (
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    load_context_meta,
    load_prompt_bundle,
    load_transcript,
)
from .paths import WorkspacePaths
from .prompts import build_system_prompt
from .utc import local_date_str, utc_iso_ts
from .llm_trace import (
    TRANSCRIPT_MSG_UUID_KEY,
    emit_trace,
    summarize_completion_response,
    summarize_messages,
)
from .workspace_init_tools import (
    REPL_WRITABLE_RELATIVE_PATHS,
    build_openai_repl_tools,
    execute_tool_call,
    openai_assistant_message_dict,
)

_REPL_USER_PROFILE_TOOL_MAX_ROUNDS = 24


def _openai_messages_payload(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop underscore-prefixed keys (e.g. transcript uuid) before chat.completions."""
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]


def _run_turn_with_user_profile_tools(
    messages: list[dict[str, Any]],
    root: Path,
    *,
    llm_trace: bool = False,
) -> str:
    """chat.completions + user_profile_record，直到模型不再调用工具。"""
    client = get_client()
    model = default_model()
    tools = build_openai_repl_tools()
    if not tools:
        raise RuntimeError("build_openai_repl_tools() returned empty list")
    last_text = ""
    for round_idx in range(1, _REPL_USER_PROFILE_TOOL_MAX_ROUNDS + 1):
        resp = client.chat.completions.create(
            model=model,
            messages=_openai_messages_payload(messages),
            tools=tools,
            parallel_tool_calls=False,
        )
        if llm_trace:
            emit_trace(
                "repl.turn",
                round_idx=round_idx,
                model=model,
                messages=summarize_messages(
                    messages,
                    ws_label=root.name,
                    trace_day=local_date_str(),
                ),
                response=summarize_completion_response(resp),
            )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        messages.append(openai_assistant_message_dict(msg))
        if not tool_calls:
            last_text = (msg.content or "").strip()
            break
        for tc in tool_calls:
            fn = tc.function
            name = fn.name
            args = fn.arguments if fn.arguments is not None else ""
            result = execute_tool_call(
                root,
                name,
                args,
                write_allowlist=REPL_WRITABLE_RELATIVE_PATHS,
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
    else:
        raise RuntimeError(
            f"repl user_profile tool loop exceeded max_rounds={_REPL_USER_PROFILE_TOOL_MAX_ROUNDS}"
        )
    return last_text


def _required_workspace_file_paths(paths: WorkspacePaths) -> tuple[Path, ...]:
    return (
        paths.identity,
        paths.soul,
        paths.user_md,
        paths.memory_md,
        paths.transcript,
    )


def is_workspace_initialized(workspace: Path) -> bool:
    """与 run_turn 相同：五件套存在则认为已初始化。"""
    paths = WorkspacePaths(root=workspace.resolve())
    for p in _required_workspace_file_paths(paths):
        if not p.is_file():
            return False
    return True


# IDENTITY/USER 仍像模板或未约定时的子串（与 bootstrap 桩、示例工作区一致；用于启动时是否先开口）
_IDENTITY_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "还没定",
    "等你来",
    "待对话填充",
)
_USER_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "等待你告诉",
    "等待观察",
    "待对话填充",
)


def _transcript_is_empty(paths: WorkspacePaths) -> bool:
    if not paths.transcript.is_file():
        return True
    return len(load_transcript(paths.transcript)) == 0


def _text_matches_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    s = text.strip()
    if not s:
        return True
    return any(m in s for m in markers)


def needs_startup_profile_inquiry(workspace: Path) -> bool:
    """
    已初始化、且 transcript 仍为空时：若 IDENTITY 或 USER 仍像占位/未约定，
    则 REPL 启动时应由助手先开口发问（见 main.repl）。
    """
    root = workspace.resolve()
    if not is_workspace_initialized(root):
        return False
    paths = WorkspacePaths(root=root)
    if not _transcript_is_empty(paths):
        return False
    ident = read_text(paths.identity) if paths.identity.is_file() else ""
    user_md = read_text(paths.user_md) if paths.user_md.is_file() else ""
    id_stub = _text_matches_any_marker(ident, _IDENTITY_STUB_MARKERS)
    user_stub = _text_matches_any_marker(user_md, _USER_STUB_MARKERS)
    return id_stub or user_stub


def _require_workspace_files(paths: WorkspacePaths) -> None:
    for p in _required_workspace_file_paths(paths):
        if not p.is_file():
            raise ValueError(f"missing required workspace file: {p}")


def _truncate_transcript(msgs: list[ChatMessage]) -> list[ChatMessage]:
    if len(msgs) <= TRANSCRIPT_WINDOW_MAX_MESSAGES:
        return msgs
    return msgs[-TRANSCRIPT_WINDOW_MAX_MESSAGES:]


def run_turn(
    workspace: Path,
    user_text: str,
    *,
    debug_print_system: bool = False,
    defer_memory_update: bool = True,
    llm_trace: bool = False,
) -> str:
    """defer_memory_update=True：记忆管线入队后台跑，先返回助手文本（repl 先打印）；False：单轮 CLI 退出前跑完。"""
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    _require_workspace_files(paths)
    get_client()

    context = load_context_meta(paths.context_json)
    bundle = load_prompt_bundle(paths, meta=context)
    transcript = _truncate_transcript(load_transcript(paths.transcript))

    system = build_system_prompt(bundle, context, enable_user_profile_tool=True)
    if debug_print_system:
        print(system)
        print("=" * 80)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in transcript:
        row: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.uuid:
            row[TRANSCRIPT_MSG_UUID_KEY] = m.uuid
        messages.append(row)

    user_msg_uuid = str(uuid.uuid4())
    messages.append(
        {
            "role": "user",
            "content": user_text,
            TRANSCRIPT_MSG_UUID_KEY: user_msg_uuid,
        }
    )

    # Must snapshot user time before the LLM call; assistant time is taken after (below).
    ts_user = utc_iso_ts()
    assistant_text = _run_turn_with_user_profile_tools(
        messages, root, llm_trace=llm_trace
    )

    assistant_msg_uuid = str(uuid.uuid4())
    append_jsonl(
        paths.transcript,
        {
            "role": "user",
            "content": user_text,
            "ts": ts_user,
            "uuid": user_msg_uuid,
        },
    )
    ts_asst = utc_iso_ts()
    append_jsonl(
        paths.transcript,
        {
            "role": "assistant",
            "content": assistant_text,
            "ts": ts_asst,
            "uuid": assistant_msg_uuid,
        },
    )

    if defer_memory_update:
        schedule_memory_update_after_turn(
            paths,
            user_text=user_text,
            assistant_text=assistant_text,
            llm_trace=llm_trace,
        )
    else:
        memory_update_after_turn(
            paths,
            user_text=user_text,
            assistant_text=assistant_text,
            llm_trace=llm_trace,
        )

    return assistant_text
