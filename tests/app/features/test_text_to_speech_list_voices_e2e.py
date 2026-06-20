# CREATED_BY_AGENT
"""
E2E tests for list voices endpoint.

关键步骤总结：
1) 访问 /api/v1/text-to-speech/list-voices（不带 provider），验证返回同时包含
   google(gemini) 与 elevenlabs 两类音色。
2) 分别带 provider=gemini 与 provider=elevenlabs 调用，验证过滤结果与
   voice_id 前缀保持一致，避免 provider/voice_id 语义漂移。
"""

from __future__ import annotations

import pytest

from tests.app.api.test_client import TestClient


def _list_voices(
    integration_client: TestClient, *, provider: str | None = None
) -> list[dict]:
    params = {}
    if provider is not None:
        params["provider"] = provider

    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/text-to-speech/list-voices",
        params=params,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, list), payload
    return payload


def _provider_set(voices: list[dict]) -> set[str]:
    return {
        voice.get("provider")
        for voice in voices
        if isinstance(voice, dict) and isinstance(voice.get("provider"), str)
    }


def _require_elevenlabs_voices_or_skip(elevenlabs_voices: list[dict]) -> None:
    if len(elevenlabs_voices) == 0:
        pytest.skip(
            "ElevenLabs voices are unavailable in this environment (likely missing/invalid API key)."
        )


def test_list_voices_includes_google_and_elevenlabs_voices(
    integration_client: TestClient,
):
    voices = _list_voices(integration_client)
    assert len(voices) > 0

    providers = _provider_set(voices)
    assert (
        "gemini" in providers
    ), f"Expected gemini voices, got providers={providers}"
    elevenlabs_filtered = _list_voices(
        integration_client, provider="elevenlabs"
    )
    _require_elevenlabs_voices_or_skip(elevenlabs_filtered)
    assert "elevenlabs" in providers, (
        f"Expected elevenlabs voices in default list when provider filter returns voices; "
        f"got providers={providers}"
    )

    gemini_voices = [v for v in voices if v.get("provider") == "gemini"]
    elevenlabs_voices = [v for v in voices if v.get("provider") == "elevenlabs"]

    assert any(
        str(v.get("voice_id", "")).startswith("google/") for v in gemini_voices
    ), f"Expected google/ voice_id for gemini voices, got={gemini_voices[:3]}"
    assert any(
        str(v.get("voice_id", "")).startswith("11labs/")
        for v in elevenlabs_voices
    ), f"Expected 11labs/ voice_id for elevenlabs voices, got={elevenlabs_voices[:3]}"


def test_list_voices_provider_filter_returns_expected_provider_voices(
    integration_client: TestClient,
):
    gemini_voices = _list_voices(integration_client, provider="gemini")
    assert len(gemini_voices) > 0
    assert _provider_set(gemini_voices) == {"gemini"}
    assert all(
        str(v.get("voice_id", "")).startswith("google/") for v in gemini_voices
    ), f"Found non-google prefixed gemini voice_ids: {gemini_voices[:5]}"

    elevenlabs_voices = _list_voices(integration_client, provider="elevenlabs")
    _require_elevenlabs_voices_or_skip(elevenlabs_voices)
    assert _provider_set(elevenlabs_voices) == {"elevenlabs"}
    assert all(
        str(v.get("voice_id", "")).startswith("11labs/")
        for v in elevenlabs_voices
    ), f"Found non-11labs prefixed elevenlabs voice_ids: {elevenlabs_voices[:5]}"
