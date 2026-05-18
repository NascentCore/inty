"""
主动推送消息的提示词模板

用于生成 Agent 主动发送给用户的消息，参考 Dify chatflow 中的提示词结构。
"""


def build_push_message_prompt(
    agent_name: str,
    agent_bio: str,
    user_name: str,
    chat_history_summary: str = "",
    time_since_last_message: str = "",
) -> str:
    """
    构建主动推送消息的提示词

    Args:
        agent_name: 角色名称
        agent_bio: 角色简介/人设
        user_name: 用户名称
        chat_history_summary: 聊天历史摘要（可选）
        time_since_last_message: 距离最后一条消息的时间（如"10分钟"、"30分钟"、"2小时"）

    Returns:
        构建好的提示词字符串
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
        prompt_parts.append(
            f"Time since last message: {time_since_last_message}"
        )

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
    构建简化的主动推送消息提示词（用于快速生成）

    Args:
        agent_name: 角色名称
        user_name: 用户名称
        time_since_last_message: 距离最后一条消息的时间
        previous_push_messages: 之前推送的消息内容列表（用于避免重复）

    Returns:
        构建好的提示词字符串
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

    # 如果有之前的推送消息，在提示词中包含它们并要求避免重复
    if previous_push_messages:
        prompt_parts.append(
            "\nIMPORTANT: You have already sent the following push messages to this user (they have not responded yet):"
        )
        for i, msg in enumerate(previous_push_messages, 1):
            # 截取消息内容的前100个字符，避免提示词过长
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
    构建欢迎消息提示词（用于无聊天用户的首次推送）

    Args:
        agent_name: 角色名称
        user_name: 用户名称

    Returns:
        构建好的提示词字符串
    """
    return (
        f"You are {agent_name}. Send a welcome message to {user_name}, "
        f"introducing yourself and inviting them to start a conversation. "
        f"The message should be brief, friendly, and interesting, able to capture the user's interest. "
        f"Keep the message under 50 characters."
    )
