"""Wire a real CompanionLLMClient to one shared scripted FakeOpenAI for harness tests.

TODO(#3563): Read ``user_turn.llm_loop_mode`` when sizing FakeOpenAI script step counts.
"""

from __future__ import annotations

import json

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.turn import InjectedCompanionRuntime
from app.core.companion_harness.companion.manager import CompanionConfig, CompanionManager
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.llms.client import CompanionLLMClient, CompanionLLMConfig
from app.external_services.fakes.openai import FakeCompletionStep, FakeOpenAI
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import DEEPSEEK_V3_2
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


def scripted_harness_llm_config() -> CompanionLLMConfig:
    return CompanionLLMConfig(
        api_key="test-key",
        api_base="https://example.invalid/v1",
        default_model=DEEPSEEK_V3_2,
        chat_model=DEEPSEEK_V3_2,
        tool_model=DEEPSEEK_V3_2,
    )


def companion_llm_client_with_scripted_transport(
    config: CompanionLLMConfig,
    script: tuple[FakeCompletionStep, ...],
) -> tuple[CompanionLLMClient, FakeOpenAI]:
    """Return real CompanionLLMClient with one shared FakeOpenAI on all sync+async routes."""
    client = CompanionLLMClient(config)
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
    client, fake = companion_llm_client_with_scripted_transport(llm_config, script)
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
        json.loads(line)
        for line in raw.strip().splitlines()
        if line.strip()
    ]
    return [row["role"] for row in rows]


def scripted_transcript_rows(store: MemoryStore) -> list[dict[str, object]]:
    raw = store.read_document("transcript.jsonl")
    return [
        json.loads(line)
        for line in raw.strip().splitlines()
        if line.strip()
    ]


def scripted_tool_background_done_rows(store: MemoryStore) -> list[dict[str, object]]:
    raw = store.read_document("tool_background.jsonl")
    return [
        json.loads(line)
        for line in raw.strip().splitlines()
        if line.strip()
    ]


def assert_all_routes_share_fake(client: CompanionLLMClient, fake: FakeOpenAI) -> None:
    """Assert every route slot points at the same scripted FakeOpenAI instance."""
    assert client._client is fake  # noqa: SLF001
    assert client._client_dual_chat is fake  # noqa: SLF001
    assert client._client_dual_tool is fake  # noqa: SLF001
    assert client._client_inner_tick is fake  # noqa: SLF001
    assert client.async_llm_client._async_client is fake.async_client  # noqa: SLF001
