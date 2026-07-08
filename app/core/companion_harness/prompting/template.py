"""Named-slot prompt template rendering for companion harness.

``PromptTemplate`` holds Jinja2 template bodies; callers supply a variable dict
for MemDoc paths, tool names, and other named slots (#3453).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from jinja2 import StrictUndefined, Template as Jinja2Template


@dataclass(frozen=True)
class PromptTemplate:
    """Named-slot prompt body; render with Jinja2 variable dict."""

    body: str


def render_prompt_template(
    template: PromptTemplate,
    variables: dict[str, str],
) -> str:
    """Render template; raise when a referenced variable is missing."""
    jinja_template = Jinja2Template(
        template.body,
        undefined=StrictUndefined,
    )
    return jinja_template.render(**variables)


BOOTSTRAP_OUTPUT_CONTRACT_TEMPLATE = PromptTemplate(
    body=(
        "输出与工具（交互式关系建立阶段）："
        "{{ in_turn_tool_round_content_contract_zh }}"
        "{{ memorystore_path_tools_intro_zh }}"
        "（0）本阶段用 **{{ tool_memory_store_write_document }}** 把 "
        "**{{ companionship_doc }} / {{ identity_doc }} / {{ style_doc }} / {{ user_doc }}** "
        "落到可用初稿；"
        "**{{ soul_doc }}** 与 **{{ memory_doc }}** 本阶段不通过该工具写入"
        "（沿用包内模板种子，见 TEMPLATE_REFERENCE）。"
        "即使用户配合度低，也基于已有对话写 best-effort 初稿，不可留空模板。"
        "用户选定内置陪伴模式时调用 **{{ tool_companion_set_experience_profile }}**（须附 note）。"
        "当你判断本阶段目标已达成、可与用户进入日常相处节奏时，**必须先完成上述三份初稿写入**，"
        "再**必须**调用 **{{ tool_companion_bootstrap_user_interactive_complete }}**（可选短 note）；"
        "禁止跳过写入直接 complete；"
        "未调用该工具前不要声称阶段已结束。"
        "调用完成后进入日常相处；后续轮次可用 **{{ tool_memory_store_write_document }}** "
        "按需更新允许列表内的持久化约定稿。"
        "（TOOLS 操作说明与 significance 评分引导为包内固定模版，不由工具写入。）"
        "（1）须核对持久化档案时先用 **{{ tool_memory_store_read_document }}** 读正文；勿编造。"
        "（2）凡涉及可与持久化档案核对的事实，须先读到持久化正文再作答。"
        "（3）模型与实现细节类问题：仅可依据当前可见上下文或已执行工具返回作答，"
        "无法核验时如实说明不确定。"
    ),
)
