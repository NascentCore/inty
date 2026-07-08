"""CI-gated headless drain_once tests with scripted FakeOpenAI transport.

Covered: settled ``USER_CHAT`` drain (no-tools x ``dual_llm`` + ``in_turn_single_llm``;
tool-bg and silent-foreground OutputQueue-skip ``dual_llm`` only), bootstrap, batch smokes.

Excluded (documented): autonomy (#3580), dreaming, proactive+tool (#3285),
sequential back-to-back drain (TODO). Script sizing via ``build_scripted_settled_user_chat_script``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.companion import (
    AgenticCompanion,
)
from app.core.companion_harness.agentic_companion.output_queue import (
    clear_output_queues_for_tests,
    get_output_queue_for_scope,
)
from app.core.companion_harness.agentic_companion.postgres_queue import (
    PostgresInputQueueRepository,
)
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
    OutputMessageKind,
    QueueStatus,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.scope_turn_lock import (
    get_scope_tool_bg_idle,
)
from app.core.companion_harness.loop.config import (
    BatchUserMessagesLlmCallMode,
    UserTurnLlmLoopMode,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.core.companion_harness.memory.memory_registry import (
    shutdown_all_memory_stores,
)
from app.core.companion_harness.tools.tool_background import (
    TOOL_RESULTS_TRANSCRIPT_MARKER,
)
from app.db.session import AsyncSessionLocal
from app.external_services.fakes.openai import fake_step_text
from app.models.agent import Agent
from app.models.agentic_companion_queue import (
    AgenticCompanionInputQueueRow,
    AgenticCompanionOutputQueueRow,
)
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.models_catalog import DEEPSEEK_V3_2
from tests.app.core.companion_harness.companion.bootstrap_test_helpers import (
    mark_interactive_bootstrap_completed,
)
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    SettledUserChatScriptScenario,
    build_scripted_injected_runtime,
    build_scripted_settled_user_chat_script,
    memory_store_for_injected_runtime,
    scripted_tool_background_done_rows,
    scripted_transcript_roles,
    scripted_transcript_rows,
    with_scripted_user_turn_llm_loop_mode,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
)


def _implicit_bundle() -> ImplicitSignalBundle:
    return ImplicitSignalBundle(
        client_time=None,
        user_signed_on=False,
        server_received_at_utc=datetime.now(UTC),
    )


def _seed_settled_store_for_drain(
    scope: AgentScope,
    injected: object,
) -> None:
    """Mark bootstrap complete so drain exercises settled ``USER_CHAT`` track."""
    mark_interactive_bootstrap_completed(
        memory_store_for_injected_runtime(scope, injected)  # type: ignore[arg-type]
    )


async def _cleanup_guest_scope_with_queues(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgenticCompanionInputQueueRow).where(
                AgenticCompanionInputQueueRow.user_id == scope.user_id
            )
        )
        await db.execute(
            delete(AgenticCompanionOutputQueueRow).where(
                AgenticCompanionOutputQueueRow.user_id == scope.user_id
            )
        )
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == scope.user_id)
        )
        await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
        await db.execute(delete(User).where(User.id == scope.user_id))
        await db.commit()


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
async def test_drain_user_chat_no_tools_delivers_foreground(
    llm_loop_mode: UserTurnLlmLoopMode,
) -> None:
    built = build_scripted_settled_user_chat_script(
        llm_loop_mode,
        SettledUserChatScriptScenario.NO_TOOLS,
    )
    injected, fake = build_scripted_injected_runtime(built.steps)
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="drain_script",
        meta_data={"test": "scripted_drain"},
    )
    try:
        _seed_settled_store_for_drain(scope, injected)
        with with_scripted_user_turn_llm_loop_mode(llm_loop_mode):
            now = datetime.now(UTC)
            async with AsyncSessionLocal() as db:
                input_repo = PostgresInputQueueRepository(db)
                await input_repo.append_user_message(
                    InboundWireMessage(
                        scope=scope,
                        channel=ChannelKind.APP_WS,
                        wire_id="wire-drain-no-tool",
                        text="hello",
                        received_at_utc=now,
                    )
                )
                await db.commit()

            async with AsyncSessionLocal() as db:
                companion = AgenticCompanion(
                    scope=scope,
                    input_repo=PostgresInputQueueRepository(db),
                )
                result = await companion.drain_once(
                    resolved_chat_model=DEEPSEEK_V3_2,
                    runtime_channel=ChannelKind.APP_WS,
                    implicit_signal_bundle=_implicit_bundle(),
                    injected_runtime=injected,
                )
                await db.commit()

            assert result is not None
            assert built.expected_foreground_reply is not None
            assert (
                result.assistant_text.strip() == built.expected_foreground_reply
            )

            output_queue = get_output_queue_for_scope(scope)
            ready = await output_queue.pull_ready_batch()
            assert [row.text for row in ready] == [
                built.expected_foreground_reply
            ]

            async with AsyncSessionLocal() as db:
                input_rows = (
                    (
                        await db.execute(
                            select(AgenticCompanionInputQueueRow).where(
                                AgenticCompanionInputQueueRow.user_id
                                == scope.user_id,
                                AgenticCompanionInputQueueRow.agent_id
                                == scope.agent_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                output_rows = (
                    (
                        await db.execute(
                            select(AgenticCompanionOutputQueueRow).where(
                                AgenticCompanionOutputQueueRow.user_id
                                == scope.user_id,
                                AgenticCompanionOutputQueueRow.agent_id
                                == scope.agent_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

            assert len(input_rows) == 1
            assert input_rows[0].status == QueueStatus.DELIVERED.value
            assert len(output_rows) >= 1
            assert any(
                row.text == built.expected_foreground_reply
                for row in output_rows
            )

            store = memory_store_for_injected_runtime(scope, injected)
            roles = scripted_transcript_roles(store)
            assert "user" in roles
            assert "assistant" in roles
            assert fake.script_index == built.expected_step_count
    finally:
        await _cleanup_guest_scope_with_queues(scope)


@pytest.mark.asyncio
async def test_drain_user_chat_background_tool_round() -> None:
    built = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.DUAL_LLM,
        SettledUserChatScriptScenario.DUAL_LLM_TOOL_BACKGROUND,
    )
    injected, fake = build_scripted_injected_runtime(built.steps)
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="drain_tool_bg",
        meta_data={"test": "scripted_drain_tool_bg"},
    )
    try:
        _seed_settled_store_for_drain(scope, injected)
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=ChannelKind.APP_WS,
                    wire_id="wire-drain-tool-bg",
                    text="what files do I have?",
                    received_at_utc=now,
                )
            )
            await db.commit()

        async with AsyncSessionLocal() as db:
            companion = AgenticCompanion(
                scope=scope,
                input_repo=PostgresInputQueueRepository(db),
            )
            await companion.drain_once(
                resolved_chat_model=DEEPSEEK_V3_2,
                runtime_channel=ChannelKind.APP_WS,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        output_queue = get_output_queue_for_scope(scope)
        ready = await output_queue.pull_ready_batch()
        assert built.expected_foreground_reply is not None
        assert [row.text for row in ready] == [built.expected_foreground_reply]

        store = memory_store_for_injected_runtime(scope, injected)
        transcript = scripted_transcript_rows(store)
        assert any(row.get("source") == "tool_bg" for row in transcript)
        assert any(
            TOOL_RESULTS_TRANSCRIPT_MARKER in str(row.get("content", ""))
            for row in transcript
        )
        done_rows = scripted_tool_background_done_rows(store)
        assert len(done_rows) == 1
        assert done_rows[0].get("kind") == "tool_background_done"
        assert done_rows[0].get("tool_calls_count") == 1
        assert fake.script_index == built.expected_step_count
    finally:
        await _cleanup_guest_scope_with_queues(scope)


@pytest.mark.asyncio
async def test_drain_dual_llm_silent_fg_delivers_tool_background_on_finish() -> (
    None
):
    built = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.DUAL_LLM,
        SettledUserChatScriptScenario.DUAL_LLM_SILENT_FOREGROUND_TOOL_BG,
    )
    injected, fake = build_scripted_injected_runtime(built.steps)
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="drain_silent_fg",
        meta_data={"test": "scripted_drain_silent_fg_tool_bg"},
    )
    try:
        _seed_settled_store_for_drain(scope, injected)
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=ChannelKind.APP_WS,
                    wire_id="wire-silent-fg",
                    text="trigger tools",
                    received_at_utc=now,
                )
            )
            await db.commit()

        async with AsyncSessionLocal() as db:
            companion = AgenticCompanion(
                scope=scope,
                input_repo=PostgresInputQueueRepository(db),
            )
            result = await companion.drain_once(
                resolved_chat_model=DEEPSEEK_V3_2,
                runtime_channel=ChannelKind.APP_WS,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        assert result is not None
        assert result.tool_background_started is True

        output_queue = get_output_queue_for_scope(scope)
        ready = await output_queue.pull_ready_batch()
        assert len(ready) == 1
        assert ready[0].kind == OutputMessageKind.TOOL_BACKGROUND
        assert ready[0].text == "Listing complete."

        async with AsyncSessionLocal() as db:
            input_rows = (
                (
                    await db.execute(
                        select(AgenticCompanionInputQueueRow).where(
                            AgenticCompanionInputQueueRow.user_id
                            == scope.user_id,
                            AgenticCompanionInputQueueRow.agent_id
                            == scope.agent_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            output_rows = (
                (
                    await db.execute(
                        select(AgenticCompanionOutputQueueRow).where(
                            AgenticCompanionOutputQueueRow.user_id
                            == scope.user_id,
                            AgenticCompanionOutputQueueRow.agent_id
                            == scope.agent_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert len(input_rows) == 1
        assert input_rows[0].status == QueueStatus.DELIVERED.value
        assert len(output_rows) == 1
        assert output_rows[0].kind == OutputMessageKind.TOOL_BACKGROUND.value
        assert fake.script_index == built.expected_step_count
    finally:
        await _cleanup_guest_scope_with_queues(scope)


@pytest.mark.asyncio
async def test_burst_user_messages_during_tool_bg() -> None:
    """Back-to-back USER_CHAT drains complete while tool_bg_idle stays cleared (#3123)."""
    tool_bg_script = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.DUAL_LLM,
        SettledUserChatScriptScenario.DUAL_LLM_TOOL_BACKGROUND,
    )
    follow_up_script = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.DUAL_LLM,
        SettledUserChatScriptScenario.NO_TOOLS,
    )
    injected, fake = build_scripted_injected_runtime(
        tool_bg_script.steps + follow_up_script.steps
    )
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="drain_burst",
        meta_data={"test": "scripted_burst_tool_bg"},
    )
    try:
        _seed_settled_store_for_drain(scope, injected)
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=ChannelKind.APP_WS,
                    wire_id="wire-burst-1",
                    text="first",
                    received_at_utc=now,
                )
            )
            await db.commit()

        companion_scope = CompanionScope(
            scope.user_id,
            scope.agent_id,
            scope.memory_store_chat_id(),
        )
        idle = get_scope_tool_bg_idle(companion_scope)
        idle.clear()

        async with AsyncSessionLocal() as db:
            companion = AgenticCompanion(
                scope=scope,
                input_repo=PostgresInputQueueRepository(db),
            )
            first = await companion.drain_once(
                resolved_chat_model=DEEPSEEK_V3_2,
                runtime_channel=ChannelKind.APP_WS,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        assert first is not None
        assert not idle.is_set()

        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=ChannelKind.APP_WS,
                    wire_id="wire-burst-2",
                    text="second",
                    received_at_utc=now,
                )
            )
            await db.commit()

        idle.clear()

        async with AsyncSessionLocal() as db:
            companion = AgenticCompanion(
                scope=scope,
                input_repo=PostgresInputQueueRepository(db),
            )
            second = await companion.drain_once(
                resolved_chat_model=DEEPSEEK_V3_2,
                runtime_channel=ChannelKind.APP_WS,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        assert second is not None
        assert (
            second.assistant_text.strip()
            == follow_up_script.expected_foreground_reply
        )
        assert fake.script_index == (
            tool_bg_script.expected_step_count
            + follow_up_script.expected_step_count
        )
    finally:
        await _cleanup_guest_scope_with_queues(scope)


@pytest.mark.asyncio
async def test_drain_empty_input_queue_returns_none() -> None:
    injected, fake = build_scripted_injected_runtime(
        (fake_step_text("unused"), fake_step_text("")),
    )
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="drain_empty",
        meta_data={"test": "scripted_drain_empty"},
    )
    try:
        async with AsyncSessionLocal() as db:
            companion = AgenticCompanion(
                scope=scope,
                input_repo=PostgresInputQueueRepository(db),
            )
            result = await companion.drain_once(
                resolved_chat_model=DEEPSEEK_V3_2,
                runtime_channel=ChannelKind.APP_WS,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        assert result is None
        assert fake.script_index == 0
    finally:
        await _cleanup_guest_scope_with_queues(scope)


@pytest.mark.asyncio
async def test_drain_multi_message_batch_merges_user_text() -> None:
    script = (
        fake_step_text("Got both lines."),
        fake_step_text(""),
    )
    injected, fake = build_scripted_injected_runtime(script)
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="drain_batch",
        meta_data={"test": "scripted_drain_batch"},
    )
    cfg = (
        global_config_loaded_from_config_yaml.agent.companion_harness.user_turn
    )
    original_mode = cfg.batch_user_messages_llm_call_mode
    cfg.batch_user_messages_llm_call_mode = (
        BatchUserMessagesLlmCallMode.JOIN_TO_ONE_USER_MESSAGE.value
    )
    try:
        _seed_settled_store_for_drain(scope, injected)
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=ChannelKind.APP_WS,
                    wire_id="wire-batch",
                    text="line one",
                    received_at_utc=now,
                )
            )
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=ChannelKind.APP_WS,
                    wire_id="wire-batch",
                    text="line two",
                    received_at_utc=now,
                )
            )
            await db.commit()

        async with AsyncSessionLocal() as db:
            companion = AgenticCompanion(
                scope=scope,
                input_repo=PostgresInputQueueRepository(db),
            )
            result = await companion.drain_once(
                resolved_chat_model=DEEPSEEK_V3_2,
                runtime_channel=ChannelKind.APP_WS,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        assert result is not None
        assert len(result.input_message_ids) == 2

        async with AsyncSessionLocal() as db:
            input_rows = (
                (
                    await db.execute(
                        select(AgenticCompanionInputQueueRow).where(
                            AgenticCompanionInputQueueRow.user_id
                            == scope.user_id,
                            AgenticCompanionInputQueueRow.agent_id
                            == scope.agent_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert len(input_rows) == 2
        assert all(
            row.status == QueueStatus.DELIVERED.value for row in input_rows
        )

        store = memory_store_for_injected_runtime(scope, injected)
        user_rows = [
            row
            for row in scripted_transcript_rows(store)
            if row.get("role") == "user"
        ]
        assert len(user_rows) == 1
        assert user_rows[0].get("content") == "line one\nline two"
        assert fake.script_index == len(script)
    finally:
        cfg.batch_user_messages_llm_call_mode = original_mode
        await _cleanup_guest_scope_with_queues(scope)


@pytest.mark.asyncio
async def test_drain_bootstrap_turn_persists_interactive_context() -> None:
    script = (fake_step_text("Welcome! What kind of companion do you want?"),)
    injected, fake = build_scripted_injected_runtime(
        script,
    )
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.APP_WS,
        nickname_prefix="drain_bootstrap",
        meta_data={"test": "scripted_drain_bootstrap"},
    )
    try:
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=ChannelKind.APP_WS,
                    wire_id="wire-bootstrap",
                    text="hi, I'm new here",
                    received_at_utc=now,
                )
            )
            await db.commit()

        async with AsyncSessionLocal() as db:
            companion = AgenticCompanion(
                scope=scope,
                input_repo=PostgresInputQueueRepository(db),
            )
            result = await companion.drain_once(
                resolved_chat_model=DEEPSEEK_V3_2,
                runtime_channel=ChannelKind.APP_WS,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        assert result is not None
        assert result.assistant_text.strip() == (
            "Welcome! What kind of companion do you want?"
        )

        output_queue = get_output_queue_for_scope(scope)
        ready = await output_queue.pull_ready_batch()
        assert [row.text for row in ready] == [
            "Welcome! What kind of companion do you want?"
        ]

        store = memory_store_for_injected_runtime(scope, injected)
        assert "user" in scripted_transcript_roles(store)
        assert "assistant" in scripted_transcript_roles(store)
        ctx = json.loads(store.read_document("context.json"))
        assert (
            ctx.get("workspace_bootstrap_user_interactive_completed") is False
        )
        assert fake.script_index == 1
    finally:
        await _cleanup_guest_scope_with_queues(scope)
