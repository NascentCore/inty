"""Tests for ``PromptTemplate`` named-slot rendering (#3453)."""

from __future__ import annotations

import pytest
from jinja2 import UndefinedError

from app.core.companion_harness.prompting.system_messages import (
    _output_contract_text_interactive_bootstrap_tools,
)
from app.core.companion_harness.prompting.template import (
    BOOTSTRAP_OUTPUT_CONTRACT_TEMPLATE,
    PromptTemplate,
    render_prompt_template,
)

_BOOTSTRAP_OUTPUT_CONTRACT_GOLDEN = (
    "输出与工具（交互式关系建立阶段）：发起 tool_calls 时，**必须**在 message.content "
    "写一句简短、自然、面向用户的进行中说明（像边做事边聊天，不要机械播报「正在执行工具」"
    "或重复状态口号）。路径工具（memory_store_*）访问本会话持久化档案（MemoryStore），"
    "类 POSIX 路径，并非用户设备上的文件夹。"
    "（0）本阶段用 **memory_store_write_document** 把 "
    "**COMPANIONSHIP.md / IDENTITY.md / STYLE.md / USER.md** 落到可用初稿；"
    "**SOUL.md** 与 **MEMORY.md** 本阶段不通过该工具写入"
    "（沿用包内模板种子，见 TEMPLATE_REFERENCE）。"
    "即使用户配合度低，也基于已有对话写 best-effort 初稿，不可留空模板。"
    "用户选定内置陪伴模式时调用 **companion_set_experience_profile**（须附 note）。"
    "当你判断本阶段目标已达成、可与用户进入日常相处节奏时，**必须先完成上述三份初稿写入**，"
    "再**必须**调用 **companion_bootstrap_user_interactive_complete**（可选短 note）；"
    "禁止跳过写入直接 complete；"
    "未调用该工具前不要声称阶段已结束。"
    "调用完成后进入日常相处；后续轮次可用 **memory_store_write_document** "
    "按需更新允许列表内的持久化约定稿。"
    "（TOOLS 操作说明与 significance 评分引导为包内固定模版，不由工具写入。）"
    "（1）须核对持久化档案时先用 **memory_store_read_document** 读正文；勿编造。"
    "（2）凡涉及可与持久化档案核对的事实，须先读到持久化正文再作答。"
    "（3）模型与实现细节类问题：仅可依据当前可见上下文或已执行工具返回作答，"
    "无法核验时如实说明不确定。"
)


def test_render_prompt_template_substitutes_variables() -> None:
    template = PromptTemplate(body="Hello {{ name }}")
    assert render_prompt_template(template, {"name": "Inty"}) == "Hello Inty"


def test_render_prompt_template_raises_on_missing_variable() -> None:
    template = PromptTemplate(body="Hello {{ name }}")
    with pytest.raises(UndefinedError):
        render_prompt_template(template, {})


def test_bootstrap_output_contract_matches_golden_text() -> None:
    rendered = _output_contract_text_interactive_bootstrap_tools()
    assert rendered == _BOOTSTRAP_OUTPUT_CONTRACT_GOLDEN


def test_bootstrap_output_contract_template_renders_with_required_slots() -> None:
    variables = {
        key: f"<{key}>"
        for key in (
            "in_turn_tool_round_content_contract_zh",
            "memorystore_path_tools_intro_zh",
            "companionship_doc",
            "identity_doc",
            "style_doc",
            "user_doc",
            "soul_doc",
            "memory_doc",
            "tool_memory_store_write_document",
            "tool_companion_set_experience_profile",
            "tool_companion_bootstrap_user_interactive_complete",
            "tool_memory_store_read_document",
        )
    }
    rendered = render_prompt_template(
        BOOTSTRAP_OUTPUT_CONTRACT_TEMPLATE,
        variables,
    )
    assert "<tool_memory_store_write_document>" in rendered
    assert "<companionship_doc>" in rendered
