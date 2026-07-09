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
from app.core.companion_harness.prompting.phase import Phase
from app.core.companion_harness.prompting.system_messages import (
    build_system_messages_for_inner_tick_autonomy,
    build_system_messages_for_inner_tick_monolog,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.prompting.tracks import (
    build_settled_user_turn_dual_chat_leg_system_messages,
)
from .models import ContextMeta, InnerTickActivity
from .prompt_stack import append_runtime_output_format_system_message
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
    if (
        inner_tick_turn
        and route_inner_activity != InnerTickActivity.PROACTIVE_CHAT
    ):
        match route_inner_activity:
            case InnerTickActivity.MONOLOG:
                tool_system_msgs = build_system_messages_for_inner_tick_monolog(
                    bundle,
                    context,
                    store,
                )
            case InnerTickActivity.AUTONOMY:
                tool_system_msgs = build_system_messages_for_inner_tick_autonomy(
                    bundle,
                    context,
                    store,
                )
            case _:
                raise RuntimeError(
                    "unexpected inner-tick activity for async tool path: "
                    f"{route_inner_activity.value}"
                )
    else:
        tool_system_msgs = build_system_messages_for_tool_track(
            bundle,
            context,
        )
    chat_system_msgs = build_settled_user_turn_dual_chat_leg_system_messages(
        bundle,
        context,
        phase=Phase.SETTLED,
    )
    tool_system_msgs = append_runtime_output_format_system_message(
        system_messages=tool_system_msgs,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    chat_system_msgs = append_runtime_output_format_system_message(
        system_messages=chat_system_msgs,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    tool_system_msgs = append_configured_fixed_reply_language_system_messages(
        tool_system_msgs
    )
    chat_system_msgs = append_configured_fixed_reply_language_system_messages(
        chat_system_msgs
    )
    return tool_system_msgs, chat_system_msgs
