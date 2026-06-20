"""Wire a real CompanionLLMClient to one shared scripted FakeOpenAI for harness tests."""

from __future__ import annotations

from app.core.llms.client import CompanionLLMClient, CompanionLLMConfig
from app.external_services.fakes.openai import FakeCompletionStep, FakeOpenAI


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


def assert_all_routes_share_fake(client: CompanionLLMClient, fake: FakeOpenAI) -> None:
    """Assert every route slot points at the same scripted FakeOpenAI instance."""
    assert client._client is fake  # noqa: SLF001
    assert client._client_dual_chat is fake  # noqa: SLF001
    assert client._client_dual_tool is fake  # noqa: SLF001
    assert client._client_inner_tick is fake  # noqa: SLF001
    assert client.async_llm_client._async_client is fake.async_client  # noqa: SLF001
