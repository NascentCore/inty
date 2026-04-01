# CREATED_BY_AGENT
"""
记忆提取模块

使用 LLM 从用户聊天历史中提取用户记忆
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openai import OpenAI

from config import get_config, get_default_memory_prompt


@dataclass
class ExtractedMemory:
    """提取的用户记忆"""

    # Part 1: 用户画像摘要（可直接嵌入提示词）
    summary_for_prompt: str
    # 完整的分析结果（包含 Part 1-4）
    full_analysis: str
    # 原始聊天历史字数
    chat_history_length: int


def extract_user_memory(
    chat_history_text: str,
    memory_prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> ExtractedMemory:
    """
    使用 LLM 从聊天历史中提取用户记忆

    Args:
        chat_history_text: 格式化后的聊天历史文本
        memory_prompt: 自定义记忆提取提示词，为 None 时使用默认提示词
        model: 自定义模型，为 None 时使用配置中的模型

    Returns:
        ExtractedMemory 对象
    """
    config = get_config()

    # 使用默认或自定义提示词
    if memory_prompt is None:
        memory_prompt = get_default_memory_prompt()

    # 使用配置或自定义模型
    if model is None:
        model = config.agent.model

    # 构建完整提示词
    full_prompt = f"{memory_prompt}\n\n---\n\n# 用户聊天记录\n\n{chat_history_text}"

    # 调用 LLM
    client = OpenAI(
        api_key=config.agent.api_key,
        base_url=config.agent.base_url,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": full_prompt},
        ],
        temperature=0.3,  # 较低温度以获得更一致的分析结果
        max_tokens=4000,
    )

    full_analysis = response.choices[0].message.content

    # 提取 Part 1 作为可嵌入提示词的摘要
    summary_for_prompt = extract_part1_summary(full_analysis)

    return ExtractedMemory(
        summary_for_prompt=summary_for_prompt,
        full_analysis=full_analysis,
        chat_history_length=len(chat_history_text),
    )


def extract_part1_summary(full_analysis: str) -> str:
    """
    从完整分析中提取 Part 1 用户画像摘要

    Args:
        full_analysis: LLM 返回的完整分析文本

    Returns:
        Part 1 的内容，或在无法提取时返回完整分析的前 2000 字符
    """
    # 尝试匹配 Part 1 部分
    # 可能的格式：
    # ### Part 1: ...
    # ## Part 1: ...
    # Part 1: ...
    # **Part 1: ...**

    patterns = [
        # 匹配从 Part 1 开始到 Part 2 之前的内容
        r"(?:#{1,3}\s*)?(?:\*\*)?Part\s*1[：:][^\n]*(?:\*\*)?\s*\n(.*?)(?=(?:#{1,3}\s*)?(?:\*\*)?Part\s*2|$)",
        # 匹配从"关于这位用户"开始到 Part 2 之前的内容
        r"(\*\*关于这位用户.*?)(?=(?:#{1,3}\s*)?(?:\*\*)?Part\s*2|$)",
        # 匹配整个 Part 1 标题到 Part 2 之间
        r"(Part\s*1.*?)(?=Part\s*2|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, full_analysis, re.DOTALL | re.IGNORECASE)
        if match:
            summary = match.group(1).strip()
            # 清理前后的分隔线
            summary = re.sub(r"^---+\s*", "", summary)
            summary = re.sub(r"\s*---+$", "", summary)
            if summary and len(summary) > 50:  # 确保提取到有意义的内容
                return summary

    # 如果无法提取 Part 1，尝试提取"关于这位用户"部分
    user_about_match = re.search(
        r"(\*\*关于这位用户.*?)(?=\n\n#{2,}|\n\n\*\*Part|\Z)",
        full_analysis,
        re.DOTALL,
    )
    if user_about_match:
        return user_about_match.group(1).strip()

    # 最后回退：返回前 2000 字符
    return full_analysis[:2000] if len(full_analysis) > 2000 else full_analysis


def load_custom_memory_prompt(prompt_path: Path) -> str:
    """
    加载自定义记忆提取提示词

    Args:
        prompt_path: 提示词文件路径

    Returns:
        提示词文本
    """
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")
