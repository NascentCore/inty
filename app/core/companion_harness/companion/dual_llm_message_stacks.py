"""Dual-LLM chat vs tool message stacks for settled ``USER_CHAT`` dual mechanism.

Builds separate system-message prefixes for the foreground chat leg and the tool_background leg,
then splices them onto the shared transcript tail via ``replace_leading_system_messages_multi``.
"""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.loop.runtime_system_clauses import (
    append_configured_fixed_reply_language_system_messages,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.tracks import (
    build_settled_user_turn_dual_chat_leg_system_messages,
)
from .models import ContextMeta, InnerTickActivity
from .inner_tick_kind import InnerTickKind, inner_tick_spec
from .prompt_stack import append_runtime_output_format_system_message
from app.core.companion_harness.prompting.system_messages import (
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)


def replace_leading_system_messages_multi(
    messages: list[dict[str, Any]],
    system_messages: list[dict[str, Any]],
    *,
    stack_depth: int,
) -> list[dict[str, Any]]:
    """Replace the first ``stack_depth`` system messages (MemoryStore stack) with ``system_messages``.

    In dual-LLM invocation turn, 把消息列表开头那几段「人设/记忆」系统提示换成 chat 或 tool 各自需要的版本，同时完整保留后面的聊天记录、时间上下文和当前用户输入。
    """
    return [*system_messages, *messages[stack_depth:]]


def _dual_llm_tool_leg_base_system_messages(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    inner_tick_turn: bool,
    route_inner_activity: InnerTickActivity,
) -> list[dict[str, Any]]:
    """Tool-path system stack before runtime output-format and language clauses."""
    if (
        inner_tick_turn
        and route_inner_activity != InnerTickActivity.PROACTIVE_CHAT
    ):
        match route_inner_activity:
            case InnerTickActivity.MONOLOG:
                spec = inner_tick_spec(InnerTickKind.MONOLOG)
            case InnerTickActivity.AUTONOMY:
                spec = inner_tick_spec(InnerTickKind.AUTONOMY)
            case _:
                raise RuntimeError(
                    "unexpected inner-tick activity for async tool path: "
                    f"{route_inner_activity.value}"
                )
        builder = spec.async_tool_prompt_builder
        assert builder is not None
        return builder(bundle, context, store)
    return build_system_messages_for_tool_track(bundle, context)


def _dual_llm_leg_system_messages_with_runtime_clauses(
    *,
    base_system_messages: list[dict[str, Any]],
    bundle: PromptBundle,
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    with_output = append_runtime_output_format_system_message(
        system_messages=base_system_messages,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    return append_configured_fixed_reply_language_system_messages(with_output)


def dual_llm_system_message_variants(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    inner_tick_turn: bool,
    route_inner_activity: InnerTickActivity,
    runtime_context: TurnRuntimeContext,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Foreground ``chat_track`` vs tool-path stacks for dual-LLM ``USER_CHAT``.

    Implicit sign-on rounds never reach this helper (greeting track uses its own stack).
    """
    tool_base = _dual_llm_tool_leg_base_system_messages(
        store=store,
        bundle=bundle,
        context=context,
        inner_tick_turn=inner_tick_turn,
        route_inner_activity=route_inner_activity,
    )
    chat_base = build_settled_user_turn_dual_chat_leg_system_messages(
        bundle,
        context,
    )
    tool_system_msgs = _dual_llm_leg_system_messages_with_runtime_clauses(
        base_system_messages=tool_base,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    chat_system_msgs = _dual_llm_leg_system_messages_with_runtime_clauses(
        base_system_messages=chat_base,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    return tool_system_msgs, chat_system_msgs
