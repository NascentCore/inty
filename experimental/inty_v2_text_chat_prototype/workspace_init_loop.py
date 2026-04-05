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
from .orchestrator import (
    default_bootstrap_completion_celebration_text,
    is_workspace_bootstrap_complete,
)
from .workspace_init_tools import (
    build_openai_tools,
    openai_assistant_message_dict,
    tool_executor_for_root,
)

WORKSPACE_BOOTSTRAP_MAX_LLM_ROUNDS = 48

# Synthetic user turn: not shown to the human; injected in bootstrap_agent tool loop when
# BOOSTRAPED is still missing (REPL uses run_turn per user line instead).
_INTERNAL_BOOTSTRAP_CONTINUE_TEMPLATE = (
    "[INTERNAL — not shown to the end user] Non-interactive bootstrap_agent session: the "
    "workspace root must still contain an empty file named BOOSTRAPED. Template md files are "
    "on disk; revise IDENTITY/SOUL/USER/MEMORY when you have enough to write, then write "
    "BOOSTRAPED. The marker is not present yet. Do not burn turns only listing directories or "
    "re-reading all four templates solely to learn structure (canonical shapes are in system). "
    "Each assistant turn that speaks to the user must include companionship-oriented language; "
    "if key facts are still missing, ask the user before more disk reads. You should use tools "
    "when ready to persist or to read current on-disk text before editing. Never hint at "
    "internal processing, frameworks, backends, setup, sync, or initialization metaphors."
)

_PKG_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _PKG_DIR / "templates"
_BOOSTRAP_PATH = _TEMPLATES_DIR / "BOOSTRAP.md"

# 与 bootstrap.ensure_workspace_skeleton 拷贝到 workspace 的四份人格 md 一致（不含 AGENTS/BOOSTRAP/MODES）；结构以包内 templates 为准。
_BOOTSTRAP_TEMPLATE_MD: tuple[str, ...] = (
    "IDENTITY.md",
    "SOUL.md",
    "USER.md",
    "MEMORY.md",
)


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


def _log_bootstrap_llm_round(round_idx: int, t_api_start: float, model: str) -> None:
    logger.info(
        "bootstrap llm_round={} chat_completions_ms={:.0f} model={}",
        round_idx,
        (time.perf_counter() - t_api_start) * 1000.0,
        model,
    )


def _maybe_emit_bootstrap_trace(
    llm_trace: bool,
    *,
    round_idx: int,
    model: str,
    messages: list[dict[str, Any]],
    response: Any,
    ws_label: str,
) -> None:
    if not llm_trace:
        return
    emit_trace(
        "bootstrap",
        round_idx=round_idx,
        model=model,
        messages=summarize_messages(
            messages,
            ws_label=ws_label,
            trace_day=local_date_str(),
        ),
        response=summarize_completion_response(response),
    )


def repl_bootstrap_continue_user_message() -> str:
    """REPL 在缺 BOOSTRAPED 时注入的 synthetic user，与 bootstrap_agent 内部续跑文案一致。"""
    return _INTERNAL_BOOTSTRAP_CONTINUE_TEMPLATE


def _bootstrap_spec_base_text(workspace: Path | None) -> str:
    if workspace is not None:
        w = workspace.resolve() / "BOOSTRAP.md"
        if w.is_file():
            return w.read_text(encoding="utf-8").rstrip()
    if not _BOOSTRAP_PATH.is_file():
        raise FileNotFoundError(f"missing bootstrap spec: {_BOOSTRAP_PATH}")
    return _BOOSTRAP_PATH.read_text(encoding="utf-8").rstrip()


def load_bootstrap_instruction_text(workspace: Path | None = None) -> str:
    """优先读 workspace/BOOSTRAP.md（init-workspace 已拷贝），否则读包内 templates/。"""
    return _bootstrap_spec_base_text(workspace)


def _bootstrap_package_template_canon_block() -> str:
    lines = [
        "## canonical_workspace_md_shapes",
        "The workspace root already has copies of these template files (same filenames). "
        "When you use workspace_write_file, you MUST preserve the exact markdown heading "
        "hierarchy, section titles in Chinese, and bullet layout shown below; only replace "
        "placeholder or stub lines with text grounded in what the user has agreed (for "
        "unknown user facts you may keep 待了解-style phrasing). You do not need to call "
        "workspace_read_file on them solely to learn structure; optional reads are only to "
        "see the current on-disk text before editing.",
    ]
    for name in _BOOTSTRAP_TEMPLATE_MD:
        path = _TEMPLATES_DIR / name
        if not path.is_file():
            raise FileNotFoundError(f"missing package workspace template: {path}")
        body = path.read_text(encoding="utf-8").rstrip()
        lines.append(f"### {name}")
        lines.append("```markdown")
        lines.append(body)
        lines.append("```")
    return "\n\n".join(lines)


def build_bootstrap_system_prompt(workspace: Path) -> str:
    """模板 bootstrap 的 system 正文（BOOSTRAP.md + canonical 包内 md 形状）；与 run_turn / bootstrap_agent 共用。"""
    spec = load_bootstrap_instruction_text(workspace)
    canon = _bootstrap_package_template_canon_block()
    return f"{spec}\n\n{canon}"


def run_workspace_bootstrap_loop(
    workspace: Path,
    user_message: str,
    *,
    model: str | None = None,
    max_rounds: int = WORKSPACE_BOOTSTRAP_MAX_LLM_ROUNDS,
    on_tool: Callable[[str, str], None] | None = None,
    llm_trace: bool = False,
) -> str:
    """
    在 workspace 上运行伴侣向的 agentic 模板填充循环（对内落盘，对用户自然语言）。
    直到根目录存在 BOOSTRAPED 才在「无 tool_calls」时返回；骨架文件应由 ensure_workspace_skeleton 预置。
    """
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    logger.debug(
        "bootstrap loop start ws={} max_rounds={} user_message_chars={}",
        root,
        max_rounds,
        len(user_message),
    )

    system = build_bootstrap_system_prompt(root)

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
        _log_bootstrap_llm_round(round_idx, t_api, m)
        rounds_used += 1
        _maybe_emit_bootstrap_trace(
            llm_trace,
            round_idx=round_idx,
            model=m,
            messages=messages,
            response=resp,
            ws_label=root.name,
        )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            last_assistant_text = (msg.content or "").strip()
            messages.append(openai_assistant_message_dict(msg))
            if is_workspace_bootstrap_complete(root):
                logger.info(
                    "bootstrap done rounds={} total_ms={:.0f} ws={}",
                    round_idx,
                    (time.perf_counter() - t_boot) * 1000.0,
                    root.name,
                )
                if not last_assistant_text.strip():
                    last_assistant_text = (
                        default_bootstrap_completion_celebration_text()
                    )
                return last_assistant_text
            logger.debug(
                "bootstrap no_tool_calls but BOOSTRAPED missing round={} "
                "injecting_internal_continue",
                round_idx,
            )
            messages.append(
                {"role": "user", "content": repl_bootstrap_continue_user_message()}
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
            _log_bootstrap_llm_round(active_round, t_api_inner, m)
            _maybe_emit_bootstrap_trace(
                llm_trace,
                round_idx=active_round,
                model=m,
                messages=messages_with_tool_results,
                response=next_resp,
                ws_label=root.name,
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
        if is_workspace_bootstrap_complete(root):
            logger.info(
                "bootstrap done rounds={} total_ms={:.0f} ws={}",
                rounds_used,
                (time.perf_counter() - t_boot) * 1000.0,
                root.name,
            )
            if not last_assistant_text.strip():
                last_assistant_text = default_bootstrap_completion_celebration_text()
            return last_assistant_text
        logger.debug(
            "bootstrap tool_loop_finished but BOOSTRAPED missing rounds_used={} "
            "injecting_internal_continue",
            rounds_used,
        )
        messages.append(
            {"role": "user", "content": repl_bootstrap_continue_user_message()}
        )

    raise RuntimeError(
        f"workspace bootstrap exceeded max_rounds={max_rounds}; last messages tail: "
        + json.dumps(messages[-4:], ensure_ascii=False)[:2000]
    )
