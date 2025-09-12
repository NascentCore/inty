"""
Utility functions for picking prompts.
"""

from enum import StrEnum
from typing import Optional

class SystemPromptingMode(StrEnum):
    """
    指生成系统提示词的方式，系统提示词指的是输入到大模型中最开始的一组提示词。
    具体来说根据角色设定、用户信息、对话设置，及其他相关信息来生成系统提示词。

    该生成提示词。
    """
    # 指未设置系统提示词模式，调用者须自己决定采用何种方式来处理。
    UNSET = "unset"

    # 指使用角色指定的提示词（无论是否空白）不进行任何额外的处理。
    STATIC = "static"

    # 指填充缺失的提示词，但不做额外处理。
    FILL_MISSING = "fill_missing"

    # 指强制替换已有的提示词，如聊天风格提示词会替换为暧昧模式（Flirting）模式。
    OVERRIDE = "override"


def pick_prompt(sys_pmt_mode: SystemPromptingMode, default: str, configured: Optional[str] = None, override: Optional[str] = None) -> str:
    """
    Pick a prompt from a list of prompts.
    """
    assert sys_pmt_mode != SystemPromptingMode.UNSET, "sys_pmt_mode is unset 无法处理"
    if sys_pmt_mode == SystemPromptingMode.STATIC:
        # 指使用角色指定的提示词（无论是否空白）不进行任何额外的处理。
        return configured
    elif sys_pmt_mode == SystemPromptingMode.FILL_MISSING:
        # 指填充缺失的提示词，但不做额外处理。
        return configured or default
    elif sys_pmt_mode == SystemPromptingMode.OVERRIDE:
        # 指强制替换已有的提示词，如聊天风格提示词会替换为暧昧模式（Flirting）模式。
        return override or configured or default
    else:
        raise ValueError(f"Invalid system prompting mode: {sys_pmt_mode}")
