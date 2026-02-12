"""
Prompt templates for proactive push messages.

Used to generate proactive agent messages sent to users, inspired by the
prompt structure in Dify chatflow.
"""


def build_push_message_prompt(
    agent_name: str,
    agent_bio: str,
    user_name: str,
    chat_history_summary: str = "",
    time_since_last_message: str = "",
) -> str:
    """
    Build a proactive push-message prompt.

    Args:
        agent_name: Character name.
        agent_bio: Character bio/persona.
        user_name: User name.
        chat_history_summary: Summary of chat history (optional).
        time_since_last_message: Time since the last message (for example:
            "10 minutes", "30 minutes", "2 hours").

    Returns:
        The assembled prompt string.
    """
    # Basic prompt structure, referencing the format: article | @character_bio.text | @input | @test.me... @text
    prompt_parts = []

    # Character information section
    prompt_parts.append(f"Character: {agent_name}")
    if agent_bio:
        prompt_parts.append(f"Character Bio: {agent_bio}")

    # User information section
    prompt_parts.append(f"User: {user_name}")

    # Time information
    if time_since_last_message:
        prompt_parts.append(f"Time since last message: {time_since_last_message}")

    # Chat history summary
    if chat_history_summary:
        prompt_parts.append(f"Previous chat summary: {chat_history_summary}")

    # Instruction to initiate conversation
    prompt_parts.append(
        "As the character, proactively send a message to the user. "
        "The content should be natural and interesting, able to capture the user's attention and encourage them to continue the conversation. "
        "The message should reflect the character's personality traits and take into account that some time has passed since the last chat. "
        "The message should be brief (no more than 50 characters), but full of personality and appeal."
    )

    return "\n".join(prompt_parts)


def build_simple_push_message_prompt(
    agent_name: str,
    user_name: str,
    time_since_last_message: str = "",
    previous_push_messages: list = None,
) -> str:
    """
    Build a simplified proactive push-message prompt (for quick generation).

    Args:
        agent_name: Character name.
        user_name: User name.
        time_since_last_message: Time since the last message.
        previous_push_messages: List of previously sent push messages
            (used to avoid repetition).

    Returns:
        The assembled prompt string.
    """
    if previous_push_messages is None:
        previous_push_messages = []

    time_context = ""
    if time_since_last_message:
        if time_since_last_message == "10min":
            time_context = "just now"
        elif time_since_last_message == "30min":
            time_context = "a while"
        elif time_since_last_message == "2h":
            time_context = "some time"

    prompt_parts = [
        f"You are {agent_name}. Proactively send a brief and interesting message to {user_name} "
        f"to encourage them to continue the conversation. The message should reflect your personality traits"
        f"{', considering that some time has passed since the last chat' if time_context else ''}."
    ]

    # If previous push messages exist, include them and ask for non-repetition.
    if previous_push_messages:
        prompt_parts.append(
            "\nIMPORTANT: You have already sent the following push messages to this user (they have not responded yet):"
        )
        for i, msg in enumerate(previous_push_messages, 1):
            # Truncate to first 100 characters to keep the prompt concise.
            msg_preview = msg[:100] + "..." if len(msg) > 100 else msg
            prompt_parts.append(f"{i}. {msg_preview}")
        prompt_parts.append(
            "You MUST generate a DIFFERENT message that is not similar to any of the above messages. "
            "Use different wording, different topics, or different approaches to avoid repetition."
        )

    prompt_parts.append("Keep the message under 50 characters.")

    return "\n".join(prompt_parts)


def build_welcome_message_prompt(
    agent_name: str,
    user_name: str,
) -> str:
    """
    Build a welcome-message prompt for first-time users with no chat history.

    Args:
        agent_name: Character name.
        user_name: User name.

    Returns:
        The assembled prompt string.
    """
    return (
        f"You are {agent_name}. Send a welcome message to {user_name}, "
        f"introducing yourself and inviting them to start a conversation. "
        f"The message should be brief, friendly, and interesting, able to capture the user's interest. "
        f"Keep the message under 50 characters."
    )
