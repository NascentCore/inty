from types import SimpleNamespace

from google.genai import types
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import pytest

import app.services.live_chat_service as live_chat_module
from app.schemas.live_chat import LiveChatConfig
from app.services.live_chat_service import LiveChatService, LiveSession


def _build_service_with_language_config() -> LiveChatService:
    service = LiveChatService()
    service._config = SimpleNamespace(
        default_voice="Zephyr",
        input_transcription=True,
        output_transcription=True,
        send_sample_rate=16000,
        speech_language_code="en-US",
        response_language_name="English",
        session_resumption=False,
        trigger_tokens=10000,
        target_tokens=512,
    )
    return service


def test_build_system_instruction_includes_english_only_policy():
    service = _build_service_with_language_config()

    instruction = service._build_system_instruction(
        agent_data={
            "personality": "Friendly and warm.",
            "scenario": "Daily chat.",
            "intro": "A supportive companion.",
        },
        history_messages=[],
    )

    assert "CRITICAL LANGUAGE RULE" in instruction
    assert "YOU MUST SPEAK ONLY IN English" in instruction
    assert "DO NOT code-switch or mix languages" in instruction


def test_build_system_instruction_merged_response_language_override():
    service = _build_service_with_language_config()

    instruction = service._build_system_instruction(
        agent_data={"personality": "P", "scenario": "S", "intro": "I"},
        history_messages=[],
        merged_response_language_name="Arabic",
    )

    assert "YOU MUST SPEAK ONLY IN Arabic" in instruction
    assert "YOU MUST SPEAK ONLY IN English" not in instruction


def test_resolved_response_language_falls_back_to_speech_code():
    service = _build_service_with_language_config()
    session = LiveSession(
        session_id="s1",
        agent_id="a1",
        user_id="u1",
        chat_id="c1",
        config=LiveChatConfig(speech_language_code="ar-SA"),
    )
    assert service._resolved_response_language_name(session) == "ar-SA"
    assert service._resolved_speech_language_code(session) == "ar-SA"


def test_build_live_config_uses_merged_speech_override():
    service = _build_service_with_language_config()

    live_config = service._build_live_config(
        merged_speech_language_code="ar-SA",
        voice_id="Zephyr",
        agent_gender="FEMALE",
        system_instruction="test",
    )

    if "language_code" in getattr(types.SpeechConfig, "model_fields", {}):
        assert live_config.speech_config.language_code == "ar-SA"


def test_build_live_config_sets_speech_language_code_when_supported():
    service = _build_service_with_language_config()

    live_config = service._build_live_config(
        merged_speech_language_code="en-US",
        voice_id="Zephyr",
        agent_gender="FEMALE",
        system_instruction="test",
    )

    assert live_config.speech_config is not None
    assert live_config.speech_config.voice_config is not None
    assert live_config.speech_config.voice_config.prebuilt_voice_config is not None
    assert (
        live_config.speech_config.voice_config.prebuilt_voice_config.voice_name
        == "Zephyr"
    )

    if "language_code" in getattr(types.SpeechConfig, "model_fields", {}):
        assert live_config.speech_config.language_code == "en-US"
    else:
        assert not hasattr(live_config.speech_config, "language_code")


def test_build_live_config_accepts_google_prefixed_voice_id():
    """带 google/ 前缀的 voice_id 应解析为 raw 名字传给 Gemini Live。"""
    service = _build_service_with_language_config()

    live_config = service._build_live_config(
        merged_speech_language_code="en-US",
        voice_id="google/Zephyr",
        agent_gender="FEMALE",
        system_instruction="test",
    )

    assert live_config.speech_config is not None
    assert (
        live_config.speech_config.voice_config.prebuilt_voice_config.voice_name
        == "Zephyr"
    )


def test_build_live_config_non_gemini_voice_id_falls_back_without_error(
    monkeypatch,
):
    service = _build_service_with_language_config()
    error_messages = []

    def fake_error(*args, **kwargs):
        error_messages.append((args, kwargs))

    monkeypatch.setattr(live_chat_module.logger, "error", fake_error)

    live_config = service._build_live_config(
        merged_speech_language_code="en-US",
        voice_id="elevenlabs/2OMO1Tj9atc7AKQjMwxW",
        agent_gender="FEMALE",
        system_instruction="test",
    )

    assert live_config.speech_config is not None
    assert (
        live_config.speech_config.voice_config.prebuilt_voice_config.voice_name
        == "Zephyr"
    )
    assert error_messages == []


def test_build_system_instruction_from_text_chat_system_messages():
    service = _build_service_with_language_config()
    text_chat_system_messages = [
        SystemMessage(content="System A"),
        SystemMessage(content="System B"),
    ]

    instruction = service._build_system_instruction_from_text_chat_system_messages(
        text_chat_system_messages
    )

    assert "System A" in instruction
    assert "System B" in instruction
    assert "这是实时语音对话" in instruction
    assert "CRITICAL LANGUAGE RULE" in instruction
    assert "YOU MUST SPEAK ONLY IN English" in instruction


def test_build_prefill_turns_from_history_messages():
    service = _build_service_with_language_config()
    history_messages = [
        HumanMessage(content="Hi there"),
        AIMessage(content="Hello!"),
        HumanMessage(
            content=[
                {"type": "text", "text": "Tell me more."},
                {"type": "image_url", "image_url": {"url": "https://example.com/a.jpg"}},
            ]
        ),
    ]

    turns = service._build_prefill_turns_from_history_messages(history_messages)

    assert len(turns) == 3
    assert turns[0].role == "user"
    assert turns[0].parts[0].text == "Hi there"
    assert turns[1].role == "model"
    assert turns[1].parts[0].text == "Hello!"
    assert turns[2].role == "user"
    assert turns[2].parts[0].text == "Tell me more."


@pytest.mark.asyncio
async def test_start_live_session_prefills_text_chat_context(monkeypatch):
    service = LiveChatService()
    service._config = SimpleNamespace(
        model="gemini-live-test-model",
        default_voice="Zephyr",
        input_transcription=True,
        output_transcription=True,
        send_sample_rate=16000,
        receive_sample_rate=24000,
        speech_language_code="en-US",
        response_language_name="English",
        enabled=True,
        audio_temp_dir="",
        session_resumption=False,
        trigger_tokens=10000,
        target_tokens=512,
    )

    async def fake_get_agent_for_chat(db, agent_id):
        return {"id": agent_id, "voice_id": "google/Zephyr", "gender": "FEMALE"}

    class _FakeAgent:
        include_output_format_prompt_value = None

        def _get_user_profile_sync(self, user_id):
            return "##User Information\nName: John"

        def build_system_messages(
            self,
            user_profile,
            chat_settings,
            user_time_context=None,
            include_output_format_prompt=True,
        ):
            self.include_output_format_prompt_value = include_output_format_prompt
            return [
                SystemMessage(content="System Prompt A"),
                SystemMessage(content="System Prompt B"),
                SystemMessage(content=user_profile),
            ]

    fake_agent_holder = {"agent": None}

    async def fake_get_agent(agent_data):
        fake_agent_holder["agent"] = _FakeAgent()
        return fake_agent_holder["agent"]

    async def fake_get_or_create_chat_settings(db, chat_id, user_id, agent_id):
        return SimpleNamespace(premium_mode=False, style_prompt=None)

    monkeypatch.setattr(
        live_chat_module.agent_service, "get_agent_for_chat", fake_get_agent_for_chat
    )
    monkeypatch.setattr(
        live_chat_module.agent_manager, "get_agent", fake_get_agent
    )
    monkeypatch.setattr(
        live_chat_module,
        "get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        live_chat_module.chat_history_service,
        "get_history_messages",
        lambda _sid: [HumanMessage(content="U1"), AIMessage(content="A1")],
    )

    prefill_payload = {}

    class _FakeGeminiSession:
        async def send_client_content(self, *, turns=None, turn_complete=True):
            prefill_payload["turns"] = turns
            prefill_payload["turn_complete"] = turn_complete

        async def send_realtime_input(self, **kwargs):
            return None

        async def receive(self):
            if False:
                yield None

    class _FakeConnectContext:
        def __init__(self, fake_session):
            self._session = fake_session

        async def __aenter__(self):
            return self._session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class _FakeLiveAPI:
        def __init__(self, fake_session):
            self._session = fake_session

        def connect(self, **kwargs):
            return _FakeConnectContext(self._session)

    class _FakeClient:
        def __init__(self, fake_session):
            self.aio = SimpleNamespace(live=_FakeLiveAPI(fake_session))

    monkeypatch.setattr(service, "_get_client", lambda: _FakeClient(_FakeGeminiSession()))

    session = live_chat_module.LiveSession(
        session_id="session-1",
        agent_id="agent-1",
        user_id="user-1",
        chat_id="chat-1",
        config=LiveChatConfig(enable_prefill=True),
    )

    status_events = []

    async def _noop_audio(_data):
        return None

    async def _noop_transcript(*_args, **_kwargs):
        return None

    async def _on_status(status, _message):
        status_events.append(status)

    async def _noop_error(_code, _message):
        return None

    gen = service.start_live_session(
        session=session,
        db=SimpleNamespace(),
        on_audio=_noop_audio,
        on_transcript=_noop_transcript,
        on_status=_on_status,
        on_error=_noop_error,
    )

    await gen.asend(None)
    with pytest.raises(StopAsyncIteration):
        await gen.asend(None)

    assert prefill_payload["turn_complete"] is False
    turns = prefill_payload["turns"]
    assert len(turns) == 2
    assert turns[0].role == "user"
    assert turns[0].parts[0].text == "U1"
    assert turns[1].role == "model"
    assert turns[1].parts[0].text == "A1"
    assert live_chat_module.LiveChatStatus.CONNECTED in status_events
    assert fake_agent_holder["agent"] is not None
    assert fake_agent_holder["agent"].include_output_format_prompt_value is False


def test_opening_conversation_trigger_text_uses_language_or_fallback():
    t = LiveChatService._opening_conversation_trigger_text("Japanese")
    assert "Japanese" in t
    t_empty = LiveChatService._opening_conversation_trigger_text("")
    assert "the configured reply language" in t_empty


@pytest.mark.asyncio
async def test_send_opening_conversation_trigger_idempotent_and_no_user_buffer():
    service = _build_service_with_language_config()
    sent: list[tuple] = []

    class _FakeGs:
        async def send(self, input=None, end_of_turn=False):
            sent.append((input, end_of_turn))

    session = LiveSession(
        session_id="s-open",
        agent_id="a1",
        user_id="u1",
        chat_id="c1",
        config=LiveChatConfig(agent_starts_conversation=True),
    )
    session.gemini_session = _FakeGs()
    await service._send_opening_conversation_trigger(session, "English")
    assert len(sent) == 1
    assert sent[0][1] is True
    assert isinstance(sent[0][0], str)
    assert "English" in sent[0][0]
    assert session.user_transcript_buffer == ""
    assert session.opening_conversation_trigger_sent is True

    await service._send_opening_conversation_trigger(session, "English")
    assert len(sent) == 1
