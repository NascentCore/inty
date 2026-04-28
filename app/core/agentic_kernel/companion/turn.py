"""Companion turn executor: 单轮对话的完整执行流程。"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from app.utils.config import CompanionWorkspaceBootstrapType

from .llm_client import (
    LLM_SCENE_CHAT,
    LLM_SCENE_INNER_TICK,
    LLM_SCENE_TOOL_CALL,
    CompanionLLMClient,
)
from .message_format import openai_assistant_message_dict
from .memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn,
    schedule_memory_update_after_turn,
)
from .memory_store import MemoryStore
from .bootstrap_user_interactive import interactive_bootstrap_active
from .models import (
    INNER_TICK_SYNTHETIC_USER_TEXT,
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    CompanionTurnResult,
    ContextMeta,
    PromptBundle,
    load_context_meta,
    load_prompt_bundle,
    load_transcript_from_store,
    transcript_for_llm_turn,
)
from .transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
    ConversationCompactor,
    load_compaction_state_from_store,
    save_compaction_state_to_store,
    transcript_rows_to_openai_dialogue,
)
from .prompts import build_system_messages
from .significance_perception import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    split_dual_llm_chat_branch_content,
)
from .companion_tool_runtime import (
    WORKSPACE_READ_FILE_MAX_CHARS_CAP,
    execute_tool_call as repl_execute_tool_call,
)
from .runtime_inspect_context import (
    build_last_chat_completion_request_payload,
    build_turn_runtime_config_dict,
    runtime_inspect_begin_turn,
    runtime_inspect_end_turn,
    runtime_inspect_set_last_chat_completion_request,
    runtime_inspect_set_runtime_config,
)
from .tools import (
    WRITABLE_RELATIVE_PATHS,
    build_companion_tools,
    build_openai_repl_tools_inner_tick,
)
from .utc import utc_iso_ts
from .heartbeat import HEARTBEAT_SYNTHETIC_USER_TEXT
from .workspace import WorkspacePaths

_MAX_TOOL_ROUNDS = 24


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
    inner_tick_turn: bool = False,
    defer_memory_update: bool = True,
    memory_config: MemoryPipelineConfig | None = None,
    transcript_compaction: TranscriptCompactionConfig | None = None,
    transcript_llm_window_max_messages: int | None = None,
    repository_only_workspace_text: bool = False,
    workspace_bootstrap_type: str = CompanionWorkspaceBootstrapType.NONE.value,
) -> CompanionTurnResult:
    """
    执行一轮完整对话。

    - 加载 context + prompt bundle + transcript
    - 组装 system prompt + messages
    - 调用 LLM (带 tool loop)
    - 持久化 transcript
    - 调度记忆管线

    返回 ``CompanionTurnResult``（``assistant_text`` 与可选 ``significance_perception``）。
    """
    t0 = time.perf_counter()
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    mem_cfg = memory_config or MemoryPipelineConfig()

    if heartbeat_turn and inner_tick_turn:
        raise ValueError("heartbeat_turn and inner_tick_turn cannot both be true")
    if heartbeat_turn:
        user_text = HEARTBEAT_SYNTHETIC_USER_TEXT
    elif inner_tick_turn:
        user_text = INNER_TICK_SYNTHETIC_USER_TEXT

    logger.info(
        "run_turn start path={} user_chars={} heartbeat_turn={} inner_tick_turn={} defer_memory={}",
        root,
        len(user_text),
        heartbeat_turn,
        inner_tick_turn,
        defer_memory_update,
    )
    logger.debug(
        "run_turn llm_client api_base={} model_chat={} model_tool={} dual_llm=True",
        llm_client.config.api_base,
        llm_client._resolve_model("chat"),
        llm_client._resolve_model("tool"),
    )

    # 加载 context 与 prompt bundle
    context = load_context_meta(paths.context_json, store=store)
    bundle = load_prompt_bundle(paths, store, meta=context)
    interactive_bootstrap = interactive_bootstrap_active(
        feature_enabled=(
            workspace_bootstrap_type
            == CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value
        ),
        meta=context,
    )
    rel_tr = paths.transcript.relative_to(root).as_posix()
    loaded = load_transcript_from_store(store, rel_tr)
    window_cap = transcript_llm_window_max_messages
    if window_cap is None:
        window_cap = TRANSCRIPT_WINDOW_MAX_MESSAGES
    transcript = transcript_for_llm_turn(loaded, max_messages=window_cap)

    tools_for_turn = (
        []
        if heartbeat_turn
        else (
            build_openai_repl_tools_inner_tick()
            if inner_tick_turn
            else build_companion_tools(interactive_bootstrap_active=interactive_bootstrap)
        )
    )
    use_dual_structured_chat = (
        (not heartbeat_turn) and (not inner_tick_turn) and not tools_for_turn
    )

    system_messages = build_system_messages(
        bundle,
        context,
        enable_tools=not heartbeat_turn,
        heartbeat_turn=heartbeat_turn,
        inner_tick_turn=inner_tick_turn,
        interactive_bootstrap_active=interactive_bootstrap,
        include_significance_perception_slice=use_dual_structured_chat,
    )

    prior_user_turns = sum(1 for m in loaded if m.role == "user")
    compaction_turn_idx = prior_user_turns + 1

    if transcript_compaction is not None and not heartbeat_turn and not inner_tick_turn:
        rel_compact = paths.context_compaction_state_json.relative_to(root).as_posix()
        prior_state = load_compaction_state_from_store(store, rel_compact)
        compactor = ConversationCompactor(
            transcript_compaction,
            initial_state=prior_state,
        )
        pre_user: list[dict[str, Any]] = [
            *system_messages,
            *transcript_rows_to_openai_dialogue(transcript),
        ]
        outcome = compactor.maybe_compact(messages=pre_user, turn=compaction_turn_idx)
        messages = list(outcome.messages)
        if outcome.did_compact:
            save_compaction_state_to_store(store, rel_compact, outcome.state)
            logger.info(
                "run_turn transcript_compaction did_compact=true reason={} before={} after={}",
                outcome.reason,
                outcome.approx_chars_before,
                outcome.approx_chars_after,
            )
    else:
        messages = list(system_messages)
        for m in transcript:
            messages.append({"role": m.role, "content": m.content})
    user_msg_uuid = str(uuid.uuid4())
    messages.append({"role": "user", "content": user_text})

    ts_user = utc_iso_ts()
    trace_id = str(uuid.uuid4())

    # Tool loop
    tools = tools_for_turn
    last_text = ""
    significance_meta: dict[str, Any] | None = None
    t_loop = time.perf_counter()

    inspect_token = runtime_inspect_begin_turn()
    try:
        runtime_inspect_set_runtime_config(
            build_turn_runtime_config_dict(
                llm_client=llm_client,
                mem_cfg=mem_cfg,
                context=context,
                transcript_llm_window_max_messages=window_cap,
                heartbeat_turn=heartbeat_turn,
                repository_only_workspace_text=repository_only_workspace_text,
                transcript_compaction=transcript_compaction,
                workspace_read_file_max_chars_cap=WORKSPACE_READ_FILE_MAX_CHARS_CAP,
            )
        )

        for round_idx in range(1, _MAX_TOOL_ROUNDS + 1):
            t_api = time.perf_counter()
            resolved_model = llm_client._resolve_model("tool" if tools else "chat")
            logger.debug(
                "run_turn llm_request round={} model={} tools_enabled={}",
                round_idx,
                resolved_model,
                bool(tools),
            )
            runtime_inspect_set_last_chat_completion_request(
                build_last_chat_completion_request_payload(
                    model=resolved_model,
                    messages=messages,
                    tools=tools or None,
                )
            )
            llm_scene = (
                LLM_SCENE_INNER_TICK
                if inner_tick_turn
                else (LLM_SCENE_TOOL_CALL if tools else LLM_SCENE_CHAT)
            )
            resp = llm_client.chat_completion(
                messages=messages,
                model=resolved_model,
                tools=tools or None,
                response_format=(
                    DUAL_LLM_CHAT_RESPONSE_FORMAT if use_dual_structured_chat else None
                ),
                scene=llm_scene,
            )
            approx_ctx_chars = sum(len(str(m.get("content") or "")) for m in messages)
            logger.info(
                "run_turn llm_round={} model={} chat_completions_ms={:.0f} approx_ctx_chars={} tools={} heartbeat={}",
                round_idx,
                resolved_model,
                (time.perf_counter() - t_api) * 1000.0,
                approx_ctx_chars,
                len(tools or []),
                heartbeat_turn,
            )

            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []
            messages.append(openai_assistant_message_dict(msg))

            if not tool_calls:
                raw_content = msg.content or ""
                if use_dual_structured_chat:
                    last_text, significance_meta = split_dual_llm_chat_branch_content(
                        raw_content
                    )
                else:
                    last_text = raw_content.strip()
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
                result = await repl_execute_tool_call(
                    root,
                    name,
                    args,
                    write_allowlist=WRITABLE_RELATIVE_PATHS,
                    repository_only_workspace_text=repository_only_workspace_text,
                )
                logger.info(
                    "run_turn tool_done round={} name={} result_chars={} ok={}",
                    round_idx,
                    name,
                    len(result),
                    not result.startswith("ERROR:"),
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
        else:
            raise RuntimeError(f"tool loop exceeded max_rounds={_MAX_TOOL_ROUNDS}")

        logger.info(
            "run_turn loop_done rounds={} loop_total_ms={:.0f}",
            round_idx,
            (time.perf_counter() - t_loop) * 1000.0,
        )
    finally:
        runtime_inspect_end_turn(inspect_token)

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
    if inner_tick_turn:
        user_row["inner_tick"] = True
    user_row["trace_id"] = trace_id
    store.append_jsonl_record(rel_tr, user_row)
    assistant_row: dict[str, Any] = {
        "role": "assistant",
        "content": last_text,
        "ts": utc_iso_ts(),
        "uuid": assistant_msg_uuid,
        "reply_to": user_msg_uuid,
        "source": "inner_tick" if inner_tick_turn else "chat",
        "trace_id": trace_id,
    }
    if significance_meta:
        assistant_row["significance_perception"] = significance_meta
    store.append_jsonl_record(rel_tr, assistant_row)

    # 记忆管线
    if heartbeat_turn:
        logger.debug("run_turn memory_pipeline=skipped (heartbeat_turn)")
    elif inner_tick_turn:
        logger.debug("run_turn memory_pipeline=skipped (inner_tick_turn)")
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
    return CompanionTurnResult(
        assistant_text=last_text,
        significance_perception=significance_meta,
    )
