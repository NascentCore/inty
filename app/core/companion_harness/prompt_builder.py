"""Typed prompt assembly for queue-served user chat with a single language model.

Builds structured system, transcript, and tail-user sections for settled user
turns that run through the agentic loop and in-turn tool calling. Legacy prompt
builders for non-queue paths stay unchanged until follow-up migration work.

TODO(!3398): First step toward prompt-stack migration; legacy callers remain
unchanged until follow-up issues land.
https://github.com/NascentCore/inty/issues/3398

TODO(!3453): Named-slot system slices should use declarative templates instead
of imperative assembly.
https://github.com/NascentCore/inty/issues/3453
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.core.companion_harness.companion.models import (
    ChatMessage,
    ContextMeta,
    load_context_meta,
    load_prompt_bundle,
)
from app.core.companion_harness.companion.prompt_stack import (
    append_runtime_output_format_system_message,
    replace_leading_system_messages_inplace,
    weixin_clawbot_contact_alias_system_message,
)
from app.core.companion_harness.prompting.tracks import (
    build_settled_user_turn_single_llm_system_messages,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_pipeline import (
    _companion_tail_user_body_for_llm,
    _companion_user_time_context_system_for_llm,
)
from app.core.companion_harness.companion.transcript_ai_private import (
    AiPrivateThought,
)
from app.core.companion_harness.companion.utc import (
    transcript_message_content_for_llm,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.transcript_compaction import (
    transcript_rows_to_openai_dialogue,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


class PromptMessageRole(StrEnum):
    """Speaker role for one line in a typed prompt plan."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class PromptMessage:
    """One line in a prompt plan before conversion to provider wire format."""

    role: PromptMessageRole
    content: str


@dataclass(frozen=True)
class PromptPlan:
    """Abstract composition of prompt slices bolted together through abstract data types.

    Holds ordered messages plus tool definitions and optional tool-choice hint
    for the first model call in an in-turn sync tool loop.

    TODO: SystemMessage, UserMessage, AssistantMessage, ToolMessage, etc.
    These should be defined as abstract data types, not concrete classes.

    TODO: Should be ordered list of messages, and allow tools to update the content and order.
    The meta-description of a PromptPlan object can be output as description for LLM
    to reorder and update the messages.
    """

    messages: tuple[
        PromptMessage, ...
    ]  # TODO: This should be abstract data type.
    # TODO(!3398): Type tool schemas instead of OpenAI dict payloads.
    tools: tuple[dict[str, Any], ...]
    tool_choice: str | None  # TODO: This should be enum.


def openai_dialogue_dicts_to_prompt_messages(
    dialogue: list[dict[str, Any]],
) -> tuple[PromptMessage, ...]:
    """Convert legacy OpenAI dialogue dicts into typed ``PromptMessage`` rows."""
    out: list[PromptMessage] = []
    for row in dialogue:
        role_raw = row.get("role")
        assert role_raw in {r.value for r in PromptMessageRole}
        out.append(
            PromptMessage(
                role=PromptMessageRole(str(role_raw)),
                content=str(row.get("content") or ""),
            )
        )
    return tuple(out)


def prompt_messages_to_openai_dicts(
    messages: tuple[PromptMessage, ...],
) -> list[dict[str, Any]]:
    """Convert typed messages to OpenAI wire shape (``LLMClient`` boundary only)."""
    return [
        {"role": message.role.value, "content": message.content}
        for message in messages
    ]


def _system_dicts_to_prompt_messages(
    system_dicts: list[dict[str, Any]],
) -> tuple[PromptMessage, ...]:
    return openai_dialogue_dicts_to_prompt_messages(system_dicts)


@dataclass(frozen=True)
class PromptBuilder:
    """Assembles prompt plans for queue-served settled user chat.

    Given memory bundle, context metadata, and runtime channel signals, produces
    a prompt plan with system doctrine, transcript window, optional private
    thought splice, time context, and the current user utterance.
    """

    bundle: PromptBundle
    context: ContextMeta
    runtime_context: TurnRuntimeContext

    def build_user_chat_prompt(
        self,
        *,
        transcript_window: list[ChatMessage],
        user_text: str,
        tail_user_ts: datetime,
        tools: tuple[dict[str, Any], ...],
        implicit_sign_on_turn: bool,
        tail_splice_thoughts: tuple[AiPrivateThought, ...],
    ) -> PromptPlan:
        """Assemble initial single-LLM user-chat prompt with in-turn tools enabled."""
        assert user_text.strip() != ""
        system_dicts = build_settled_user_turn_single_llm_system_messages(
            self.bundle,
            self.context,
        )
        system_dicts = append_runtime_output_format_system_message(
            system_messages=system_dicts,
            bundle=self.bundle,
            runtime_context=self.runtime_context,
        )
        if (
            self.runtime_context.channel
            == CompanionRuntimeChannel.WECHAT_WEIXIN
        ):
            system_dicts.append(weixin_clawbot_contact_alias_system_message())
        messages: list[PromptMessage] = list(
            _system_dicts_to_prompt_messages(system_dicts)
        )
        messages.extend(
            openai_dialogue_dicts_to_prompt_messages(
                transcript_rows_to_openai_dialogue(transcript_window)
            )
        )
        for thought in tail_splice_thoughts:
            messages.append(
                PromptMessage(
                    role=PromptMessageRole.ASSISTANT,
                    content=transcript_message_content_for_llm(
                        content=thought.text,
                        ts=thought.ts,
                    ),
                )
            )
        time_ctx_system = _companion_user_time_context_system_for_llm(
            implicit_signal_bundle=self.runtime_context.implicit_signal_bundle,
        )
        if time_ctx_system is not None:
            messages.append(
                PromptMessage(
                    role=PromptMessageRole.SYSTEM,
                    content=time_ctx_system,
                )
            )
        tail_user = _companion_tail_user_body_for_llm(
            user_text=user_text,
            implicit_sign_on_turn=implicit_sign_on_turn,
            tail_user_ts=tail_user_ts,
        )
        messages.append(
            PromptMessage(role=PromptMessageRole.USER, content=tail_user)
        )
        return PromptPlan(
            messages=tuple(messages),
            tools=tools,
            tool_choice=None,
        )


def refresh_single_llm_user_chat_prompt_prefix(
    *,
    store: MemoryStore,
    messages: list[dict[str, Any]],
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Replace leading system messages after a tool round on single-LLM ``USER_CHAT``.

    Does not fall back to tool-background compact prompt (``build_system_messages_for_tool_track``).
    """
    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    refreshed = build_settled_user_turn_single_llm_system_messages(
        bundle, context
    )
    refreshed = append_runtime_output_format_system_message(
        system_messages=refreshed,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    if runtime_context.channel == CompanionRuntimeChannel.WECHAT_WEIXIN:
        refreshed.append(weixin_clawbot_contact_alias_system_message())
    replace_leading_system_messages_inplace(messages, refreshed)
    return messages
