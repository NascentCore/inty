"""CI-gated harness orchestration tests using scripted FakeOpenAI transport.

Covered: settled ``USER_CHAT`` (no-tools x ``dual_llm`` + ``in_turn_single_llm``;
tool-bg ``dual_llm`` only), bootstrap, proactive single-shot and multi-round silent envelope,
``INNER_TICK_MONOLOG`` tool-background (``ai_private_append`` only, no foreground LLM).

Excluded (documented): autonomy (#3580), dreaming, proactive+tool (#3285),
sequential double-drain. ``IN_TURN_SINGLE_LLM`` tool-bg uses in-turn sync tools — see
``test_agentic_loop_output_queue.py``; not duplicated here.

TODO(#3606): Add FakeOpenAI scripted github_issue / companion_record_user_feedback path
so CI regression does not depend on live LLM tool compliance.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC

import pytest

from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    clear_output_queues_for_tests,
    get_output_queue_for_scope,
)
from app.core.companion_harness.agentic_companion.types import (
    AgenticLoopInputBatch,
    InputQueueRecord,
    QueueStatus,
    UserMessageBatch,
)
from app.core.companion_harness.companion.ai_private_prompt import (
    load_ai_private_thoughts,
)
from app.core.companion_harness.companion.models import InnerTickActivity
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
    CompanionSession,
)
from app.core.companion_harness.loop.config import (
    BatchUserMessagesLlmCallMode,
    UserTurnLlmLoopMode,
)
from app.core.companion_harness.memory.memory_registry import (
    shutdown_all_memory_stores,
)
from app.core.companion_harness.tools.tool_background import (
    TOOL_RESULTS_TRANSCRIPT_MARKER,
)
from app.external_services.fakes.openai import (
    FakeCompletionStep,
    FakeOpenAI,
    fake_step_proactive_chat_envelope,
    fake_step_text,
)
from app.core.config import global_config_loaded_from_config_yaml
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
    delete_guest_scope_for_test,
)
from tests.app.core.companion_harness.companion.bootstrap_test_helpers import (
    mark_interactive_bootstrap_completed,
)
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    SettledUserChatScriptScenario,
    build_scripted_monolog_inner_tick_script,
    build_scripted_settled_user_chat_script,
    companion_llm_client_with_scripted_transport,
    scripted_harness_llm_config,
    scripted_inner_tick_transcript_rows,
    scripted_tool_background_done_rows,
    scripted_transcript_roles,
    scripted_transcript_rows,
    seed_settled_scope_for_inner_tick,
    with_scripted_user_turn_llm_loop_mode,
)


async def _build_scripted_manager(
    *,
    script: tuple[FakeCompletionStep, ...],
    bootstrap_completed: bool = False,
) -> tuple[CompanionManager, CompanionSession, FakeOpenAI, AgentScope]:
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="harn",
        meta_data={"test": "scripted_llm"},
    )
    llm_config = scripted_harness_llm_config()
    client, fake = companion_llm_client_with_scripted_transport(
        llm_config, script
    )
    config = CompanionConfig(
        llm=llm_config,
        memory_pg_dsn=companion_memory_registry_dsn(),
        langsmith_companion_parent_run_enabled=False,
    )
    manager = CompanionManager(config, llm_client=client)
    session = manager.get_or_create_session(
        scope.user_id,
        scope.agent_id,
        scope.memory_store_chat_id(),
    )
    if bootstrap_completed:
        mark_interactive_bootstrap_completed(session.store)
    return manager, session, fake, scope


def _input_record(
    *,
    scope: AgentScope,
    message_id: str,
    sequence: int,
    text: str,
) -> InputQueueRecord:
    return InputQueueRecord(
        message_id=message_id,
        scope=scope,
        sequence=sequence,
        status=QueueStatus.CLAIMED,
        channel=ChannelKind.APP_WS,
        wire_id="wire-1",
        text=text,
        received_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture(autouse=True)
def _clear_output_queue_registry() -> None:
    clear_output_queues_for_tests()
    yield
    clear_output_queues_for_tests()


@pytest.fixture(autouse=True)
def _shutdown_memory_stores_after_test() -> None:
    yield
    shutdown_all_memory_stores()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "llm_loop_mode",
    [UserTurnLlmLoopMode.DUAL_LLM, UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM],
)
async def test_user_chat_no_tools_delivers_foreground_to_output_queue(
    llm_loop_mode: UserTurnLlmLoopMode,
) -> None:
    built = build_scripted_settled_user_chat_script(
        llm_loop_mode,
        SettledUserChatScriptScenario.NO_TOOLS,
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=built.steps,
        bootstrap_completed=True,
    )
    try:
        with with_scripted_user_turn_llm_loop_mode(llm_loop_mode):
            output_queue = get_output_queue_for_scope(scope)
            batch_id = str(uuid.uuid4())
            user_msg_id = str(uuid.uuid4())
            user_batch = UserMessageBatch(
                batch_id=batch_id, message_ids=(user_msg_id,)
            )

            result = await manager.run_user_chat_turn(
                session,
                "hello",
                preset_user_msg_uuid=user_msg_id,
                agentic_output_queue=output_queue,
                user_message_batch=user_batch,
                runtime_context=TurnRuntimeContext(
                    channel=ChannelKind.APP_WS,
                    implicit_signal_bundle=None,
                ),
            )

            ready = await output_queue.pull_ready_batch()
            assert built.expected_foreground_reply is not None
            texts = [row.text for row in ready]
            assert texts == [built.expected_foreground_reply]
            assert (
                result.assistant_text.strip() == built.expected_foreground_reply
            )
            assert scripted_transcript_roles(session.store) == [
                "user",
                "assistant",
            ]
            assert fake.script_index == built.expected_step_count
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_user_chat_default_multi_batch_persists_each_user_row() -> None:
    script = (
        fake_step_text("I saw both messages."),
        fake_step_text(""),
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        bootstrap_completed=True,
    )
    try:
        output_queue = get_output_queue_for_scope(scope)
        batch_id = str(uuid.uuid4())
        first_msg_id = str(uuid.uuid4())
        second_msg_id = str(uuid.uuid4())
        user_batch = UserMessageBatch(
            batch_id=batch_id, message_ids=(first_msg_id, second_msg_id)
        )
        input_batch = AgenticLoopInputBatch(
            batch_id=batch_id,
            scope=scope,
            messages=(
                _input_record(
                    scope=scope,
                    message_id=first_msg_id,
                    sequence=1,
                    text="first",
                ),
                _input_record(
                    scope=scope,
                    message_id=second_msg_id,
                    sequence=2,
                    text="second",
                ),
            ),
            primary_user_msg_uuid=second_msg_id,
        )

        result = await manager.run_user_chat_turn(
            session,
            "first\nsecond",
            preset_user_msg_uuid=second_msg_id,
            agentic_output_queue=output_queue,
            user_message_batch=user_batch,
            input_batch=input_batch,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )

        ready = await output_queue.pull_ready_batch()
        assert [row.text for row in ready] == ["I saw both messages."]
        assert result.transcript_user_content == "first\nsecond"
        transcript = scripted_transcript_rows(session.store)
        assert [row["role"] for row in transcript] == [
            "user",
            "user",
            "assistant",
        ]
        assert [(row["uuid"], row["content"]) for row in transcript[:2]] == [
            (first_msg_id, "first"),
            (second_msg_id, "second"),
        ]
        assert transcript[2]["reply_to"] == second_msg_id
        assert fake.script_index == len(script)
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_user_chat_join_mode_batch_persists_one_user_row() -> None:
    script = (
        fake_step_text("Joined reply."),
        fake_step_text(""),
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        bootstrap_completed=True,
    )
    cfg = (
        global_config_loaded_from_config_yaml.agent.companion_harness.user_turn
    )
    original_mode = cfg.batch_user_messages_llm_call_mode
    cfg.batch_user_messages_llm_call_mode = (
        BatchUserMessagesLlmCallMode.JOIN_TO_ONE_USER_MESSAGE.value
    )
    try:
        output_queue = get_output_queue_for_scope(scope)
        batch_id = str(uuid.uuid4())
        first_msg_id = str(uuid.uuid4())
        second_msg_id = str(uuid.uuid4())
        user_batch = UserMessageBatch(
            batch_id=batch_id, message_ids=(first_msg_id, second_msg_id)
        )
        input_batch = AgenticLoopInputBatch(
            batch_id=batch_id,
            scope=scope,
            messages=(
                _input_record(
                    scope=scope,
                    message_id=first_msg_id,
                    sequence=1,
                    text="first",
                ),
                _input_record(
                    scope=scope,
                    message_id=second_msg_id,
                    sequence=2,
                    text="second",
                ),
            ),
            primary_user_msg_uuid=second_msg_id,
        )

        result = await manager.run_user_chat_turn(
            session,
            "first\nsecond",
            preset_user_msg_uuid=second_msg_id,
            agentic_output_queue=output_queue,
            user_message_batch=user_batch,
            input_batch=input_batch,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )

        ready = await output_queue.pull_ready_batch()
        assert [row.text for row in ready] == ["Joined reply."]
        assert result.transcript_user_content == "first\nsecond"
        transcript = scripted_transcript_rows(session.store)
        assert [row["role"] for row in transcript] == ["user", "assistant"]
        assert transcript[0]["uuid"] == second_msg_id
        assert transcript[0]["content"] == "first\nsecond"
        assert transcript[1]["reply_to"] == second_msg_id
        assert fake.script_index == len(script)
    finally:
        cfg.batch_user_messages_llm_call_mode = original_mode
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_user_chat_background_tool_round_persists_side_effects() -> None:
    built = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.DUAL_LLM,
        SettledUserChatScriptScenario.DUAL_LLM_TOOL_BACKGROUND,
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=built.steps,
        bootstrap_completed=True,
    )
    try:
        output_queue = get_output_queue_for_scope(scope)
        batch_id = str(uuid.uuid4())
        user_msg_id = str(uuid.uuid4())
        user_batch = UserMessageBatch(
            batch_id=batch_id, message_ids=(user_msg_id,)
        )

        await manager.run_user_chat_turn(
            session,
            "what files do I have?",
            preset_user_msg_uuid=user_msg_id,
            agentic_output_queue=output_queue,
            user_message_batch=user_batch,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )

        ready = await output_queue.pull_ready_batch()
        assert built.expected_foreground_reply is not None
        assert [row.text for row in ready] == [built.expected_foreground_reply]
        transcript = scripted_transcript_rows(session.store)
        assert any(row.get("source") == "tool_bg" for row in transcript)
        assert any(
            TOOL_RESULTS_TRANSCRIPT_MARKER in str(row.get("content", ""))
            for row in transcript
        )
        done_rows = scripted_tool_background_done_rows(session.store)
        assert len(done_rows) == 1
        assert done_rows[0].get("kind") == "tool_background_done"
        assert done_rows[0].get("tool_calls_count") == 1
        assert fake.script_index == built.expected_step_count
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_bootstrap_turn_delivers_and_persists_context() -> None:
    script = (fake_step_text("Welcome! What kind of companion do you want?"),)
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
    )
    try:
        output_queue = get_output_queue_for_scope(scope)
        batch_id = str(uuid.uuid4())
        user_msg_id = str(uuid.uuid4())
        user_batch = UserMessageBatch(
            batch_id=batch_id, message_ids=(user_msg_id,)
        )

        result = await manager.run_user_chat_turn(
            session,
            "hi, I'm new here",
            preset_user_msg_uuid=user_msg_id,
            agentic_output_queue=output_queue,
            user_message_batch=user_batch,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )

        ready = await output_queue.pull_ready_batch()
        assert [row.text for row in ready] == [
            "Welcome! What kind of companion do you want?"
        ]
        assert result.assistant_text.strip() == (
            "Welcome! What kind of companion do you want?"
        )
        assert "user" in scripted_transcript_roles(session.store)
        assert "assistant" in scripted_transcript_roles(session.store)
        ctx_raw = session.store.read_document("context.json")
        ctx = json.loads(ctx_raw)
        assert (
            ctx.get("workspace_bootstrap_user_interactive_completed") is False
        )
        assert fake.script_index == 1
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_proactive_chat_silent_envelope_skips_assistant_transcript() -> (
    None
):
    script = (
        fake_step_proactive_chat_envelope(
            output_to_user=False,
            message="",
        ),
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        bootstrap_completed=True,
    )
    try:
        result = await manager.run_inner_tick_proactive_chat_turn(
            session,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )

        assert result.assistant_text == ""
        roles = scripted_transcript_roles(session.store)
        assert roles.count("user") == 1
        assert "assistant" not in roles
        assert fake.script_index == 1
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_proactive_chat_visible_then_silent_two_rounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two proactive inner ticks: visible round then structured silent (no assistant row)."""
    script = (
        fake_step_proactive_chat_envelope(
            output_to_user=True,
            message="First ping.",
        ),
        fake_step_proactive_chat_envelope(
            output_to_user=False,
            message="",
        ),
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        bootstrap_completed=True,
    )
    try:
        first = await manager.run_inner_tick_proactive_chat_turn(
            session,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )
        assert first.assistant_text == "First ping."

        monkeypatch.setattr(
            "app.core.companion_harness.companion.proactive_chat.next_proactive_chat_wait_seconds",
            lambda _store, _config, **_: 0.0,
        )

        second = await manager.run_inner_tick_proactive_chat_turn(
            session,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )
        assert second.assistant_text == ""

        transcript = scripted_transcript_rows(session.store)
        proactive_users = [
            row
            for row in transcript
            if row.get("role") == "user" and row.get("proactive_chat") is True
        ]
        assistant_rows = [
            row for row in transcript if row.get("role") == "assistant"
        ]
        assert len(proactive_users) == 2
        assert len(assistant_rows) == 1
        assert assistant_rows[0]["content"] == "First ping."
        assert fake.script_index == 2
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_proactive_chat_returns_assistant_text_and_transcript() -> None:
    script = (
        fake_step_proactive_chat_envelope(
            output_to_user=True,
            message="Just checking in on you.",
        ),
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        bootstrap_completed=True,
    )
    try:
        result = await manager.run_inner_tick_proactive_chat_turn(
            session,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )

        assert result.assistant_text.strip() == "Just checking in on you."
        roles = scripted_transcript_roles(session.store)
        assert "user" in roles
        assert "assistant" in roles
        assert fake.script_index == 1
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_monolog_inner_tick_scripted_transport_skips_foreground_and_appends_ai_private() -> (
    None
):
    """MONOLOG inner tick: async tool-background only, silent foreground, ai_private append."""
    monolog_text = "quiet worry about his silence"
    script = build_scripted_monolog_inner_tick_script(monolog_text=monolog_text)
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        bootstrap_completed=True,
    )
    try:
        seed_settled_scope_for_inner_tick(session.store)
        main_transcript_before = scripted_transcript_rows(session.store)

        result = await manager.run_inner_tick_monolog_turn(
            session,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )

        assert result.inner_tick_activity == InnerTickActivity.MONOLOG.value
        assert fake.script_index == len(script)

        thoughts = load_ai_private_thoughts(session.store)
        assert len(thoughts) == 1
        assert thoughts[0].text == monolog_text

        assert scripted_transcript_rows(session.store) == main_transcript_before

        inner_rows = scripted_inner_tick_transcript_rows(session.store)
        assert len(inner_rows) >= 1
        assert inner_rows[0]["role"] == "user"
        assert inner_rows[0].get("inner_tick") is True
    finally:
        await delete_guest_scope_for_test(scope)
