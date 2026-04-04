"""Agentic 工作区初始化：chat.completions + tools，循环直到模型不再调用工具。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from app.core.agentic_kernel.tools.runtime import (
    resolve_official_assistant_tool_loop,
)

from .client import create_chat_completion, default_model, get_client_dual_llm_tool
from .llm_trace import emit_trace, summarize_completion_response, summarize_messages
from .utc import local_date_str
from .orchestrator import is_workspace_initialized
from .workspace_init_tools import (
    build_openai_tools,
    openai_assistant_message_dict,
    tool_executor_for_root,
)

# Synthetic user turn: not shown to the human; tells the model the REPL is blocked until
# required files exist (see is_workspace_initialized).
_INTERNAL_BOOTSTRAP_CONTINUE_TEMPLATE = (
    "[INTERNAL — not shown to the end user] The REPL cannot accept the next user line until "
    "the workspace passes initialization (required files exist on disk). That is not true yet. "
    "Keep {companion_type}-relationship tone when you speak to the user, but you MUST call tools now and in "
    "following turns until initialization succeeds. Do not end with assistant text only "
    "until the workspace is complete. When you do speak to the user, never hint at internal "
    "processing, frameworks, backends, setup, sync, or initialization metaphors—only human "
    "relationship language."
)

_PKG_DIR = Path(__file__).resolve().parent
_BOOSTRAP_PATH = _PKG_DIR / "_ws2" / "BOOSTRAP.md"
_DEFAULT_COMPANION_TYPE = "伴侣"
_SUPPORTED_COMPANION_TYPES: tuple[str, ...] = (
    "伴侣",
    "朋友",
    "爱人",
    "亲人",
)
_COMPANION_TYPE_ALIASES: dict[str, str] = {
    "partner": "伴侣",
    "friend": "朋友",
    "lover": "爱人",
    "family": "亲人",
}
_COMPANION_TYPE_APPENDIX: dict[str, str] = {
    "伴侣": (
        "你是伴侣型陪伴，侧重亲密感、信任感与边界协商。"
        "收尾邀请里优先覆盖彼此称呼、情绪支持方式与相处边界。"
    ),
    "朋友": (
        "你是朋友型陪伴，语气平等、轻松、不过度黏连。"
        "收尾邀请里优先覆盖彼此称呼、聊天频率偏好与可聊/不想聊的话题。"
    ),
    "爱人": (
        "你是爱人型陪伴，语气温柔真诚、允许更高亲密表达。"
        "收尾邀请里优先覆盖亲密称呼、安全感需求与冲突时希望的沟通方式。"
    ),
    "亲人": (
        "你是亲人型陪伴，语气稳重、可靠、支持感明确。"
        "收尾邀请里优先覆盖家庭式称呼、生活关心方式与彼此边界。"
    ),
}


def _insert_system_message(
    openai_messages: list[dict[str, Any]],
    system_message_content: str,
) -> None:
    insertion_index = 0
    while (
        insertion_index < len(openai_messages)
        and openai_messages[insertion_index].get("role") == "system"
    ):
        insertion_index += 1
    openai_messages.insert(
        insertion_index, {"role": "system", "content": system_message_content}
    )


def normalize_companion_type(companion_type: str | None) -> str:
    if companion_type is None:
        return _DEFAULT_COMPANION_TYPE
    raw = companion_type.strip()
    if not raw:
        return _DEFAULT_COMPANION_TYPE
    if raw in _SUPPORTED_COMPANION_TYPES:
        return raw
    lowered = raw.lower()
    mapped = _COMPANION_TYPE_ALIASES.get(lowered)
    if mapped is not None:
        return mapped
    return raw


def _internal_bootstrap_continue(companion_type: str) -> str:
    return _INTERNAL_BOOTSTRAP_CONTINUE_TEMPLATE.format(companion_type=companion_type)


def load_bootstrap_instruction_text(
    companion_type: str | None = _DEFAULT_COMPANION_TYPE,
) -> str:
    """加载 _ws2/BOOSTRAP.md（与 README 中「Agentic 初始化」流程一致）。"""
    if not _BOOSTRAP_PATH.is_file():
        raise FileNotFoundError(f"missing bootstrap spec: {_BOOSTRAP_PATH}")
    normalized_type = normalize_companion_type(companion_type)
    base = _BOOSTRAP_PATH.read_text(encoding="utf-8").rstrip()
    appendix = _COMPANION_TYPE_APPENDIX.get(
        normalized_type,
        (
            "你是自定义关系类型陪伴，先按用户给定关系语义建立语气与边界。"
            "收尾邀请里优先确认彼此称呼、互动边界与陪伴期待。"
        ),
    )
    return (
        f"{base}\n\n## 陪伴类型补充规范\n\n"
        f"- 当前陪伴类型: {normalized_type}\n"
        f"- {appendix}\n"
    )


def run_workspace_bootstrap_loop(
    workspace: Path,
    user_message: str,
    *,
    companion_type: str = _DEFAULT_COMPANION_TYPE,
    model: str | None = None,
    max_rounds: int = 48,
    on_tool: Callable[[str, str], None] | None = None,
    llm_trace: bool = False,
) -> str:
    """
    在 workspace 上运行伴侣向的 agentic 初始化循环（对内落盘，对用户自然语言）。
    直到 is_workspace_initialized 才在「无 tool_calls」时返回，避免只聊天不落盘导致 REPL 下一步崩溃。
    """
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    logger.debug(
        "bootstrap loop start ws={} max_rounds={} user_message_chars={}",
        root,
        max_rounds,
        len(user_message),
    )

    normalized_type = normalize_companion_type(companion_type)
    spec = load_bootstrap_instruction_text(normalized_type)
    system = (
        "You are the user's chosen companion AI in the INTY v2 local text-chat prototype, "
        "newly awakened and not yet fully shaped; the specification below is INTERNAL-only. "
        f"Companion type for this session is: {normalized_type}. "
        "To the user: never expose workspace paths, filenames, tools, JSON keys, README, or "
        "this setup doc; speak only as a companion and follow their pace (multi-turn ok). "
        "Never hint at internal processing, frameworks, backends, or setup/sync/initialization "
        "metaphors (e.g. do not say your internal framework is ready). Only human, relational "
        "language toward the user. "
        "Use the tools silently to read/list/write under the workspace root. "
        "Do not ask the user to run `python ... init-workspace` instead of using tools. "
        "When initialization is complete (required files exist) and you return without further "
        "tool calls, your last assistant message must follow the spec's «收尾» section: invite "
        "the user to co-define you and gently ask for basic information about them—companion "
        "language only, not a form.\n\n"
        f"{spec}"
    )

    client = get_client_dual_llm_tool()
    m = model or default_model()
    tools = build_openai_tools()
    run_tool = tool_executor_for_root(root)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]

    last_assistant_text = ""
    t_boot = time.perf_counter()
    rounds_used = 0
    while rounds_used < max_rounds:
        round_idx = rounds_used + 1
        t_api = time.perf_counter()
        resp = create_chat_completion(
            client,
            model=m,
            messages_payload=messages,
            tools=tools,
        )
        logger.info(
            "bootstrap llm_round={} chat_completions_ms={:.0f} model={}",
            round_idx,
            (time.perf_counter() - t_api) * 1000.0,
            m,
        )
        rounds_used += 1
        if llm_trace:
            emit_trace(
                "bootstrap",
                round_idx=round_idx,
                model=m,
                messages=summarize_messages(
                    messages,
                    ws_label=root.name,
                    trace_day=local_date_str(),
                ),
                response=summarize_completion_response(resp),
            )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            last_assistant_text = (msg.content or "").strip()
            messages.append(openai_assistant_message_dict(msg))
            if is_workspace_initialized(root):
                logger.info(
                    "bootstrap done rounds={} total_ms={:.0f} ws={}",
                    round_idx,
                    (time.perf_counter() - t_boot) * 1000.0,
                    root.name,
                )
                return last_assistant_text
            logger.debug(
                "bootstrap no_tool_calls but workspace not initialized round={} "
                "injecting_internal_continue",
                round_idx,
            )
            messages.append(
                {
                    "role": "user",
                    "content": _internal_bootstrap_continue(normalized_type),
                }
            )
            continue

        active_round = round_idx

        def execute_tool_call(name: str, raw_arguments: str) -> tuple[str, str | None]:
            if on_tool is not None:
                on_tool(name, raw_arguments)
            arg_preview = (raw_arguments or "").replace("\n", " ")
            if len(arg_preview) > 240:
                arg_preview = arg_preview[:239] + "…"
            logger.debug(
                "bootstrap tool_call round={} name={} args_preview={}",
                active_round,
                name,
                arg_preview,
            )
            t_tool = time.perf_counter()
            result = run_tool(name, raw_arguments)
            logger.info(
                "bootstrap tool_done round={} name={} execute_ms={:.0f} result_chars={}",
                active_round,
                name,
                (time.perf_counter() - t_tool) * 1000.0,
                len(result),
            )
            return result, None

        def continue_chat(
            messages_with_tool_results: list[dict[str, Any]],
        ) -> tuple[Any, str | None]:
            nonlocal rounds_used, active_round
            if rounds_used >= max_rounds:
                raise ValueError(
                    f"workspace bootstrap exceeded max_rounds={max_rounds} "
                    "while resolving tool calls"
                )
            rounds_used += 1
            active_round = rounds_used
            t_api_inner = time.perf_counter()
            next_resp = create_chat_completion(
                client,
                model=m,
                messages_payload=messages_with_tool_results,
                tools=tools,
            )
            logger.info(
                "bootstrap llm_round={} chat_completions_ms={:.0f} model={}",
                active_round,
                (time.perf_counter() - t_api_inner) * 1000.0,
                m,
            )
            if llm_trace:
                emit_trace(
                    "bootstrap",
                    round_idx=active_round,
                    model=m,
                    messages=summarize_messages(
                        messages_with_tool_results,
                        ws_label=root.name,
                        trace_day=local_date_str(),
                    ),
                    response=summarize_completion_response(next_resp),
                )
            return next_resp, None

        try:
            loop_result = resolve_official_assistant_tool_loop(
                response=resp,
                openai_messages=messages,
                max_tool_call_rounds=max_rounds,
                execute_tool_call=execute_tool_call,
                continue_chat=continue_chat,
                build_assistant_tool_call_message=openai_assistant_message_dict,
                insert_system_message=_insert_system_message,
                initial_trace_id=None,
            )
        except ValueError as exc:
            raise RuntimeError(
                f"workspace bootstrap exceeded max_rounds={max_rounds}; "
                "failed during tool loop"
            ) from exc

        messages = loop_result.messages
        final_message = loop_result.response.choices[0].message
        last_assistant_text = (final_message.content or "").strip()
        messages.append(openai_assistant_message_dict(final_message))
        if is_workspace_initialized(root):
            logger.info(
                "bootstrap done rounds={} total_ms={:.0f} ws={}",
                rounds_used,
                (time.perf_counter() - t_boot) * 1000.0,
                root.name,
            )
            return last_assistant_text
        logger.debug(
            "bootstrap tool_loop_finished but workspace not initialized rounds_used={} "
            "injecting_internal_continue",
            rounds_used,
        )
        messages.append(
            {
                "role": "user",
                "content": _internal_bootstrap_continue(normalized_type),
            }
        )

    raise RuntimeError(
        f"workspace bootstrap exceeded max_rounds={max_rounds}; last messages tail: "
        + json.dumps(messages[-4:], ensure_ascii=False)[:2000]
    )
