from datetime import datetime, timezone

from app.utils.langsmith_metadata import normalize_langsmith_metadata


class _ColumnStub:
    def __init__(self, name: str):
        self.name = name


class _TableStub:
    def __init__(self, *column_names: str):
        self.columns = [_ColumnStub(name) for name in column_names]


class _FakeChatSettingsModel:
    __table__ = _TableStub(
        "id",
        "language",
        "voice_enabled",
        "keep_talking",
        "style_prompt",
        "premium_mode",
        "created_at",
        "updated_at",
        "user_id",
        "agent_id",
        "chat_id",
    )

    def __init__(
        self,
        *,
        id: str,
        language: str,
        voice_enabled: bool,
        keep_talking: bool,
        style_prompt: str,
        premium_mode: bool,
        created_at: datetime,
        updated_at: datetime,
        user_id: str,
        agent_id: str,
        chat_id: str,
    ):
        self.id = id
        self.language = language
        self.voice_enabled = voice_enabled
        self.keep_talking = keep_talking
        self.style_prompt = style_prompt
        self.premium_mode = premium_mode
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.agent_id = agent_id
        self.chat_id = chat_id


def test_normalize_langsmith_metadata_serializes_chat_settings_model():
    now = datetime(2026, 2, 12, 10, 30, tzinfo=timezone.utc)
    chat_settings = _FakeChatSettingsModel(
        id="chat_settings_1",
        language="en",
        voice_enabled=True,
        keep_talking=False,
        style_prompt="Be concise and warm.",
        premium_mode=True,
        user_id="user_1",
        agent_id="agent_1",
        chat_id="chat_1",
        created_at=now,
        updated_at=now,
    )

    metadata = normalize_langsmith_metadata({"chat_settings": chat_settings})
    serialized = metadata["chat_settings"]

    assert serialized["id"] == "chat_settings_1"
    assert serialized["language"] == "en"
    assert serialized["voice_enabled"] is True
    assert serialized["keep_talking"] is False
    assert serialized["style_prompt"] == "Be concise and warm."
    assert serialized["premium_mode"] is True
    assert serialized["created_at"] == now.isoformat()
    assert serialized["updated_at"] == now.isoformat()
    assert serialized["user_id"] == "user_1"
    assert serialized["agent_id"] == "agent_1"
    assert serialized["chat_id"] == "chat_1"


def test_normalize_langsmith_metadata_handles_opaque_nested_values():
    class OpaqueValue:
        def __str__(self) -> str:
            return "OpaqueValue(debug=ok)"

    metadata = {
        "opaque": OpaqueValue(),
        "nested": {"values": [OpaqueValue(), {"more": OpaqueValue()}]},
    }

    normalized = normalize_langsmith_metadata(metadata)

    assert normalized["opaque"] == "OpaqueValue(debug=ok)"
    assert normalized["nested"]["values"][0] == "OpaqueValue(debug=ok)"
    assert normalized["nested"]["values"][1]["more"] == "OpaqueValue(debug=ok)"
