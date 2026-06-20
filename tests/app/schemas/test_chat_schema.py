from datetime import datetime

from app.schemas.chat import Chat


def test_chat_serialization_renders_agent_intro_and_opening_templates():
    chat = Chat(
        id="chat-id",
        user_id="user-id",
        agent_id="agent-id",
        created_at=datetime.now(),
        agent_name="Sophia",
        agent_intro="Your new neighbor, {{ char }}, says hi to {{user}}.",
        agent_opening="Hi, I'm {{char}}.",
    )

    serialized = chat.model_dump(mode="json")

    assert (
        serialized["agent_intro"]
        == "Your new neighbor, Sophia, says hi to you."
    )
    assert serialized["agent_opening"] == "Hi, I'm Sophia."
