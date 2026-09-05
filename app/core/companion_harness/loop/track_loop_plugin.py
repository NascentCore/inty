"""Track-family AgenticLoop plugins for companion turn dispatch (#3393 slice 3b)."""

from __future__ import annotations

from typing import Any, Protocol

from app.core.agentic_companion.types import (
    UserMessageBatch,
    synthetic_user_message_batch,
)
from app.core.companion_harness.companion.dual_llm_message_stacks import (
    dual_llm_system_message_variants,
    replace_leading_system_messages_multi,
)
from app.core.companion_harness.companion.models import (
    ChatMessage,
    CompanionTurnTrack,
)
from app.core.companion_harness.companion.transcript_ai_private import (
    expand_manifest_rows,
    track_uses_ai_private_splice,
)
from app.core.companion_harness.loop.agentic_loop import AgenticLoop
from app.core.companion_harness.loop.config import (
    AgenticLoopMechanism,
    resolve_agentic_loop_mechanism,
)
from app.core.companion_harness.loop.context import (
    AgenticLoopOutput,
    build_bootstrap_user_chat_loop_context,
    build_implicit_sign_on_greeting_loop_context,
    build_inner_tick_chat_only_loop_context,
    build_inner_tick_tool_loop_context,
    build_settled_dual_llm_user_chat_loop_context,
    build_settled_user_chat_loop_context,
)
from app.core.companion_harness.loop.track_loop_input import (
    CompanionTurnLoopInput,
)
from app.core.companion_harness.prompting.track_composer import (
    TrackPromptComposer,
)
from app.core.companion_harness.loop.track_policy import (
    build_loop_execution_policy,
)
from app.core.companion_harness.prompt_builder import (
    PromptBuilder,
    PromptPlan,
    prompt_messages_to_openai_dicts,
    refresh_single_llm_bootstrap_chat_prompt_prefix,
    refresh_single_llm_user_chat_prompt_prefix,
)

_TRACK_COMPOSER = TrackPromptComposer()


class AgenticLoopTurnPlugin(Protocol):
    """Build loop context for one track family and execute via AgenticLoop."""

    async def run(self, prepared: CompanionTurnLoopInput) -> AgenticLoopOutput:
        """Execute one companion turn through AgenticLoop + OutputQueue."""


def _stack_depth_openai_messages(messages: list[dict[str, Any]]) -> int:
    return sum(1 for message in messages if message.get("role") == "system")


def _system_stack_depth_from_prompt_plan(prompt_plan: PromptPlan) -> int:
    return sum(
        1 for message in prompt_plan.messages if message.role.value == "system"
    )


def _user_message_batch_or_synthetic(
    prepared: CompanionTurnLoopInput,
) -> UserMessageBatch:
    user_message_batch = prepared.user_message_batch
    if user_message_batch is not None:
        return user_message_batch
    return synthetic_user_message_batch(
        user_msg_uuid=prepared.user_msg_uuid,
        track_label=prepared.track.value,
    )


def _expanded_transcript_window(
    prepared: CompanionTurnLoopInput,
) -> list[ChatMessage]:
    transcript_window = prepared.loaded_state.transcript_window
    if track_uses_ai_private_splice(prepared.track):
        return expand_manifest_rows(
            prepared.store,
            prepared.loaded_state.transcript_window,
        )
    return transcript_window


def _loop_execution_policy(prepared: CompanionTurnLoopInput):
    return build_loop_execution_policy(
        track=prepared.track,
        runtime_flags=prepared.runtime_flags,
        has_openai_tools=bool(prepared.tools_for_turn),
    )


def _agentic_loop(prepared: CompanionTurnLoopInput) -> AgenticLoop:
    return AgenticLoop(
        store=prepared.store,
        llm_client=prepared.llm_client.async_llm_client,
        legacy_llm_client=prepared.llm_client,
    )


class BootstrapUserChatPlugin:
    """``USER_CHAT_BOOTSTRAP`` single-LLM AgenticLoop with bootstrap prompt refresh."""

    async def run(self, prepared: CompanionTurnLoopInput) -> AgenticLoopOutput:
        assert prepared.user_message_batch is not None
        p = prepared
        store = p.store
        runtime_context = p.runtime_context
        bundle = p.loaded_state.bundle
        context = p.loaded_state.context

        async def _after_tool_round(
            messages_with_tool_results: list[dict[str, Any]],
        ) -> list[dict[str, Any]]:
            return refresh_single_llm_bootstrap_chat_prompt_prefix(
                store=store,
                messages=messages_with_tool_results,
                runtime_context=runtime_context,
            )

        transcript_window = _expanded_transcript_window(p)
        bootstrap_prompt_plan = PromptBuilder(
            bundle=bundle,
            context=context,
            runtime_context=runtime_context,
        ).build_bootstrap_user_chat_prompt(
            transcript_window=transcript_window,
            tail_user_messages=p.tail_user_messages,
            tools=tuple(p.tools_for_turn),
            implicit_sign_on_turn=p.runtime_flags.implicit_sign_on_turn,
            tail_splice_thoughts=p.ai_private_splice_plan.thoughts,
        )
        execution = _loop_execution_policy(p)
        loop_context = build_bootstrap_user_chat_loop_context(
            tools_for_turn=p.tools_for_turn,
            repository_only_store_text=p.repository_only_store_text,
            trace_id=p.trace_id,
            user_text=p.user_text,
            ts_user=p.ts_user,
            user_msg_uuid=p.user_msg_uuid,
            transcript_rel=p.transcript_rel,
            langsmith_slice=p.langsmith_slice,
            runtime_context=runtime_context,
            stack_depth=_system_stack_depth_from_prompt_plan(
                bootstrap_prompt_plan
            ),
            langsmith_trace_id=p.langsmith_trace_id,
            langsmith_run_id=p.langsmith_run_id,
            after_tool_messages_appended=_after_tool_round,
            output_queue=p.agentic_output_queue,
            user_message_batch=p.user_message_batch,
            tail_user_messages=p.tail_user_messages,
            prompt_plan=bootstrap_prompt_plan,
            execution=execution,
        )
        return await _agentic_loop(p).run_single_llm_turn(context=loop_context)


class SettledUserChatPlugin:
    """Settled ``USER_CHAT`` via single-LLM or dual-LLM mechanism from config."""

    async def run(self, prepared: CompanionTurnLoopInput) -> AgenticLoopOutput:
        assert prepared.user_message_batch is not None
        p = prepared
        store = p.store
        runtime_context = p.runtime_context
        bundle = p.loaded_state.bundle
        context = p.loaded_state.context
        execution = _loop_execution_policy(p)

        match resolve_agentic_loop_mechanism(track=p.track):
            case AgenticLoopMechanism.SINGLE_LLM:

                async def _after_tool_round(
                    messages_with_tool_results: list[dict[str, Any]],
                ) -> list[dict[str, Any]]:
                    return refresh_single_llm_user_chat_prompt_prefix(
                        store=store,
                        messages=messages_with_tool_results,
                        runtime_context=runtime_context,
                    )

                transcript_window = _expanded_transcript_window(p)
                single_llm_prompt_plan = PromptBuilder(
                    bundle=bundle,
                    context=context,
                    runtime_context=runtime_context,
                ).build_user_chat_prompt(
                    transcript_window=transcript_window,
                    tail_user_messages=p.tail_user_messages,
                    tools=tuple(p.tools_for_turn),
                    implicit_sign_on_turn=p.runtime_flags.implicit_sign_on_turn,
                    tail_splice_thoughts=p.ai_private_splice_plan.thoughts,
                )
                loop_context = build_settled_user_chat_loop_context(
                    tools_for_turn=p.tools_for_turn,
                    repository_only_store_text=p.repository_only_store_text,
                    trace_id=p.trace_id,
                    user_text=p.user_text,
                    ts_user=p.ts_user,
                    user_msg_uuid=p.user_msg_uuid,
                    transcript_rel=p.transcript_rel,
                    langsmith_slice=p.langsmith_slice,
                    runtime_context=runtime_context,
                    stack_depth=_system_stack_depth_from_prompt_plan(
                        single_llm_prompt_plan
                    ),
                    langsmith_trace_id=p.langsmith_trace_id,
                    langsmith_run_id=p.langsmith_run_id,
                    after_tool_messages_appended=_after_tool_round,
                    output_queue=p.agentic_output_queue,
                    user_message_batch=p.user_message_batch,
                    tail_user_messages=p.tail_user_messages,
                    execution=execution,
                    prompt_plan=single_llm_prompt_plan,
                )
                return await _agentic_loop(p).run_single_llm_turn(
                    context=loop_context
                )
            case AgenticLoopMechanism.DUAL_LLM:
                # TODO(#3460): Move dual-LLM message-stack assembly into loop/context.py.
                _, chat_system_msgs = dual_llm_system_message_variants(
                    store=store,
                    bundle=bundle,
                    context=context,
                    inner_tick_turn=False,
                    route_inner_activity=p.runtime_flags.route_inner_activity,
                    runtime_context=runtime_context,
                )
                stack_depth = len(p.prompt_plan.system_messages)
                chat_msgs = replace_leading_system_messages_multi(
                    p.messages,
                    chat_system_msgs,
                    stack_depth=stack_depth,
                )
                dual_llm_prompt_builder = PromptBuilder(
                    bundle=bundle,
                    context=context,
                    runtime_context=runtime_context,
                )
                tool_plan = dual_llm_prompt_builder.build_settled_user_chat_dual_llm_tool_prompt_plan(
                    base_messages=p.messages,
                    stack_depth=stack_depth,
                    tools=tuple(p.tools_for_turn),
                )
                tool_msgs = prompt_messages_to_openai_dicts(tool_plan.messages)
                loop_context = build_settled_dual_llm_user_chat_loop_context(
                    tools_for_turn=p.tools_for_turn,
                    repository_only_store_text=p.repository_only_store_text,
                    trace_id=p.trace_id,
                    user_text=p.user_text,
                    ts_user=p.ts_user,
                    user_msg_uuid=p.user_msg_uuid,
                    transcript_rel=p.transcript_rel,
                    langsmith_slice=p.langsmith_slice,
                    runtime_context=runtime_context,
                    stack_depth=stack_depth,
                    langsmith_trace_id=p.langsmith_trace_id,
                    langsmith_run_id=p.langsmith_run_id,
                    output_queue=p.agentic_output_queue,
                    user_message_batch=p.user_message_batch,
                    tail_user_messages=p.tail_user_messages,
                    dual_llm_chat_msgs=tuple(chat_msgs),
                    dual_llm_tool_msgs=tuple(tool_msgs),
                    prompt_bundle=bundle,
                    context_meta=context,
                    execution=execution,
                )
                return await _agentic_loop(p).run_dual_llm_turn(
                    context=loop_context
                )


class ImplicitSignOnGreetingPlugin:
    """``IMPLICIT_SIGN_ON_GREETING`` chat-only single-LLM turn."""

    async def run(self, prepared: CompanionTurnLoopInput) -> AgenticLoopOutput:
        p = prepared
        user_message_batch = _user_message_batch_or_synthetic(p)
        execution = _loop_execution_policy(p)
        greeting_prompt_plan = _TRACK_COMPOSER.compose_from_openai_messages(
            p.messages,
            tools=(),
        )
        loop_context = build_implicit_sign_on_greeting_loop_context(
            repository_only_store_text=p.repository_only_store_text,
            trace_id=p.trace_id,
            user_text=p.user_text,
            ts_user=p.ts_user,
            user_msg_uuid=p.user_msg_uuid,
            transcript_rel=p.transcript_rel,
            langsmith_slice=p.langsmith_slice,
            runtime_context=p.runtime_context,
            stack_depth=_stack_depth_openai_messages(p.messages),
            langsmith_trace_id=p.langsmith_trace_id,
            langsmith_run_id=p.langsmith_run_id,
            output_queue=p.agentic_output_queue,
            user_message_batch=user_message_batch,
            tail_user_messages=p.tail_user_messages,
            prompt_plan=greeting_prompt_plan,
            execution=execution,
        )
        return await _agentic_loop(p).run_single_llm_turn(context=loop_context)


class InnerTickChatOnlyPlugin:
    """Proactive and scheduled inner-tick chat-only turns."""

    async def run(self, prepared: CompanionTurnLoopInput) -> AgenticLoopOutput:
        p = prepared
        user_message_batch = _user_message_batch_or_synthetic(p)
        execution = _loop_execution_policy(p)
        inner_prompt_plan = _TRACK_COMPOSER.compose_from_openai_messages(
            p.messages,
            tools=(),
        )
        loop_context = build_inner_tick_chat_only_loop_context(
            track=p.track,
            repository_only_store_text=p.repository_only_store_text,
            trace_id=p.trace_id,
            user_text=p.user_text,
            ts_user=p.ts_user,
            user_msg_uuid=p.user_msg_uuid,
            transcript_rel=p.transcript_rel,
            langsmith_slice=p.langsmith_slice,
            runtime_context=p.runtime_context,
            stack_depth=_stack_depth_openai_messages(p.messages),
            langsmith_trace_id=p.langsmith_trace_id,
            langsmith_run_id=p.langsmith_run_id,
            output_queue=p.agentic_output_queue,
            user_message_batch=user_message_batch,
            tail_user_messages=p.tail_user_messages,
            prompt_plan=inner_prompt_plan,
            execution=execution,
        )
        return await _agentic_loop(p).run_single_llm_turn(context=loop_context)


class InnerTickToolLoopPlugin:
    """Monolog and autonomy inner-tick turns with inline tool loop."""

    async def run(self, prepared: CompanionTurnLoopInput) -> AgenticLoopOutput:
        p = prepared
        user_message_batch = _user_message_batch_or_synthetic(p)
        execution = _loop_execution_policy(p)
        throttle_prompt_plan = _TRACK_COMPOSER.compose_from_openai_messages(
            p.messages,
            tools=tuple(p.tools_for_turn),
        )
        loop_context = build_inner_tick_tool_loop_context(
            track=p.track,
            tools_for_turn=p.tools_for_turn,
            repository_only_store_text=p.repository_only_store_text,
            trace_id=p.trace_id,
            user_text=p.user_text,
            ts_user=p.ts_user,
            user_msg_uuid=p.user_msg_uuid,
            transcript_rel=p.transcript_rel,
            langsmith_slice=p.langsmith_slice,
            runtime_context=p.runtime_context,
            stack_depth=_stack_depth_openai_messages(p.messages),
            langsmith_trace_id=p.langsmith_trace_id,
            langsmith_run_id=p.langsmith_run_id,
            output_queue=p.agentic_output_queue,
            user_message_batch=user_message_batch,
            tail_user_messages=p.tail_user_messages,
            prompt_plan=throttle_prompt_plan,
            execution=execution,
        )
        return await _agentic_loop(p).run_single_llm_turn(context=loop_context)


_BOOTSTRAP_PLUGIN = BootstrapUserChatPlugin()
_SETTLED_USER_CHAT_PLUGIN = SettledUserChatPlugin()
_GREETING_PLUGIN = ImplicitSignOnGreetingPlugin()
_INNER_TICK_CHAT_PLUGIN = InnerTickChatOnlyPlugin()
_INNER_TICK_TOOL_PLUGIN = InnerTickToolLoopPlugin()


def resolve_agentic_loop(*, track: CompanionTurnTrack) -> AgenticLoopTurnPlugin:
    """Return the loop plugin for one production companion turn track."""
    match track:
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            return _BOOTSTRAP_PLUGIN
        case CompanionTurnTrack.USER_CHAT:
            return _SETTLED_USER_CHAT_PLUGIN
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            return _GREETING_PLUGIN
        case (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
        ):
            return _INNER_TICK_CHAT_PLUGIN
        case (
            CompanionTurnTrack.INNER_TICK_MONOLOG
            | CompanionTurnTrack.INNER_TICK_AUTONOMY
        ):
            return _INNER_TICK_TOOL_PLUGIN
        case _ as unexpected:
            raise AssertionError(f"no loop plugin for track={unexpected!r}")
