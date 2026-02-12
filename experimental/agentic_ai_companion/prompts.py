"""系统提示词构建，依赖 app.core.agent。"""

from __future__ import annotations

from app.core.agent import prompt_template, prompts


def build_system_messages_openai(
    char_name: str,
    user_name: str,
    *,
    _logger=None,
) -> list[dict[str, str]]:
    if _logger is not None:
        _logger.debug("构建系统消息 char_name=%s user_name=%s", char_name, user_name)
    main_prompt = prompts.PURITY_ROLEPLAY_PROMPT.main_prompt
    mode_prompt = prompts.PURITY_ROLEPLAY_PROMPT.mode_prompt
    rendered_main = prompt_template.render_prompt_jinja2_template(
        main_prompt, char=char_name, user=user_name
    )
    rendered_mode = prompt_template.render_prompt_jinja2_template(
        mode_prompt, char=char_name, user=user_name
    )
    tool_instruction = (
        "## Tool Usage\n"
        "When the user requests app icon, Zun Long's photo, an image, or voice, you MUST call the corresponding tool. Never return empty content or skip the tool call."
    )
    msgs = [
        {"role": "system", "content": rendered_main},
        {"role": "system", "content": rendered_mode},
        {"role": "system", "content": tool_instruction},
    ]
    if _logger is not None:
        _logger.info("系统消息已构建，共 %d 条", len(msgs))
    return msgs
