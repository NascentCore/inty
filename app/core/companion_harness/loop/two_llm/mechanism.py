"""2-LLM agentic loop mechanism (fg + in-process tool leg)."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.companion.dual_llm_foreground_chat import (
    DualLlmForegroundChatInput,
    run_dual_llm_foreground_chat,
)
from app.core.companion_harness.companion.dual_llm_message_stacks import (
    dual_llm_system_message_variants,
    replace_leading_system_messages_multi,
)
from app.core.companion_harness.companion.models import InnerTickActivity
from app.core.companion_harness.companion.llm_client import (
    LLM_SCENE_CHAT,
    LLM_SCENE_INNER_TICK,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call as repl_execute_tool_call,
)
from app.core.companion_harness.tools.tool_background import run_tool_background_loop

from ..contract import AgenticLoopInput, AgenticLoopOutput, AgenticLoopRunBundle
from ..sink_adapters import ToolBackgroundEventSink


class TwoModelChatThenToolBgMechanism:
    """Dual-LLM foreground envelope + in-process ``run_tool_background_loop``."""

    async def run(self, bundle: AgenticLoopRunBundle) -> AgenticLoopOutput:
        loop_input = bundle.loop_input
        output_queue = bundle.output_queue
        chat_msgs, tool_msgs = _resolve_dual_llm_message_stacks(loop_input)
        chat_model = loop_input.llm_client.resolve_model("chat")
        tool_model = loop_input.llm_client.resolve_model("tool")
        tick_proactive = (
            loop_input.inner_tick_turn
            and loop_input.inner_tick_activity
            == InnerTickActivity.PROACTIVE_CHAT
        )
        foreground_scene = (
            LLM_SCENE_INNER_TICK
            if loop_input.inner_tick_turn and not tick_proactive
            else LLM_SCENE_CHAT
        )
        fg_result = await run_dual_llm_foreground_chat(
            DualLlmForegroundChatInput(
                llm_client=loop_input.llm_client,
                chat_msgs=chat_msgs,
                tool_msgs=tool_msgs,
                chat_model=chat_model,
                langsmith_slice=loop_input.langsmith_slice,
                foreground_scene=foreground_scene,
                high_reasoning=loop_input.high_reasoning,
                trace_id=loop_input.trace_id,
                skip_foreground_envelope=loop_input.skip_foreground_envelope,
                route_inner_activity=loop_input.inner_tick_activity,
                langsmith_trace_id=loop_input.langsmith_trace_id,
                langsmith_run_id=loop_input.langsmith_run_id,
            )
        )
        fg_text = fg_result.assistant_text.strip()
        if fg_text:
            await output_queue.push_foreground_text(
                assistant_text=fg_text,
                significance_meta=fg_result.significance_meta,
                turn_recall=fg_result.turn_recall,
            )
        event_sink = ToolBackgroundEventSink(output_queue)
        await run_tool_background_loop(
            memory_store=loop_input.store,
            request_messages=list(fg_result.tool_msgs_for_bg),
            tool_model=tool_model,
            user_msg_uuid=loop_input.user_msg_uuid,
            trace_id=loop_input.trace_id,
            tools=list(loop_input.openai_tools),
            on_event=event_sink,
            execute_tool_call_fn=repl_execute_tool_call,
            client=loop_input.llm_client.sync_client_for_route("tool"),
            chat_completion_sync=loop_input.llm_client.chat_completions_sync,
            write_allowlist=loop_input.write_allowlist,
            repository_only_store_text=loop_input.repository_only_store_text,
            memory_bootstrap_type=loop_input.memory_bootstrap_type,
            inner_tick_turn=loop_input.inner_tick_turn,
            inner_tick_activity=loop_input.inner_tick_activity,
            runtime_context=loop_input.runtime_context,
            companion_turn_track=loop_input.companion_turn_track,
            force_tools_first_round=fg_result.force_tools_first_round,
        )
        # TODO(#3398): production ``turn.py`` uses ``start_tool_background_job`` (thread);
        # sidecar uses in-process ``await`` — add ``ThreadToolLegAdapter`` at integration.
        await event_sink.flush()
        return AgenticLoopOutput(
            assistant_text=fg_result.assistant_text,
            significance_meta=fg_result.significance_meta,
            turn_recall=fg_result.turn_recall,
            langsmith_trace_id=fg_result.langsmith_trace_id,
            langsmith_run_id=fg_result.langsmith_run_id,
            deliverables=output_queue.deliverables,
            skip_final_transcript_assistant_row=False,
            tool_background_started=True,
        )


def _resolve_dual_llm_message_stacks(
    loop_input: AgenticLoopInput,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    if (
        loop_input.dual_llm_chat_msgs is not None
        and loop_input.dual_llm_tool_msgs is not None
    ):
        return loop_input.dual_llm_chat_msgs, loop_input.dual_llm_tool_msgs
    assert loop_input.prompt_bundle is not None
    assert loop_input.context_meta is not None
    tool_system_msgs, chat_system_msgs = dual_llm_system_message_variants(
        store=loop_input.store,
        bundle=loop_input.prompt_bundle,
        context=loop_input.context_meta,
        memory_bootstrap_type=loop_input.memory_bootstrap_type,
        inner_tick_turn=loop_input.inner_tick_turn,
        route_inner_activity=loop_input.inner_tick_activity,
        runtime_context=loop_input.runtime_context,
    )
    base_messages = list(loop_input.openai_messages)
    chat_msgs = tuple(
        replace_leading_system_messages_multi(
            base_messages,
            chat_system_msgs,
            stack_depth=loop_input.stack_depth,
        )
    )
    tool_msgs = tuple(
        replace_leading_system_messages_multi(
            base_messages,
            tool_system_msgs,
            stack_depth=loop_input.stack_depth,
        )
    )
    return chat_msgs, tool_msgs
