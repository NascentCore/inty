"""1-LLM agentic loop mechanism (delegates ``run_in_turn_sync_tool_loop``)."""

from __future__ import annotations

from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    InTurnSyncToolLoopInput,
    run_in_turn_sync_tool_loop,
)

from ..contract import AgenticLoopOutput, AgenticLoopRunBundle
from ..sink_adapters import make_bootstrap_interim_sink


class OneModelInTurnSyncMechanism:
    """In-turn single-LLM sync tool loop with per-call-streaming interim + terminal."""

    async def run(self, bundle: AgenticLoopRunBundle) -> AgenticLoopOutput:
        loop_input = bundle.loop_input
        output_queue = bundle.output_queue
        interim_sink = make_bootstrap_interim_sink(output_queue)
        sync_result = await run_in_turn_sync_tool_loop(
            InTurnSyncToolLoopInput(
                store=loop_input.store,
                llm_client=loop_input.llm_client,
                messages=loop_input.openai_messages,
                tools_for_turn=loop_input.openai_tools,
                write_allowlist=loop_input.write_allowlist,
                langsmith_foreground_source=loop_input.langsmith_foreground_source,
                repository_only_store_text=loop_input.repository_only_store_text,
                trace_id=loop_input.trace_id,
                user_text=loop_input.user_text,
                ts_user=loop_input.ts_user,
                user_msg_uuid=loop_input.user_msg_uuid,
                transcript_rel=loop_input.transcript_rel,
                interim_output_sink=interim_sink,
                skip_inline_interim_transcript=True,
                langsmith_slice=loop_input.langsmith_slice,
                max_tool_rounds=loop_input.max_tool_rounds,
                after_tool_messages_appended=loop_input.after_tool_messages_appended,
            )
        )
        terminal_text = sync_result.assistant_text.strip()
        if terminal_text:
            await output_queue.push_user_reply(assistant_text=terminal_text)
        return AgenticLoopOutput(
            assistant_text=sync_result.assistant_text,
            significance_meta=None,
            turn_recall=None,
            langsmith_trace_id=sync_result.langsmith_trace_id,
            langsmith_run_id=sync_result.langsmith_run_id,
            deliverables=output_queue.deliverables,
            skip_final_transcript_assistant_row=(
                sync_result.skip_final_transcript_assistant_row
            ),
            tool_background_started=False,
            last_interim_assistant_msg_uuid=(
                sync_result.last_interim_assistant_msg_uuid
            ),
        )
