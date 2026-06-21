"""Tests for companion_scripted_llm wiring helper."""

from __future__ import annotations

from app.core.llms.client import CompanionLLMConfig
from app.external_services.fakes.openai import fake_step_text
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    assert_all_routes_share_fake,
    companion_llm_client_with_scripted_transport,
)


def test_companion_llm_client_with_scripted_transport_wires_all_routes() -> (
    None
):
    script = (fake_step_text("wired"),)
    client, fake = companion_llm_client_with_scripted_transport(
        CompanionLLMConfig(api_key="test-key"),
        script,
    )
    assert_all_routes_share_fake(client, fake)

    resp = client.chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        scene="chat",
    )
    assert resp.choices[0].message.content == "wired"
    assert fake.script_index == 1
