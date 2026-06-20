"""CI-gated harness orchestration tests using scripted FakeOpenAI transport."""

from __future__ import annotations

import json
import uuid

import pytest

from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    clear_output_queues_for_tests,
    get_output_queue_for_scope,
)
from app.core.companion_harness.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.manager import CompanionConfig, CompanionManager
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.memory.memory_registry import shutdown_all_memory_stores
from app.core.llms.client import CompanionLLMConfig
from app.external_services.fakes.openai import (
    FakeCompletionStep,
    FakeOpenAI,
    fake_step_dual_llm_envelope,
    fake_step_text,
    fake_step_tool_call,
)
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import DEEPSEEK_V3_2
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
    delete_guest_scope_for_test,
)
from tests.fixtures.companion_scripted_llm import (
    companion_llm_client_with_scripted_transport,
)


def _llm_config() -> CompanionLLMConfig:
    return CompanionLLMConfig(
        api_key="test-key",
        api_base="https://example.invalid/v1",
        default_model=DEEPSEEK_V3_2,
        chat_model=DEEPSEEK_V3_2,
        tool_model=DEEPSEEK_V3_2,
    )


async def _build_scripted_manager(
    *,
    script: tuple[FakeCompletionStep, ...],
    memory_bootstrap_type: str,
) -> tuple[CompanionManager, object, FakeOpenAI, AgentScope]:
    scope = await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="harn",
        meta_data={"test": "scripted_llm"},
    )
    llm_config = _llm_config()
    client, fake = companion_llm_client_with_scripted_transport(llm_config, script)
    config = CompanionConfig(
        llm=llm_config,
        memory_pg_dsn=companion_memory_registry_dsn(),
        memory_bootstrap_type=memory_bootstrap_type,
        langsmith_companion_parent_run_enabled=False,
    )
    manager = CompanionManager(config, llm_client=client)
    session = manager.get_or_create_session(
        scope.user_id,
        scope.agent_id,
        scope.memory_store_chat_id(),
    )
    return manager, session, fake, scope


def _transcript_roles(store: object) -> list[str]:
    raw = store.read_document("transcript.jsonl")
    rows = [
        json.loads(line)
        for line in raw.strip().splitlines()
        if line.strip()
    ]
    return [row["role"] for row in rows]


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
async def test_user_chat_no_tools_delivers_foreground_to_output_queue() -> None:
    script = (
        fake_step_text("Hi, I'm here."),
        fake_step_text(""),
    )
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
    )
    try:
        output_queue = get_output_queue_for_scope(scope)
        batch_id = str(uuid.uuid4())
        user_msg_id = str(uuid.uuid4())
        user_batch = UserMessageBatch(batch_id=batch_id, message_ids=(user_msg_id,))

        result = await manager.run_user_chat_turn(
            session,
            "hello",
            preset_user_msg_uuid=user_msg_id,
            agentic_output_queue=output_queue,
            user_message_batch=user_batch,
            runtime_context=TurnRuntimeContext(
                channel=CompanionRuntimeChannel.APP,
                implicit_signal_bundle=None,
            ),
        )

        ready = await output_queue.pull_ready_batch()
        texts = [row.text for row in ready]
        assert texts == ["Hi, I'm here."]
        assert result.assistant_text.strip() == "Hi, I'm here."
        assert _transcript_roles(session.store) == ["user", "assistant"]
        assert fake.script_index == len(script)
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_user_chat_background_tool_round_persists_side_effects() -> None:
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
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
    )
    try:
        output_queue = get_output_queue_for_scope(scope)
        batch_id = str(uuid.uuid4())
        user_msg_id = str(uuid.uuid4())
        user_batch = UserMessageBatch(batch_id=batch_id, message_ids=(user_msg_id,))

        await manager.run_user_chat_turn(
            session,
            "what files do I have?",
            preset_user_msg_uuid=user_msg_id,
            agentic_output_queue=output_queue,
            user_message_batch=user_batch,
            runtime_context=TurnRuntimeContext(
                channel=CompanionRuntimeChannel.APP,
                implicit_signal_bundle=None,
            ),
        )

        ready = await output_queue.pull_ready_batch()
        assert [row.text for row in ready] == ["I'll list your scope root."]
        roles = _transcript_roles(session.store)
        assert "user" in roles
        assert "assistant" in roles
        assert fake.script_index == len(script)
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_bootstrap_turn_delivers_and_persists_context() -> None:
    script = (fake_step_text("Welcome! What kind of companion do you want?"),)
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        memory_bootstrap_type=CompanionMemoryBootstrapType.USER_INTERACTIVE.value,
    )
    try:
        output_queue = get_output_queue_for_scope(scope)
        batch_id = str(uuid.uuid4())
        user_msg_id = str(uuid.uuid4())
        user_batch = UserMessageBatch(batch_id=batch_id, message_ids=(user_msg_id,))

        result = await manager.run_user_chat_turn(
            session,
            "hi, I'm new here",
            preset_user_msg_uuid=user_msg_id,
            agentic_output_queue=output_queue,
            user_message_batch=user_batch,
            runtime_context=TurnRuntimeContext(
                channel=CompanionRuntimeChannel.APP,
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
        assert "user" in _transcript_roles(session.store)
        assert "assistant" in _transcript_roles(session.store)
        ctx_raw = session.store.read_document("context.json")
        ctx = json.loads(ctx_raw)
        assert ctx.get("workspace_bootstrap_user_interactive_completed") is False
        assert fake.script_index == 1
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_proactive_chat_returns_assistant_text_and_transcript() -> None:
    script = (fake_step_text("Just checking in on you."),)
    manager, session, fake, scope = await _build_scripted_manager(
        script=script,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
    )
    try:
        result = await manager.run_inner_tick_proactive_chat_turn(
            session,
            runtime_context=TurnRuntimeContext(
                channel=CompanionRuntimeChannel.APP,
                implicit_signal_bundle=None,
            ),
        )

        assert result.assistant_text.strip() == "Just checking in on you."
        roles = _transcript_roles(session.store)
        assert "user" in roles
        assert "assistant" in roles
        assert fake.script_index == 1
    finally:
        await delete_guest_scope_for_test(scope)
