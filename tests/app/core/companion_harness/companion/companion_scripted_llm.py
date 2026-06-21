"""Wire a real CompanionLLMClient to one shared scripted FakeOpenAI for harness tests.

TODO(!3562): ``build_scripted_injected_runtime`` feeds headless ``AgenticCompanion.drain_once`` CI tests.
"""

from __future__ import annotations

from app.core.companion_harness.agentic_companion.turn import InjectedCompanionRuntime
from app.core.companion_harness.companion.manager import CompanionConfig
from app.core.llms.client import CompanionLLMClient, CompanionLLMConfig
from app.external_services.fakes.openai import FakeCompletionStep, FakeOpenAI
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import DEEPSEEK_V3_2
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


def _scripted_llm_config() -> CompanionLLMConfig:
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
) -> tuple[InjectedCompanionRuntime, FakeOpenAI]:
    """Build test ``InjectedCompanionRuntime`` with NONE bootstrap and scripted transport."""
    llm_config = _scripted_llm_config()
    client, fake = companion_llm_client_with_scripted_transport(llm_config, script)
    companion_config = CompanionConfig(
        llm=llm_config,
        memory_pg_dsn=companion_memory_registry_dsn(),
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        langsmith_companion_parent_run_enabled=False,
    )
    injected = InjectedCompanionRuntime(
        companion_config=companion_config,
        llm_client=client,
    )
    return injected, fake


def assert_all_routes_share_fake(client: CompanionLLMClient, fake: FakeOpenAI) -> None:
    """Assert every route slot points at the same scripted FakeOpenAI instance."""
    assert client._client is fake  # noqa: SLF001
    assert client._client_dual_chat is fake  # noqa: SLF001
    assert client._client_dual_tool is fake  # noqa: SLF001
    assert client._client_inner_tick is fake  # noqa: SLF001
    assert client.async_llm_client._async_client is fake.async_client  # noqa: SLF001
