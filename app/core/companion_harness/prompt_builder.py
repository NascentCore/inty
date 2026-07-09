"""Typed prompt assembly for queue-served single-LLM user chat (settled + bootstrap).

Builds ``PromptPlan`` objects for AgenticLoop single-LLM execution: system slices,
transcript window, optional private-thought splice, time context, and tail user.
Bootstrap, settled user chat, and chat-only tracks (greeting, proactive, scheduled)
compose system prefixes through this module. Monolog, autonomy, and dual-LLM
paths still use legacy ``prompt_stack`` / ``build_system_messages`` entrypoints (#3453).

``PromptPlan`` is the **output** of the memory projection stage (target pipeline:
MemoryStore → retrieval → ``prompting.projection`` → PromptPlan). **Today** assembly
is imperative and skips an explicit selection stage (#3521).

TODO(#3453): Named-slot system slices should use declarative templates instead
of imperative assembly.
https://github.com/NascentCore/inty/issues/3453

TODO(#3629): PromptPlan end-to-end; OpenAI wire conversion only in AsyncLlmClient.
https://github.com/NascentCore/inty/issues/3629
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.companion_harness.companion.models import (
    ChatMessage,
    CompanionTurnTrack,
    ContextMeta,
    load_context_meta,
    load_prompt_bundle,
)
from app.core.companion_harness.companion.prompt_stack import (
    append_runtime_output_format_system_message,
    replace_leading_system_messages_inplace,
    weixin_clawbot_contact_alias_system_message,
)
from app.core.companion_harness.companion.dual_llm_message_stacks import (
    replace_leading_system_messages_multi,
)
from app.core.companion_harness.prompting.compose_context import (
    build_turn_compose_context,
    empty_memory_store_for_compose,
)
from app.core.companion_harness.prompting.contextual import assemble_contextual_slices
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.phase import Phase, resolve_compose_phase
from app.core.companion_harness.prompting.system_messages import (
    _assemble_proactive_chat_life_currents_hint_prompt,
    _auxiliary_system_messages,
    _capability_system_messages,
    _doctrine_system_messages,
    _output_contract_text,
    _output_system_messages,
    _persona_system_messages,
    _proactive_chat_structured_output_contract_text,
    _scheduled_reminder_structured_output_contract_text,
    _system_message,
    append_profile_collection_system_messages,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.prompting.tracks import (
    _capability_bootstrap_single_llm_system_messages,
    _capability_settled_single_llm_system_messages,
    _output_bootstrap_single_llm_system_messages,
    _output_settled_single_llm_system_messages,
    _persona_bootstrap_user_turn_system_messages,
    _persona_settled_user_turn_system_messages,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_pipeline import (
    _companion_user_time_context_system_for_llm,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
    tail_user_message_contents_for_llm,
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
from app.core.companion_harness.loop.runtime_system_clauses import (
    append_configured_fixed_reply_language_system_messages,
    apply_debug_github_disclosure_runtime_clause,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_bootstrap_track_tools,
    build_openai_repl_tools,
)


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
    """Abstract composition of prompt slices — target output of memory projection.

    Holds ordered messages plus tool definitions and optional tool-choice hint
    for the first model call in an in-turn sync tool loop.

    ``messages`` stay typed until callers convert to OpenAI wire dicts via
    ``prompt_messages_to_openai_dicts``; the target boundary is ``AsyncLlmClient``
    (#3460).

    TODO(#3453): SystemMessage, UserMessage, AssistantMessage, ToolMessage, etc.
    These should be defined as abstract data types, not concrete classes.

    TODO(#3453): Should be ordered list of messages, and allow tools to update the content and order.
    The meta-description of a PromptPlan object can be output as description for LLM
    to reorder and update the messages.

    TODO(prompt-plan-e2e): Typed end-to-end carrier; wire conversion only in AsyncLlmClient. — #3629
    """

    messages: tuple[
        PromptMessage, ...
    ]  # TODO(#3453): This should be abstract data type.
    # TODO(#3398): Type tool schemas instead of OpenAI dict payloads.
    tools: tuple[dict[str, Any], ...]
    tool_choice: str | None  # TODO(#3453): This should be enum.


def openai_dialogue_dicts_to_prompt_messages(
    dialogue: list[dict[str, Any]],
) -> tuple[PromptMessage, ...]:
    """Ingest legacy OpenAI dialogue dicts into typed ``PromptMessage`` rows.

    Used while assembling ``PromptPlan`` from paths that still emit
    ``list[dict[str, Any]]`` (system-prefix replacement, transcript projection).
    Prefer constructing ``PromptMessage`` directly in new assembly code (#3453).
    """
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
    """Map typed ``PromptMessage`` rows to OpenAI chat ``messages`` wire dicts.

    Each output row is ``{"role": <role>, "content": <content>}`` — the shape
    ``AsyncLlmClient.chat_completion`` expects today.

    Conversion currently happens at call sites before ``AsyncLlmClient``:
    ``agentic_loop._run_prompt_plan_tool_loop`` (single-LLM in-turn sync),
    ``turn.py`` dual-LLM tool-leg paths, and unit tests. The **target**
    boundary is inside ``AsyncLlmClient`` so harness code keeps ``PromptPlan``
    typed end-to-end (#3460 AgenticLoop consolidation; #3398 dual vs single-LLM).
    """
    return [
        {"role": message.role.value, "content": message.content}
        for message in messages
    ]


def _system_dicts_to_prompt_messages(
    system_dicts: list[dict[str, Any]],
) -> tuple[PromptMessage, ...]:
    return openai_dialogue_dicts_to_prompt_messages(system_dicts)


def _append_runtime_channel_system_extras(
    *,
    system_dicts: list[dict[str, Any]],
    bundle: PromptBundle,
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Append peripheral gateway modality slices (output format, Weixin alias) for the active channel.

    Runtime organization: peripheral (track-attached).
    """
    out = append_runtime_output_format_system_message(
        system_messages=system_dicts,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    if runtime_context.channel == ChannelKind.WECHAT_WEIXIN:
        out.append(weixin_clawbot_contact_alias_system_message())
    return out


@dataclass(frozen=True)
class PromptBuilder:
    """Assembles ``PromptPlan`` for queue-served single-LLM user chat (settled + bootstrap).

    Given memory bundle, context metadata, and runtime channel signals, produces
    a prompt plan with system doctrine, transcript window, optional private
    thought splice, time context, and the current user utterance.
    """

    bundle: PromptBundle
    context: ContextMeta
    runtime_context: TurnRuntimeContext

    def _turn_compose_context(
        self,
        *,
        track: CompanionTurnTrack,
        store: MemoryStore,
        ai_private_text: str,
        proactive_life_currents_block: str | None,
    ) -> object:
        life_currents = proactive_life_currents_block
        if (
            track == CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            and life_currents is None
        ):
            life_currents = _assemble_proactive_chat_life_currents_hint_prompt(
                store
            )
        return build_turn_compose_context(
            bundle=self.bundle,
            context_meta=self.context,
            runtime_context=self.runtime_context,
            store=store,
            track=track,
            phase=self._compose_phase(),
            leg_kind=PromptLegKind.SINGLE_LLM,
            ai_private_text=ai_private_text,
            proactive_life_currents_block=life_currents,
        )

    def settled_single_llm_system_messages(self) -> list[dict[str, Any]]:
        """Settled ``user_turn`` single-LLM in-turn tools system prefix."""
        # TODO(#3629): Fold fixed reply-language into one PromptPlan Output assembly site.
        out: list[dict[str, Any]] = []
        out.extend(_doctrine_system_messages())
        out.extend(_auxiliary_system_messages())
        out.extend(_capability_settled_single_llm_system_messages(self.bundle))
        out.extend(
            _persona_settled_user_turn_system_messages(
                bundle=self.bundle,
                context=self.context,
                include_significance_perception_slice=False,
            )
        )
        out.extend(_output_settled_single_llm_system_messages())
        out.extend(
            assemble_contextual_slices(
                self._turn_compose_context(
                    track=CompanionTurnTrack.USER_CHAT,
                    store=empty_memory_store_for_compose(),
                    ai_private_text="",
                    proactive_life_currents_block=None,
                )
            )
        )
        return append_configured_fixed_reply_language_system_messages(out)

    def bootstrap_single_llm_system_messages(self) -> list[dict[str, Any]]:
        """Core and runtime bootstrap system prefix (doctrine through bootstrap contextual slices)."""
        out: list[dict[str, Any]] = []
        out.extend(_doctrine_system_messages())
        out.extend(_auxiliary_system_messages())
        out.extend(_capability_bootstrap_single_llm_system_messages())
        out.extend(
            _persona_bootstrap_user_turn_system_messages(
                bundle=self.bundle,
                context=self.context,
            )
        )
        out.extend(_output_bootstrap_single_llm_system_messages())
        out.extend(
            assemble_contextual_slices(
                self._turn_compose_context(
                    track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
                    store=empty_memory_store_for_compose(),
                    ai_private_text="",
                    proactive_life_currents_block=None,
                )
            )
        )
        return append_configured_fixed_reply_language_system_messages(out)

    def settled_dual_llm_tool_system_messages(self) -> list[dict[str, Any]]:
        """Tool-leg system prefix for settled USER_CHAT dual-LLM (not inner-tick)."""
        return append_configured_fixed_reply_language_system_messages(
            _append_runtime_channel_system_extras(
                system_dicts=build_system_messages_for_tool_track(
                    self.bundle,
                    self.context,
                ),
                bundle=self.bundle,
                runtime_context=self.runtime_context,
            )
        )

    def build_settled_user_chat_dual_llm_tool_prompt_plan(
        self,
        *,
        base_messages: list[dict[str, Any]],
        stack_depth: int,
        tools: tuple[dict[str, Any], ...],
    ) -> PromptPlan:
        """Assemble tool-leg ``PromptPlan`` for settled/async USER_CHAT dual-LLM turns."""
        assert stack_depth >= 0
        assert tools
        wire = replace_leading_system_messages_multi(
            list(base_messages),
            self.settled_dual_llm_tool_system_messages(),
            stack_depth=stack_depth,
        )
        apply_debug_github_disclosure_runtime_clause(openai_messages=wire)
        return PromptPlan(
            messages=openai_dialogue_dicts_to_prompt_messages(wire),
            tools=tools,
            tool_choice=None,
        )

    def _prompt_plan_from_system_and_dialogue(
        self,
        *,
        system_dicts: list[dict[str, Any]],
        transcript_window: list[ChatMessage],
        tail_user_messages: tuple[TurnTailUserMessage, ...],
        tools: tuple[dict[str, Any], ...],
        implicit_sign_on_turn: bool,
        tail_splice_thoughts: tuple[AiPrivateThought, ...],
    ) -> PromptPlan:
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
        for tail_user in tail_user_message_contents_for_llm(
            tail_user_messages=tail_user_messages,
            implicit_sign_on_turn=implicit_sign_on_turn,
        ):
            messages.append(
                PromptMessage(role=PromptMessageRole.USER, content=tail_user)
            )
        return PromptPlan(
            messages=tuple(messages),
            tools=tools,
            tool_choice=None,
        )

    def bootstrap_turn_system_dicts(self) -> list[dict[str, Any]]:
        """System prefix for one bootstrap turn: core stack, peripheral gateway, then cohort slices."""
        system_dicts = self.bootstrap_single_llm_system_messages()
        return self._append_track_peripheral_system_dicts(system_dicts)

    def _compose_phase(self) -> Phase:
        return resolve_compose_phase(self.context)

    def _append_track_peripheral_system_dicts(
        self,
        system_dicts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Append channel output format, Weixin alias, and bootstrap cohort overlays."""
        out = _append_runtime_channel_system_extras(
            system_dicts=system_dicts,
            bundle=self.bundle,
            runtime_context=self.runtime_context,
        )
        return append_profile_collection_system_messages(
            out,
            context=self.context,
            runtime_channel=self.runtime_context.channel,
            interactive_bootstrap_active=(
                self._compose_phase() == Phase.BOOTSTRAP
            ),
            user_md=self.bundle.user_md,
        )

    def _greeting_core_system_dicts(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        out.extend(_doctrine_system_messages())
        out.extend(_auxiliary_system_messages())
        match self._compose_phase():
            case Phase.BOOTSTRAP:
                out.extend(_capability_bootstrap_single_llm_system_messages())
                out.extend(
                    _persona_bootstrap_user_turn_system_messages(
                        bundle=self.bundle,
                        context=self.context,
                    )
                )
                if self.bundle.significance_perception_md.strip():
                    out.append(
                        _system_message(
                            self.bundle.significance_perception_md.strip()
                        )
                    )
                out.append(_system_message(_output_contract_text()))
            case Phase.SETTLED:
                out.extend(
                    _capability_settled_single_llm_system_messages(self.bundle)
                )
                out.extend(
                    _persona_settled_user_turn_system_messages(
                        bundle=self.bundle,
                        context=self.context,
                        include_significance_perception_slice=True,
                    )
                )
                out.append(_system_message(_output_contract_text()))
        out.extend(
            assemble_contextual_slices(
                self._turn_compose_context(
                    track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
                    store=empty_memory_store_for_compose(),
                    ai_private_text="",
                    proactive_life_currents_block=None,
                )
            )
        )
        return out

    def _settled_inner_tick_chat_core_system_dicts(
        self,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        out.extend(_doctrine_system_messages())
        out.extend(_auxiliary_system_messages())
        out.extend(
            _capability_system_messages(
                bundle=self.bundle,
                tools_on=False,
                chat_branch_no_tool_api=False,
                tool_side_compact=False,
                inner_tick_turn=True,
                interactive_bootstrap_active=False,
            )
        )
        out.extend(
            _persona_system_messages(
                bundle=self.bundle,
                context=self.context,
                inner_tick_turn=True,
                skip_memory_blocks=False,
                include_significance_perception_slice=False,
                interactive_bootstrap_active=False,
            )
        )
        out.extend(
            _output_system_messages(
                inner_tick_turn=True,
                tick_proactive=True,
                tools_on=False,
                tool_side_compact=False,
                async_foreground_chat_stack=False,
                interactive_bootstrap_active=False,
                include_significance_perception_slice=False,
                chat_branch_no_tool_api=False,
            )
        )
        return out

    def _bootstrap_inner_tick_chat_core_system_dicts(
        self,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        out.extend(_doctrine_system_messages())
        out.extend(_auxiliary_system_messages())
        out.extend(_capability_bootstrap_single_llm_system_messages())
        out.extend(
            _persona_bootstrap_user_turn_system_messages(
                bundle=self.bundle,
                context=self.context,
            )
        )
        out.append(_system_message(_output_contract_text()))
        return out

    def _finalize_chat_only_system_dicts(
        self,
        system_dicts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Append peripheral gateway slices and configured reply-language clause."""
        return append_configured_fixed_reply_language_system_messages(
            self._append_track_peripheral_system_dicts(system_dicts)
        )

    def greeting_system_dicts(self) -> list[dict[str, Any]]:
        """Chat-only implicit sign-on greeting system prefix."""
        return self._finalize_chat_only_system_dicts(
            self._greeting_core_system_dicts()
        )

    def proactive_system_dicts(
        self, store: MemoryStore
    ) -> list[dict[str, Any]]:
        """Chat-only proactive inner-tick system prefix."""
        life_currents_block = (
            _assemble_proactive_chat_life_currents_hint_prompt(store)
        )
        match self._compose_phase():
            case Phase.BOOTSTRAP:
                out = self._bootstrap_inner_tick_chat_core_system_dicts()
            case Phase.SETTLED:
                out = self._settled_inner_tick_chat_core_system_dicts()
        out.extend(
            assemble_contextual_slices(
                self._turn_compose_context(
                    track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
                    store=store,
                    ai_private_text="",
                    proactive_life_currents_block=life_currents_block,
                )
            )
        )
        out.append(
            _system_message(_proactive_chat_structured_output_contract_text())
        )
        return self._finalize_chat_only_system_dicts(out)

    def scheduled_system_dicts(
        self, store: MemoryStore
    ) -> list[dict[str, Any]]:
        """Chat-only scheduled reminder inner-tick system prefix."""
        match self._compose_phase():
            case Phase.BOOTSTRAP:
                out = self._bootstrap_inner_tick_chat_core_system_dicts()
            case Phase.SETTLED:
                out = self._settled_inner_tick_chat_core_system_dicts()
        out.extend(
            assemble_contextual_slices(
                self._turn_compose_context(
                    track=CompanionTurnTrack.INNER_TICK_SCHEDULED,
                    store=store,
                    ai_private_text="",
                    proactive_life_currents_block=None,
                )
            )
        )
        out.append(
            _system_message(
                _scheduled_reminder_structured_output_contract_text()
            )
        )
        return self._finalize_chat_only_system_dicts(out)

    def _compose_settled_single_llm_user_chat_prompt(
        self,
        *,
        transcript_window: list[ChatMessage],
        tail_user_messages: tuple[TurnTailUserMessage, ...],
        tools: tuple[dict[str, Any], ...],
        implicit_sign_on_turn: bool,
        tail_splice_thoughts: tuple[AiPrivateThought, ...],
    ) -> PromptPlan:
        """Compose one settled-turn PromptPlan: core stack, peripheral gateway slices, then dialogue."""
        system_dicts = _append_runtime_channel_system_extras(
            system_dicts=self.settled_single_llm_system_messages(),
            bundle=self.bundle,
            runtime_context=self.runtime_context,
        )
        return self._prompt_plan_from_system_and_dialogue(
            system_dicts=system_dicts,
            transcript_window=transcript_window,
            tail_user_messages=tail_user_messages,
            tools=tools,
            implicit_sign_on_turn=implicit_sign_on_turn,
            tail_splice_thoughts=tail_splice_thoughts,
        )

    def _compose_bootstrap_single_llm_user_chat_prompt(
        self,
        *,
        transcript_window: list[ChatMessage],
        tail_user_messages: tuple[TurnTailUserMessage, ...],
        tools: tuple[dict[str, Any], ...],
        implicit_sign_on_turn: bool,
        tail_splice_thoughts: tuple[AiPrivateThought, ...],
    ) -> PromptPlan:
        """Compose one bootstrap-turn PromptPlan: core stack, peripheral gateway and cohort slices, then dialogue."""
        return self._prompt_plan_from_system_and_dialogue(
            system_dicts=self.bootstrap_turn_system_dicts(),
            transcript_window=transcript_window,
            tail_user_messages=tail_user_messages,
            tools=tools,
            implicit_sign_on_turn=implicit_sign_on_turn,
            tail_splice_thoughts=tail_splice_thoughts,
        )

    def build_user_chat_prompt(
        self,
        *,
        transcript_window: list[ChatMessage],
        tail_user_messages: tuple[TurnTailUserMessage, ...],
        tools: tuple[dict[str, Any], ...],
        implicit_sign_on_turn: bool,
        tail_splice_thoughts: tuple[AiPrivateThought, ...],
    ) -> PromptPlan:
        """Assemble initial settled single-LLM user-chat prompt with in-turn tools."""
        assert tail_user_messages
        return self._compose_settled_single_llm_user_chat_prompt(
            transcript_window=transcript_window,
            tail_user_messages=tail_user_messages,
            tools=tools,
            implicit_sign_on_turn=implicit_sign_on_turn,
            tail_splice_thoughts=tail_splice_thoughts,
        )

    def build_bootstrap_user_chat_prompt(
        self,
        *,
        transcript_window: list[ChatMessage],
        tail_user_messages: tuple[TurnTailUserMessage, ...],
        tools: tuple[dict[str, Any], ...],
        implicit_sign_on_turn: bool,
        tail_splice_thoughts: tuple[AiPrivateThought, ...],
    ) -> PromptPlan:
        """Assemble initial bootstrap single-LLM user-chat prompt with in-turn tools."""
        assert tail_user_messages
        return self._compose_bootstrap_single_llm_user_chat_prompt(
            transcript_window=transcript_window,
            tail_user_messages=tail_user_messages,
            tools=tools,
            implicit_sign_on_turn=implicit_sign_on_turn,
            tail_splice_thoughts=tail_splice_thoughts,
        )


def refresh_single_llm_user_chat_prompt_prefix(
    *,
    store: MemoryStore,
    messages: list[dict[str, Any]],
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Refresh settled single-LLM system prefix; return tools for later rounds."""
    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    builder = PromptBuilder(
        bundle=bundle,
        context=context,
        runtime_context=runtime_context,
    )
    refreshed = _append_runtime_channel_system_extras(
        system_dicts=builder.settled_single_llm_system_messages(),
        bundle=bundle,
        runtime_context=runtime_context,
    )
    replace_leading_system_messages_inplace(messages, refreshed)
    return build_openai_repl_tools()


def refresh_single_llm_bootstrap_chat_prompt_prefix(
    *,
    store: MemoryStore,
    messages: list[dict[str, Any]],
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Refresh bootstrap single-LLM system prefix; return tools for later rounds."""
    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    builder = PromptBuilder(
        bundle=bundle,
        context=context,
        runtime_context=runtime_context,
    )
    replace_leading_system_messages_inplace(
        messages, builder.bootstrap_turn_system_dicts()
    )
    return build_openai_bootstrap_track_tools()
