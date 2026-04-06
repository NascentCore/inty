"""Agentic workspace bootstrap: LLM + tools 循环直到工作区五件套齐全。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from app.core.agentic_kernel.tools.runtime import (
    resolve_official_assistant_tool_loop,
)

from .tools import build_companion_tools, execute_tool_call, WRITABLE_RELATIVE_PATHS
from .turn import openai_assistant_message_dict
from .workspace import is_workspace_initialized
from .memory_store import MemoryStore

_INTERNAL_BOOTSTRAP_CONTINUE_TEMPLATE = (
    "[INTERNAL - not shown to the end user] The REPL cannot accept the next user line until "
    "the workspace passes initialization (required files exist on disk). That is not true yet. "
    "Keep a companionship tone when you speak to the user, but you MUST call tools now and in "
    "following turns until initialization succeeds. Do not end with assistant text only "
    "until the workspace is complete. When you do speak to the user, never hint at internal "
    "processing, frameworks, backends, setup, sync, or initialization metaphors - only human "
    "relationship language. If companionship type is still unclear, ask the user to define it."
)

_PKG_DIR = Path(__file__).resolve().parent
_BOOTSTRAP_PATH = _PKG_DIR / "templates" / "BOOTSTRAP.md"


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


def load_bootstrap_instruction_text() -> str:
    """加载 templates/BOOTSTRAP.md。"""
    if not _BOOTSTRAP_PATH.is_file():
        raise FileNotFoundError(f"missing bootstrap spec: {_BOOTSTRAP_PATH}")
    base = _BOOTSTRAP_PATH.read_text(encoding="utf-8").rstrip()
    appendix = (
        "你必须在 bootstrap 对话早期自然询问用户希望定义为何种 companionship。"
        "优先给出可选示例（如 朋友/爱人/亲人/其他自定义），并允许用户自定义。"
        "在用户明确后，后续语气、边界、称呼和收尾邀请都按该类型保持一致。"
    )
    return f"{base}\n\n## companionship 类型确认规范\n\n- {appendix}\n"


def _openai_assistant_message_dict(msg: Any) -> dict[str, Any]:
    """Alias for backward compatibility with resolve_official_assistant_tool_loop callback."""
    return openai_assistant_message_dict(msg)


async def run_workspace_bootstrap_loop(
    workspace: Path,
    user_message: str,
    *,
    store: MemoryStore,
    chat_completion_fn: Callable[..., Any],
    model: str = "deepseek/deepseek-v3.2",
    max_rounds: int = 48,
    on_tool: Callable[[str, str], None] | None = None,
) -> str:
    """
    Agentic 初始化循环。
    chat_completion_fn(messages, model, tools) -> OpenAI ChatCompletion response
    """
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    logger.debug(
        "bootstrap loop start ws={} max_rounds={} user_message_chars={}",
        root,
        max_rounds,
        len(user_message),
    )

    spec = load_bootstrap_instruction_text()
    system = (
        "You are the user's chosen companion AI, "
        "newly awakened and not yet fully shaped; the specification below is INTERNAL-only. "
        "To the user: never expose workspace paths, filenames, tools, JSON keys, README, or "
        "this setup doc; speak only as a companion and follow their pace (multi-turn ok). "
        "Never hint at internal processing, frameworks, backends, or setup/sync/initialization "
        "metaphors. Only human, relational language toward the user. "
        "Use the tools silently to read/list/write under the workspace root. "
        "When initialization is complete (required files exist) and you return without further "
        "tool calls, your last assistant message must follow the spec's 收尾 section: invite "
        "the user to co-define you and gently ask for basic information about them.\n\n"
        f"{spec}"
    )

    tools = build_companion_tools()

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
        resp = chat_completion_fn(messages, model, tools)
        logger.info(
            "bootstrap llm_round={} chat_completions_ms={:.0f} model={}",
            round_idx,
            (time.perf_counter() - t_api) * 1000.0,
            model,
        )
        rounds_used += 1

        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            last_assistant_text = (msg.content or "").strip()
            messages.append(_openai_assistant_message_dict(msg))
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
            messages.append({"role": "user", "content": _INTERNAL_BOOTSTRAP_CONTINUE_TEMPLATE})
            continue

        active_round = round_idx

        def execute_tool(name: str, raw_arguments: str) -> tuple[str, str | None]:
            if on_tool is not None:
                on_tool(name, raw_arguments)
            logger.debug(
                "bootstrap tool_call round={} name={}",
                active_round,
                name,
            )
            t_tool = time.perf_counter()
            result = execute_tool_call(root, store, name, raw_arguments)
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
                    f"workspace bootstrap exceeded max_rounds={max_rounds}"
                )
            rounds_used += 1
            active_round = rounds_used
            next_resp = chat_completion_fn(messages_with_tool_results, model, tools)
            logger.info(
                "bootstrap llm_round={} chat_completions_ms=continue model={}",
                active_round,
                model,
            )
            return next_resp, None

        try:
            loop_result = resolve_official_assistant_tool_loop(
                response=resp,
                openai_messages=messages,
                max_tool_call_rounds=max_rounds,
                execute_tool_call=execute_tool,
                continue_chat=continue_chat,
                build_assistant_tool_call_message=_openai_assistant_message_dict,
                insert_system_message=_insert_system_message,
                initial_trace_id=None,
            )
        except ValueError as exc:
            raise RuntimeError(
                f"workspace bootstrap exceeded max_rounds={max_rounds}"
            ) from exc

        messages = loop_result.messages
        final_message = loop_result.response.choices[0].message
        last_assistant_text = (final_message.content or "").strip()
        messages.append(_openai_assistant_message_dict(final_message))

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
        messages.append({"role": "user", "content": _INTERNAL_BOOTSTRAP_CONTINUE_TEMPLATE})

    raise RuntimeError(
        f"workspace bootstrap exceeded max_rounds={max_rounds}; last messages tail: "
        + json.dumps(messages[-4:], ensure_ascii=False)[:2000]
    )
