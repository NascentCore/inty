from datetime import datetime, timezone

from app.core.agent import agent as agent_module
from app.models.chat_settings import ChatSettings


def test_normalize_langsmith_metadata_serializes_chat_settings_model():
    now = datetime(2026, 2, 12, 10, 30, tzinfo=timezone.utc)
    chat_settings = ChatSettings(
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

    metadata = agent_module._normalize_langsmith_metadata(
        {"chat_settings": chat_settings}
    )
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

    normalized = agent_module._normalize_langsmith_metadata(metadata)

    assert normalized["opaque"] == "OpaqueValue(debug=ok)"
    assert normalized["nested"]["values"][0] == "OpaqueValue(debug=ok)"
    assert normalized["nested"]["values"][1]["more"] == "OpaqueValue(debug=ok)"
