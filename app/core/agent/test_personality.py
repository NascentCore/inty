from app.core.agent.personality import EVERYONE_LIKES_YOU


def test_personality_to_prompt():
    """Test that the personality to prompt method returns the correct prompt"""
    prompt = EVERYONE_LIKES_YOU.to_prompt()
    assert (
        prompt
        == "personality: Kind, Generous, Compassionate, Empathetic, Optimistic, Cheerful"
    )
