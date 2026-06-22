"""Wire a real LlmClient to one shared scripted FakeOpenAI for harness tests.

Settled ``USER_CHAT`` script shapes are centralized in
``build_scripted_settled_user_chat_script`` keyed on ``UserTurnLlmLoopMode``.

Excluded from scripted coverage here (see orchestration/drain module docstrings):
monolog/autonomy (#3580), dreaming, proactive+tool (#3285), sequential double-drain.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.turn import (
    InjectedCompanionRuntime,
)
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
)
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.config import global_config_loaded_from_config_yaml
from app.core.llms.client import CompanionLLMConfig, LlmClient
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

_DEFAULT_NO_TOOLS_REPLY = "Hi, I'm here."
_DEFAULT_TOOL_FG_REPLY = "I'll list your scope root."
_DEFAULT_TOOL_CALL_ID = "call_list_paths"
_DEFAULT_IMPORTANCE = 5


class SettledUserChatScriptScenario(StrEnum):
    """Which settled USER_CHAT FakeOpenAI script shape to build."""

    NO_TOOLS = "no_tools"
    DUAL_LLM_TOOL_BACKGROUND = "dual_llm_tool_background"
    DUAL_LLM_SILENT_FOREGROUND_TOOL_BG = "dual_llm_silent_foreground_tool_bg"


@dataclass(frozen=True)
class ScriptedSettledUserChatScript:
    """One deterministic FakeOpenAI script for a settled USER_CHAT integration test.

    ``steps`` is consumed sequentially by every LLM call in the turn.
    ``expected_step_count`` is asserted via ``fake.script_index`` exhaustion checks.
    """

    mode: UserTurnLlmLoopMode
    scenario: SettledUserChatScriptScenario
    steps: tuple[FakeCompletionStep, ...]
    expected_step_count: int
    expected_foreground_reply: str | None


def scripted_harness_llm_config() -> CompanionLLMConfig:
    return CompanionLLMConfig(
        api_key="test-key",
        api_base="https://example.invalid/v1",
        default_model=DEEPSEEK_V3_2,
        chat_model=DEEPSEEK_V3_2,
        tool_model=DEEPSEEK_V3_2,
    )


def build_scripted_settled_user_chat_script(
    mode: UserTurnLlmLoopMode,
    scenario: SettledUserChatScriptScenario,
) -> ScriptedSettledUserChatScript:
    """Return FakeOpenAI steps sized for the given loop mode and USER_CHAT scenario."""
    match scenario:
        case SettledUserChatScriptScenario.NO_TOOLS:
            return _no_tools_script(mode)
        case SettledUserChatScriptScenario.DUAL_LLM_TOOL_BACKGROUND:
            assert mode == UserTurnLlmLoopMode.DUAL_LLM
            return _dual_llm_tool_background_script()
        case SettledUserChatScriptScenario.DUAL_LLM_SILENT_FOREGROUND_TOOL_BG:
            assert mode == UserTurnLlmLoopMode.DUAL_LLM
            return _dual_llm_silent_foreground_tool_bg_script()


def _no_tools_script(
    mode: UserTurnLlmLoopMode,
) -> ScriptedSettledUserChatScript:
    reply = _DEFAULT_NO_TOOLS_REPLY
    match mode:
        case UserTurnLlmLoopMode.DUAL_LLM:
            steps = (
                fake_step_text(reply),
                fake_step_text(""),
            )
        case UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM:
            steps = (fake_step_text(reply),)
    return ScriptedSettledUserChatScript(
        mode=mode,
        scenario=SettledUserChatScriptScenario.NO_TOOLS,
        steps=steps,
        expected_step_count=len(steps),
        expected_foreground_reply=reply,
    )


def _dual_llm_tool_background_script() -> ScriptedSettledUserChatScript:
    fg_reply = _DEFAULT_TOOL_FG_REPLY
    steps = (
        fake_step_text(fg_reply),
        fake_step_tool_call(
            "memory_store_list_paths",
            '{"relative_path": ""}',
            tool_call_id=_DEFAULT_TOOL_CALL_ID,
        ),
        fake_step_dual_llm_envelope(
            user_facing_reply="Listing complete.",
            output_to_user=False,
            importance_round=_DEFAULT_IMPORTANCE,
            importance_user_message=_DEFAULT_IMPORTANCE,
            importance_assistant_message=_DEFAULT_IMPORTANCE,
            turn_recall="",
        ),
    )
    return ScriptedSettledUserChatScript(
        mode=UserTurnLlmLoopMode.DUAL_LLM,
        scenario=SettledUserChatScriptScenario.DUAL_LLM_TOOL_BACKGROUND,
        steps=steps,
        expected_step_count=len(steps),
        expected_foreground_reply=fg_reply,
    )


def _dual_llm_silent_foreground_tool_bg_script() -> (
    ScriptedSettledUserChatScript
):
    steps = (
        fake_step_dual_llm_envelope(
            user_facing_reply="",
            output_to_user=False,
            importance_round=_DEFAULT_IMPORTANCE,
            importance_user_message=_DEFAULT_IMPORTANCE,
            importance_assistant_message=_DEFAULT_IMPORTANCE,
            turn_recall="",
        ),
        fake_step_tool_call(
            "memory_store_list_paths",
            '{"relative_path": ""}',
            tool_call_id=_DEFAULT_TOOL_CALL_ID,
        ),
        fake_step_dual_llm_envelope(
            user_facing_reply="Listing complete.",
            output_to_user=False,
            importance_round=_DEFAULT_IMPORTANCE,
            importance_user_message=_DEFAULT_IMPORTANCE,
            importance_assistant_message=_DEFAULT_IMPORTANCE,
            turn_recall="",
        ),
    )
    return ScriptedSettledUserChatScript(
        mode=UserTurnLlmLoopMode.DUAL_LLM,
        scenario=SettledUserChatScriptScenario.DUAL_LLM_SILENT_FOREGROUND_TOOL_BG,
        steps=steps,
        expected_step_count=len(steps),
        expected_foreground_reply=None,
    )


@contextmanager
def with_scripted_user_turn_llm_loop_mode(
    mode: UserTurnLlmLoopMode,
) -> Iterator[None]:
    """Temporarily override ``user_turn.llm_loop_mode`` for one scripted test."""
    cfg = (
        global_config_loaded_from_config_yaml.agent.companion_harness.user_turn
    )
    original = cfg.llm_loop_mode
    cfg.llm_loop_mode = mode.value
    try:
        yield
    finally:
        cfg.llm_loop_mode = original


def companion_llm_client_with_scripted_transport(
    config: CompanionLLMConfig,
    script: tuple[FakeCompletionStep, ...],
) -> tuple[LlmClient, FakeOpenAI]:
    """Return real LlmClient with one shared FakeOpenAI on all sync+async routes."""
    client = LlmClient(config)
    fake = FakeOpenAI(script=script)
    client._client = fake  # noqa: SLF001
    client._client_dual_chat = fake  # noqa: SLF001
    client._client_dual_tool = fake  # noqa: SLF001
    client._client_inner_tick = fake  # noqa: SLF001
    async_client = client.async_llm_client
    async_client._async_client = fake.async_client  # noqa: SLF001
    return client, fake


def build_scripted_injected_runtime(
    script: tuple[FakeCompletionStep, ...],
    *,
    memory_bootstrap_type: str = CompanionMemoryBootstrapType.NONE.value,
) -> tuple[InjectedCompanionRuntime, FakeOpenAI]:
    """Build test ``InjectedCompanionRuntime`` with scripted transport and bootstrap mode."""
    llm_config = scripted_harness_llm_config()
    client, fake = companion_llm_client_with_scripted_transport(
        llm_config, script
    )
    companion_config = CompanionConfig(
        llm=llm_config,
        memory_pg_dsn=companion_memory_registry_dsn(),
        memory_bootstrap_type=memory_bootstrap_type,
        langsmith_companion_parent_run_enabled=False,
    )
    injected = InjectedCompanionRuntime(
        companion_config=companion_config,
        llm_client=client,
    )
    return injected, fake


def memory_store_for_injected_runtime(
    scope: AgentScope,
    injected: InjectedCompanionRuntime,
) -> MemoryStore:
    """Read MemoryStore for a scope after a turn using the same injected config."""
    manager = CompanionManager(
        injected.companion_config,
        llm_client=injected.llm_client,
    )
    return manager.get_or_create_session(
        scope.user_id,
        scope.agent_id,
        scope.memory_store_chat_id(),
    ).store


def scripted_transcript_roles(store: MemoryStore) -> list[str]:
    raw = store.read_document("transcript.jsonl")
    rows = [
        json.loads(line) for line in raw.strip().splitlines() if line.strip()
    ]
    return [row["role"] for row in rows]


def scripted_transcript_rows(store: MemoryStore) -> list[dict[str, object]]:
    raw = store.read_document("transcript.jsonl")
    return [
        json.loads(line) for line in raw.strip().splitlines() if line.strip()
    ]


def scripted_tool_background_done_rows(
    store: MemoryStore,
) -> list[dict[str, object]]:
    raw = store.read_document("tool_background.jsonl")
    return [
        json.loads(line) for line in raw.strip().splitlines() if line.strip()
    ]


def assert_all_routes_share_fake(client: LlmClient, fake: FakeOpenAI) -> None:
    """Assert every route slot points at the same scripted FakeOpenAI instance."""
    assert client._client is fake  # noqa: SLF001
    assert client._client_dual_chat is fake  # noqa: SLF001
    assert client._client_dual_tool is fake  # noqa: SLF001
    assert client._client_inner_tick is fake  # noqa: SLF001
    assert (
        client.async_llm_client._async_client is fake.async_client
    )  # noqa: SLF001
