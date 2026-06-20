"""Phone-call feature tests."""

import base64
import math
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient as FastAPITestClient

from app.api import deps
from app.services.phone_call_service import (
    TwilioPcmBridgeCodec,
    phone_call_service,
)
from backend.inty.main import app
from tests.app.api.v1.endpoints.conftest import _make_user


class _ScalarResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDb:
    def __init__(self, scalar_value=None):
        self.scalar_value = scalar_value
        self.added = []
        self.committed = False

    async def execute(self, stmt):
        return _ScalarResult(self.scalar_value)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True


class _AllowSubscription:
    async def check_live_chat_limit(self, db, user, agent_id):
        return True, "", {"remaining_duration": 60}


class _FakeTwilio:
    def __init__(self):
        self.calls = []

    def create_call(self, *, to_number, twiml):
        self.calls.append({"to_number": to_number, "twiml": twiml})
        return SimpleNamespace(sid="CA_TEST", status="queued")


@pytest.fixture
def configured_phone_call(monkeypatch):
    cfg = phone_call_service.config
    monkeypatch.setattr(cfg, "enabled", True)
    monkeypatch.setattr(cfg, "twilio_from_number", "+15005550006")
    monkeypatch.setattr(cfg, "twilio_account_sid", "AC_TEST")
    monkeypatch.setattr(cfg, "twilio_auth_token", "auth")
    monkeypatch.setattr(
        cfg, "twilio_media_stream_base_url", "wss://voice.example"
    )
    monkeypatch.setattr(phone_call_service.gemini_live_config, "enabled", True)
    return cfg


def test_phone_call_status_requires_auth():
    with FastAPITestClient(app) as client:
        response = client.get("/api/v1/phone-calls/status")
    assert response.status_code == 401


def test_phone_call_status_authenticated(configured_phone_call):
    async def override_user():
        return _make_user()

    app.dependency_overrides[deps.get_current_active_user] = override_user
    try:
        with FastAPITestClient(app) as client:
            response = client.get("/api/v1/phone-calls/status")
    finally:
        app.dependency_overrides.pop(deps.get_current_active_user, None)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["enabled"] is True
    assert body["data"]["available"] is True


@pytest.mark.asyncio
async def test_start_outbound_call_normalizes_masks_and_binds(
    configured_phone_call,
):
    fake_twilio = _FakeTwilio()
    db = _FakeDb()
    user = _make_user(user_id="user-phone")

    result = await phone_call_service.start_outbound_call(
        db=db,
        current_user=user,
        agent_id="agent-1",
        phone_number="1234560123",
        subscription_svc=_AllowSubscription(),
        reason="test",
        twilio_service=fake_twilio,
    )

    assert result.call_sid == "CA_TEST"
    assert result.status == "queued"
    assert result.to_number_masked == "+1***0123"
    assert fake_twilio.calls[0]["to_number"] == "+11234560123"
    assert (
        '<Stream url="wss://voice.example/api/v1/phone-calls/twilio-media?'
        in fake_twilio.calls[0]["twiml"]
    )
    assert db.added[0].phone_number_hmac != "+11234560123"
    assert db.added[0].phone_number_masked == "+1***0123"
    assert db.committed is True


def test_call_me_at_phrase_extraction():
    assert (
        phone_call_service.extract_call_me_at_number(
            "Call me at 1234560123 please"
        )
        == "1234560123"
    )
    assert phone_call_service.extract_call_me_at_number("call me later") is None


@pytest.mark.asyncio
async def test_inbound_twiml_rejects_unknown_caller(configured_phone_call):
    cfg = phone_call_service.config
    cfg.inbound_number_agent_map = {"+15005550006": "agent-1"}
    inbound = SimpleNamespace(
        from_number="+14155550123",
        to_number="+15005550006",
        call_sid="CA_INBOUND",
    )

    twiml = await phone_call_service.build_inbound_twiml(
        db=_FakeDb(scalar_value=None),
        inbound=inbound,
    )

    assert "<Say>Please open the app" in twiml
    assert "<Stream" not in twiml


@pytest.mark.asyncio
async def test_inbound_twiml_streams_known_caller(configured_phone_call):
    cfg = phone_call_service.config
    cfg.inbound_number_agent_map = {"+15005550006": "agent-1"}
    inbound = SimpleNamespace(
        from_number="+14155550123",
        to_number="+15005550006",
        call_sid="CA_INBOUND",
    )

    twiml = await phone_call_service.build_inbound_twiml(
        db=_FakeDb(scalar_value="user-1"),
        inbound=inbound,
    )

    assert "<Connect><Stream" in twiml
    assert "token=" in twiml


def test_twilio_audio_codec_round_trip_duration():
    codec = TwilioPcmBridgeCodec()
    samples_24k = bytearray()
    for i in range(240):
        v = int(math.sin(i / 10.0) * 12000)
        samples_24k.extend(v.to_bytes(2, "little", signed=True))

    payload = codec.pcm16_24k_to_twilio_mulaw_8k_payload(bytes(samples_24k))
    assert payload
    pcm16 = codec.twilio_mulaw_8k_to_pcm16_16k(payload)
    assert len(pcm16) > 0
    assert len(base64.b64decode(payload)) in range(70, 90)
