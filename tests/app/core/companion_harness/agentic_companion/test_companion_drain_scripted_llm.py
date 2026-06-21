"""CI-gated headless drain_once tests with scripted FakeOpenAI transport.

Script step counts assume default ``user_turn.llm_loop_mode=dual_llm``:
- No-tool USER_CHAT: 2 steps (reply + empty routing)
- Tool-bg round: 4 steps (see #3559 orchestration test)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
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
    QueueStatus,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.memory.memory_registry import shutdown_all_memory_stores
from app.core.companion_harness.tools.tool_background import (
    TOOL_RESULTS_TRANSCRIPT_MARKER,
)
from app.db.session import AsyncSessionLocal
from app.external_services.fakes.openai import (
    fake_step_dual_llm_envelope,
    fake_step_text,
    fake_step_tool_call,
)
from app.models.agent import Agent
from app.models.agentic_companion_queue import (
    AgenticCompanionInputQueueRow,
    AgenticCompanionOutputQueueRow,
)
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.models_catalog import DEEPSEEK_V3_2
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    build_scripted_injected_runtime,
    memory_store_for_injected_runtime,
    scripted_tool_background_done_rows,
    scripted_transcript_roles,
    scripted_transcript_rows,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
)


def _implicit_bundle() -> ImplicitSignalBundle:
    return ImplicitSignalBundle(
        client_time=None,
        user_signed_on=False,
        server_received_at_utc=datetime.now(timezone.utc),
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
async def test_drain_user_chat_no_tools_delivers_foreground() -> None:
    script = (
        fake_step_text("Hi, I'm here."),
        fake_step_text(""),
    )
    injected, fake = build_scripted_injected_runtime(script)
    scope = await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="drain_script",
        meta_data={"test": "scripted_drain"},
    )
    try:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=CompanionRuntimeChannel.APP,
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
                runtime_channel=CompanionRuntimeChannel.APP,
                background_output_sink=None,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        assert result is not None
        assert result.assistant_text.strip() == "Hi, I'm here."

        output_queue = get_output_queue_for_scope(scope)
        ready = await output_queue.pull_ready_batch()
        assert [row.text for row in ready] == ["Hi, I'm here."]

        async with AsyncSessionLocal() as db:
            input_rows = (
                (
                    await db.execute(
                        select(AgenticCompanionInputQueueRow).where(
                            AgenticCompanionInputQueueRow.user_id == scope.user_id,
                            AgenticCompanionInputQueueRow.agent_id == scope.agent_id,
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
                            AgenticCompanionOutputQueueRow.user_id == scope.user_id,
                            AgenticCompanionOutputQueueRow.agent_id == scope.agent_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert len(input_rows) == 1
        assert input_rows[0].status == QueueStatus.DELIVERED.value
        assert len(output_rows) >= 1
        assert any(row.text == "Hi, I'm here." for row in output_rows)

        store = memory_store_for_injected_runtime(scope, injected)
        roles = scripted_transcript_roles(store)
        assert "user" in roles
        assert "assistant" in roles
        assert fake.script_index == len(script)
    finally:
        await _cleanup_guest_scope_with_queues(scope)


@pytest.mark.asyncio
async def test_drain_user_chat_background_tool_round() -> None:
    script = (
        fake_step_text("I'll list your scope root."),
        fake_step_tool_call(
            "memory_store_list_paths",
            '{"relative_path": ""}',
            tool_call_id="call_list_paths",
        ),
        fake_step_dual_llm_envelope(
            user_facing_reply="Listing complete.",
            output_to_user=False,
            importance_round=5,
            importance_user_message=5,
            importance_assistant_message=5,
            turn_recall="",
        ),
    )
    injected, fake = build_scripted_injected_runtime(script)
    scope = await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="drain_tool_bg",
        meta_data={"test": "scripted_drain_tool_bg"},
    )
    try:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=CompanionRuntimeChannel.APP,
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
                runtime_channel=CompanionRuntimeChannel.APP,
                background_output_sink=None,
                implicit_signal_bundle=_implicit_bundle(),
                injected_runtime=injected,
            )
            await db.commit()

        output_queue = get_output_queue_for_scope(scope)
        ready = await output_queue.pull_ready_batch()
        assert [row.text for row in ready] == ["I'll list your scope root."]

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
        assert fake.script_index == len(script)
    finally:
        await _cleanup_guest_scope_with_queues(scope)
