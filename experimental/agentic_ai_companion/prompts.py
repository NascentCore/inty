"""系统提示词构建，依赖 app.core.agent。"""

from __future__ import annotations

from app.core.agent import prompt_template, prompts

from . import tools


def build_imate_photo_album_system_message(*, _logger=None) -> dict[str, str] | None:
    """构建相册索引的系统消息，列出可用照片文件名（无后缀）。若无照片则返回 None。"""
    index = tools.get_photo_album_index()
    if not index:
        if _logger is not None:
            _logger.debug("相册为空，跳过 photo album 系统消息")
        return None
    names = sorted(index.keys())
    content = (
        "## Photo Album\n"
        f"Available photos (filename without extension): {', '.join(names)}. "
        "When the user asks for your photo or selfie, call send_selfie_photo; the tool picks one not yet sent."
    )
    return {"role": "system", "content": content}


def build_system_messages_openai(
    char_name: str,
    user_name: str,
    *,
    _logger=None,
) -> list[dict[str, str]]:
    if _logger is not None:
        _logger.debug("构建系统消息 char_name=%s user_name=%s", char_name, user_name)
    main_prompt = prompts.ROLEPLAY_MAIN_PROMPT_1225
    mode_prompt = prompts.FLIRTING_MODE_PROMPT_20250902
    rendered_main = prompt_template.render_prompt_jinja2_template(
        main_prompt, char=char_name, user=user_name
    )
    rendered_mode = prompt_template.render_prompt_jinja2_template(
        mode_prompt, char=char_name, user=user_name
    )
    tool_instruction = (
        "## Tool Usage\n"
        "When the user requests app icon, Zun Long's photo, an image, voice, or your selfie/photo, you MUST call the corresponding tool. "
        "This applies to every new user message, including after a previous tool result. Never return empty content or skip the tool call."
    )
    msgs = [
        {"role": "system", "content": rendered_main},
        {"role": "system", "content": rendered_mode},
        {"role": "system", "content": tool_instruction},
    ]
    photo_album_msg = build_imate_photo_album_system_message(_logger=_logger)
    if photo_album_msg is not None:
        msgs.append(photo_album_msg)
    if _logger is not None:
        _logger.info("系统消息已构建，共 %d 条", len(msgs))
    return msgs
