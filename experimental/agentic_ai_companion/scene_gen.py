# 根据最近对话上下文调用 Gemini 文本模型生成连续文字 scene，仅输出文字、不生成图片。
# 参考: image_gen 的上下文拼接；prompts 中 FLIRTING_MODE 的输出格式约定。

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from google.genai import Client

SCENE_MODEL = "gemini-2.0-flash"
RECENT_MESSAGES_LIMIT = 10

from loguru import logger


def _format_messages_as_context(
    messages: list[dict[str, Any]], recent_n: int
) -> str:
    """将最近 N 条 user/assistant 消息格式化为对话上下文字符串（不含 tool 消息）。"""
    lines: list[str] = []
    for m in messages[-recent_n:]:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if not content or role not in ("user", "assistant"):
            continue
        if role == "user":
            lines.append(f"User: {content}")
        else:
            lines.append(f"Assistant: {content}")
    return "\n".join(lines) if lines else ""


def _build_scene_prompt(
    context_str: str,
    char_name: str,
    user_name: str,
    user_desires: str,
    max_paragraphs: int = 5,
) -> str:
    """构建发给 Gemini 的 scene 生成提示：角色、用户、格式与长度要求。"""
    return (
        "You are an erotic writer.\n"
        f"You are writing a scene of erotic/intimate interaction between {char_name} and {user_name}.\n\n"
        f"You are writing from the perspective of {char_name}.\n"
        f"You are writing to satisfy {user_name}'s erotic/intimate fantasies.\n"
        f"{user_name}'s desires: {user_desires}\n"
        f"The format of conversations between {char_name} and {user_name}:\n"
        "All actions, emotions, and scene descriptions in parentheses (); "
        'All dialogues in double quotation marks "". '
        "Your must continue from the following conversations:\n"
        f"{context_str}\n\n"
        f"Generate a single continuous scene in 3 to {max_paragraphs} paragraphs. "
        "Advance the scene based on the conversations, using your own initiative. "
        "Do not ask the user what to do next. "
        "Must make something new and unexpected. "
        "Do not use *, **, [], <> or Markdown. "
        "Text only—do not describe images or request image generation.\n\n"
        "Your writing:\n"
    )


def generate_erotic_scene_text(
    messages: list[dict[str, Any]],
    client: "Client",
    char_name: str,
    user_name: str,
    *,
    user_desires: str = "",
    recent_n: int = RECENT_MESSAGES_LIMIT,
    max_paragraphs: int = 5,
    model: str = SCENE_MODEL,
    _logger: logging.Logger | None = None,
) -> str:
    """
    根据最近对话、角色名与用户名，调用 Gemini 文本模型生成一段连续的文字 scene。
    返回生成的纯文本；格式与 FLIRTING_MODE 一致：动作/情绪在 ()，台词在 ""。
    """
    log = _logger or logger
    recent = messages[-recent_n:] if len(messages) > recent_n else messages
    context_str = _format_messages_as_context(recent, recent_n)
    prompt = _build_scene_prompt(
        context_str,
        char_name,
        user_name,
        user_desires or "",
        max_paragraphs=max_paragraphs,
    )
    log.info(
        "generate_erotic_scene_text: char=%s user=%s recent_n=%d prompt=%s",
        char_name,
        user_name,
        recent_n,
        prompt,
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ValueError("Gemini 未返回 candidates")
    content = getattr(candidates[0], "content", None)
    if not content:
        raise ValueError("Gemini 返回的 candidate 无 content")
    parts = getattr(content, "parts", None) or []
    if not parts:
        raise ValueError("Gemini 返回的 content 无 parts")
    text_parts: list[str] = []
    for p in parts:
        t = getattr(p, "text", None)
        if isinstance(t, str) and t.strip():
            text_parts.append(t.strip())
    if not text_parts:
        raise ValueError("Gemini 返回的 parts 中无有效 text")
    return "\n\n".join(text_parts)
