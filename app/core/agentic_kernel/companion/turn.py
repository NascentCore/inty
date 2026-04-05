"""Companion turn executor: 单轮对话的完整执行流程。"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from .file_store import append_jsonl
from .llm_client import CompanionLLMClient
from .memory_pipeline import MemoryPipelineConfig, memory_update_after_turn, schedule_memory_update_after_turn
from .memory_store import MemoryStore
from .models import (
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    ContextMeta,
    PromptBundle,
    load_context_meta,
    load_prompt_bundle,
    load_transcript,
    transcript_for_llm_turn,
)
from .prompts import build_system_prompt
from .tools import WRITABLE_RELATIVE_PATHS, build_companion_tools, execute_tool_call
from .utc import utc_iso_ts
from .workspace import WorkspacePaths, is_workspace_initialized

_MAX_TOOL_ROUNDS = 24

# 与 heartbeat 合成的 user text 一致
HEARTBEAT_SYNTHETIC_USER_TEXT = (
    "（陪伴心跳：用户尚未输入新内容。请读本窗口里**正在进行的场景、话题与语气**，用一两句自然接话，"
    "延续当下氛围与节奏，像同一场对话的下一拍；不要突然换风格、换口吻或像新开一局；"
    "不要提系统、心跳、等待或「我以为你走了」；不要调用工具。）"
)


def _openai_assistant_message_dict(msg: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
    tool_calls = getattr(msg, "tool_calls", None) or []
    if tool_calls:
        row["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "",
                },
            }
            for tc in tool_calls
        ]
    return row


def _preview(s: str, max_len: int = 280) -> str:
    one = s.replace("\n", " ").strip()
    if len(one) <= max_len:
        return one
    return one[: max_len - 1] + "..."


async def run_turn(
    workspace: Path,
    user_text: str,
    *,
    store: MemoryStore,
    llm_client: CompanionLLMClient,
    heartbeat_turn: bool = False,
    defer_memory_update: bool = True,
    memory_config: MemoryPipelineConfig | None = None,
) -> str:
    """
    执行一轮完整对话。

    - 加载 context + prompt bundle + transcript
    - 组装 system prompt + messages
    - 调用 LLM (带 tool loop)
    - 持久化 transcript
    - 调度记忆管线

    返回 assistant_text。
    """
    t0 = time.perf_counter()
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    mem_cfg = memory_config or MemoryPipelineConfig()

    if heartbeat_turn:
        user_text = HEARTBEAT_SYNTHETIC_USER_TEXT

    logger.info(
        "run_turn start path={} user_chars={} heartbeat_turn={} defer_memory={}",
        root,
        len(user_text),
        heartbeat_turn,
        defer_memory_update,
    )

    # 加载 context 与 prompt bundle
    context = load_context_meta(paths.context_json)
    bundle = load_prompt_bundle(paths, store, meta=context)
    loaded = load_transcript(paths.transcript)
    transcript = transcript_for_llm_turn(loaded)

    system = build_system_prompt(
        bundle,
        context,
        enable_tools=not heartbeat_turn,
        heartbeat_turn=heartbeat_turn,
    )

    # 组装 messages
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in transcript:
        messages.append({"role": m.role, "content": m.content})
    user_msg_uuid = str(uuid.uuid4())
    messages.append({"role": "user", "content": user_text})

    ts_user = utc_iso_ts()
    trace_id = str(uuid.uuid4())

    # Tool loop
    tools = [] if heartbeat_turn else build_companion_tools()
    last_text = ""
    t_loop = time.perf_counter()

    for round_idx in range(1, _MAX_TOOL_ROUNDS + 1):
        t_api = time.perf_counter()
        resp = llm_client.chat_completion(
            messages=messages,
            model=llm_client._resolve_model("tool" if tools else "chat"),
            tools=tools or None,
        )
        logger.info(
            "run_turn llm_round={} chat_completions_ms={:.0f} heartbeat={}",
            round_idx,
            (time.perf_counter() - t_api) * 1000.0,
            heartbeat_turn,
        )

        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        messages.append(_openai_assistant_message_dict(msg))

        if not tool_calls:
            last_text = (msg.content or "").strip()
            break

        # 执行 tools
        for tc in tool_calls:
            fn = tc.function
            name = fn.name
            args = fn.arguments if fn.arguments is not None else ""
            logger.info(
                "run_turn tool_call round={} name={} trace_id={}",
                round_idx,
                name,
                trace_id,
            )
            import asyncio
            result = await execute_tool_call(
                root, store, name, args,
                write_allowlist=WRITABLE_RELATIVE_PATHS,
            )
            logger.info(
                "run_turn tool_done round={} name={} result_chars={} ok={}",
                round_idx,
                name,
                len(result),
                not result.startswith("ERROR:"),
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        raise RuntimeError(f"tool loop exceeded max_rounds={_MAX_TOOL_ROUNDS}")

    logger.info(
        "run_turn loop_done rounds={} loop_total_ms={:.0f}",
        round_idx,
        (time.perf_counter() - t_loop) * 1000.0,
    )

    # 持久化 transcript
    assistant_msg_uuid = str(uuid.uuid4())
    user_row: dict[str, Any] = {
        "role": "user",
        "content": user_text,
        "ts": ts_user,
        "uuid": user_msg_uuid,
    }
    if heartbeat_turn:
        user_row["heartbeat"] = True
    user_row["trace_id"] = trace_id
    append_jsonl(paths.transcript, user_row)
    append_jsonl(paths.transcript, {
        "role": "assistant",
        "content": last_text,
        "ts": utc_iso_ts(),
        "uuid": assistant_msg_uuid,
        "reply_to": user_msg_uuid,
        "source": "chat",
        "trace_id": trace_id,
    })

    # 记忆管线
    if heartbeat_turn:
        logger.debug("run_turn memory_pipeline=skipped (heartbeat_turn)")
    elif defer_memory_update:
        def _complete_fn(msgs: list[dict[str, Any]], model_role: str) -> str:
            return llm_client.complete_text(msgs, model_role=model_role)
        schedule_memory_update_after_turn(
            paths,
            store=store,
            user_text=user_text,
            assistant_text=last_text,
            complete_fn=_complete_fn,
            config=mem_cfg,
        )
    else:
        def _complete_fn_sync(msgs: list[dict[str, Any]], model_role: str) -> str:
            return llm_client.complete_text(msgs, model_role=model_role)
        memory_update_after_turn(
            paths,
            store=store,
            user_text=user_text,
            assistant_text=last_text,
            complete_fn=_complete_fn_sync,
            config=mem_cfg,
        )

    logger.info(
        "run_turn done assistant_chars={} ms={:.0f}",
        len(last_text),
        (time.perf_counter() - t0) * 1000.0,
    )
    return last_text
