"""Wire a real LlmClient to one shared scripted FakeOpenAI for harness tests.

Settled ``USER_CHAT`` script shapes are centralized in
``build_scripted_settled_user_chat_script`` keyed on ``UserTurnLlmLoopMode``.

Excluded from scripted coverage here (see orchestration/drain module docstrings):
dreaming, proactive+tool (#3285), sequential double-drain.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.agentic_companion.turn import (
    InjectedCompanionRuntime,
)
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
)
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
    IDENTITY_MD_REL,
    LIFE_CURRENTS_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    USER_MD_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

_SCOPE_PATHS = DEFAULT_MEMORY_STORE_SCOPE_PATHS
from app.core.config import global_config_loaded_from_config_yaml
from app.core.llms.client import CompanionLLMConfig, LlmClient
from app.external_services.fakes.openai import (
    FakeCompletionStep,
    FakeOpenAI,
    fake_step_dual_llm_envelope,
    fake_step_text,
    fake_step_tool_call,
)
from app.utils.models_catalog import DEEPSEEK_V3_2
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)

_DEFAULT_NO_TOOLS_REPLY = "Hi, I'm here."
_DEFAULT_TOOL_FG_REPLY = "I'll list your scope root."
_DEFAULT_TOOL_CALL_ID = "call_list_paths"
_DEFAULT_IMPORTANCE = 5
_DEFAULT_MONOLOG_TEXT = "quiet worry about his silence"
_DEFAULT_MONOLOG_TOOL_CALL_ID = "call_monolog_ai_private_1"
_DEFAULT_AUTONOMY_LIFE_CURRENTS_BODY = "# Life currents\nQuiet evening sketch."
_DEFAULT_AUTONOMY_TOOL_CALL_ID = "call_autonomy_life_currents_1"


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


class UnusedLlmClient:
    """LlmClient stand-in for sequential-mode dreaming tests: any call fails."""

    def chat_completion_unified(self, **_kwargs: object) -> object:
        raise AssertionError("llm_client must not be called in sequential mode")

    def resolve_model(self, _role: str) -> object:
        raise AssertionError("llm_client must not be called in sequential mode")


def scripted_harness_llm_config() -> CompanionLLMConfig:
    return CompanionLLMConfig(
        api_key="test-key",
        api_base="https://example.invalid/v1",
        default_model=DEEPSEEK_V3_2,
        chat_model=DEEPSEEK_V3_2,
        tool_model=DEEPSEEK_V3_2,
    )


def build_scripted_monolog_inner_tick_script(
    *,
    monolog_text: str = _DEFAULT_MONOLOG_TEXT,
) -> tuple[FakeCompletionStep, ...]:
    """Deterministic FakeOpenAI script for one ``INNER_TICK_MONOLOG`` tool-background turn."""
    return (
        fake_step_tool_call(
            "ai_private_append",
            json.dumps({"text": monolog_text}, ensure_ascii=False),
            tool_call_id=_DEFAULT_MONOLOG_TOOL_CALL_ID,
        ),
        fake_step_dual_llm_envelope(
            user_facing_reply="",
            output_to_user=False,
            importance_round=_DEFAULT_IMPORTANCE,
            importance_user_message=_DEFAULT_IMPORTANCE,
            importance_assistant_message=_DEFAULT_IMPORTANCE,
            turn_recall="",
        ),
    )


def build_scripted_autonomy_inner_tick_script(
    *,
    life_currents_body: str = _DEFAULT_AUTONOMY_LIFE_CURRENTS_BODY,
) -> tuple[FakeCompletionStep, ...]:
    """Deterministic FakeOpenAI script for one ``INNER_TICK_AUTONOMY`` inline tool turn."""
    return (
        fake_step_tool_call(
            "memory_store_write_document",
            json.dumps(
                {
                    "relative_path": LIFE_CURRENTS_MD_REL,
                    "content": life_currents_body,
                },
                ensure_ascii=False,
            ),
            tool_call_id=_DEFAULT_AUTONOMY_TOOL_CALL_ID,
        ),
        fake_step_dual_llm_envelope(
            user_facing_reply="",
            output_to_user=False,
            importance_round=_DEFAULT_IMPORTANCE,
            importance_user_message=_DEFAULT_IMPORTANCE,
            importance_assistant_message=_DEFAULT_IMPORTANCE,
            turn_recall="",
        ),
    )


def seed_settled_scope_for_inner_tick(store: MemoryStore) -> None:
    """Seed MemoryStore for settled inner-tick turns (bootstrap done, min transcript)."""
    store.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    for rel in (IDENTITY_MD_REL, SOUL_MD_REL, USER_MD_REL, MEMORY_MD_REL, STYLE_MD_REL):
        store.write_document(rel, f"# {rel}\n")
    store.write_document(
        _SCOPE_PATHS.transcript,
        "\n".join(
            [
                json.dumps(
                    {
                        "role": "user",
                        "content": "hello",
                        "ts": "2026-01-01T00:00:00Z",
                        "uuid": "user-seed-1",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "content": "hi there",
                        "ts": "2026-01-01T00:00:01Z",
                        "uuid": "asst-seed-1",
                        "reply_to": "user-seed-1",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
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
            output_to_user=True,
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
) -> tuple[InjectedCompanionRuntime, FakeOpenAI]:
    """Build test ``InjectedCompanionRuntime`` with scripted transport."""
    llm_config = scripted_harness_llm_config()
    client, fake = companion_llm_client_with_scripted_transport(
        llm_config, script
    )
    companion_config = CompanionConfig(
        llm=llm_config,
        memory_pg_dsn=companion_memory_registry_dsn(),
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
    raw = store.read_document(_SCOPE_PATHS.transcript)
    rows = [
        json.loads(line) for line in raw.strip().splitlines() if line.strip()
    ]
    return [row["role"] for row in rows]


def scripted_transcript_rows(store: MemoryStore) -> list[dict[str, object]]:
    raw = store.read_document(_SCOPE_PATHS.transcript)
    return [
        json.loads(line) for line in raw.strip().splitlines() if line.strip()
    ]


def scripted_inner_tick_transcript_rows(
    store: MemoryStore,
) -> list[dict[str, object]]:
    raw = store.read_document(_SCOPE_PATHS.transcript_inner_tick)
    if not raw.strip():
        return []
    return [
        json.loads(line) for line in raw.strip().splitlines() if line.strip()
    ]


def scripted_tool_background_done_rows(
    store: MemoryStore,
) -> list[dict[str, object]]:
    raw = store.read_document(_SCOPE_PATHS.tool_background_jsonl)
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
