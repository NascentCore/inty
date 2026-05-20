from __future__ import annotations

from ..contracts import ChannelType


def compose_reactive_reply(
    *, channel: ChannelType, inbound_content: str
) -> str:
    if channel is ChannelType.TELEGRAM:
        return f"收到你的消息：{inbound_content}"
    if channel is ChannelType.SMS:
        return f"收到你的短信：{inbound_content}"
    return f"收到你的来电消息：{inbound_content}"


def compose_followup_reply(*, channel: ChannelType, user_id: str) -> str:
    if channel is ChannelType.SMS:
        return f"你好 {user_id}，这里是短信回访。"
    if channel is ChannelType.TELEGRAM:
        return f"你好 {user_id}，这里是 Telegram 回访。"
    return f"你好 {user_id}，这是计划中的语音回访。"
