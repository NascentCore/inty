"""Agentic 工作区初始化：chat.completions + tools，循环直到模型不再调用工具。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from .client import default_model, get_client
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
_INTERNAL_BOOTSTRAP_CONTINUE = (
    "[INTERNAL — not shown to the end user] The REPL cannot accept the next user line until "
    "the workspace passes initialization (required files exist on disk). That is not true yet. "
    "Keep companion tone when you speak to the user, but you MUST call tools now and in "
    "following turns until initialization succeeds. Do not end with assistant text only "
    "until the workspace is complete. When you do speak to the user, never hint at internal "
    "processing, frameworks, backends, setup, sync, or initialization metaphors—only human "
    "relationship language."
)

_PKG_DIR = Path(__file__).resolve().parent
_BOOSTRAP_PATH = _PKG_DIR / "_ws2" / "BOOSTRAP.md"


def load_bootstrap_instruction_text() -> str:
    """加载 _ws2/BOOSTRAP.md（与 README 中「Agentic 初始化」流程一致）。"""
    if not _BOOSTRAP_PATH.is_file():
        raise FileNotFoundError(f"missing bootstrap spec: {_BOOSTRAP_PATH}")
    return _BOOSTRAP_PATH.read_text(encoding="utf-8")


def run_workspace_bootstrap_loop(
    workspace: Path,
    user_message: str,
    *,
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

    spec = load_bootstrap_instruction_text()
    system = (
        "You are the user's chosen companion AI in the INTY v2 local text-chat prototype, "
        "newly awakened and not yet fully shaped; the specification below is INTERNAL-only. "
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

    client = get_client()
    m = model or default_model()
    tools = build_openai_tools()
    run_tool = tool_executor_for_root(root)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]

    last_assistant_text = ""
    t_boot = time.perf_counter()
    for round_idx in range(1, max_rounds + 1):
        t_api = time.perf_counter()
        resp = client.chat.completions.create(
            model=m,
            messages=messages,
            tools=tools,
            # parallel_tool_calls=False,
            parallel_tool_calls=True,
        )
        logger.info(
            "bootstrap llm_round={} chat_completions_ms={:.0f} model={}",
            round_idx,
            (time.perf_counter() - t_api) * 1000.0,
            m,
        )
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
            messages.append({"role": "user", "content": _INTERNAL_BOOTSTRAP_CONTINUE})
            continue

        messages.append(openai_assistant_message_dict(msg))
        for tc in tool_calls:
            fn = tc.function
            name = fn.name
            args = fn.arguments if fn.arguments is not None else ""
            if on_tool is not None:
                on_tool(name, args)
            arg_preview = (args or "").replace("\n", " ")
            if len(arg_preview) > 240:
                arg_preview = arg_preview[:239] + "…"
            logger.debug(
                "bootstrap tool_call round={} name={} args_preview={}",
                round_idx,
                name,
                arg_preview,
            )
            t_tool = time.perf_counter()
            result = run_tool(name, args)
            logger.info(
                "bootstrap tool_done round={} name={} execute_ms={:.0f} result_chars={}",
                round_idx,
                name,
                (time.perf_counter() - t_tool) * 1000.0,
                len(result),
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    raise RuntimeError(
        f"workspace bootstrap exceeded max_rounds={max_rounds}; last messages tail: "
        + json.dumps(messages[-4:], ensure_ascii=False)[:2000]
    )
