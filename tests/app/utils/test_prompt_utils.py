# 测试 prompt_utils 的缩进感知模板替换

import pytest

from app.utils.prompt_utils import render_template_with_indent, strip_multiline_str


def test_render_template_with_indent_multiline_placeholder():
    """多行占位符按所在行缩进折叠，与用户示例一致。"""
    template = """I am {{ char }}, I have been many places:
  - {{ places }}
  - Tianjin
  - Shenzhen
  """
    char = "Yaxiong"
    places = """
Specials:
- Beijing
- New York
"""
    out = render_template_with_indent(template, char=char, places=places)
    assert out.splitlines() == [
        "I am Yaxiong, I have been many places:",
        "  - Specials:",
        "    - Beijing",
        "    - New York",
        "  - Tianjin",
        "  - Shenzhen",
        "  ",
    ]

def test_render_template_with_indent_single_line():
    """单行替换不改变缩进。"""
    template = "Hello {{ name }}!"
    assert render_template_with_indent(template, name="World") == "Hello World!"


def test_render_template_with_indent_no_placeholder():
    """无占位符时原样返回。"""
    template = "No placeholders here."
    assert render_template_with_indent(template) == template


def test_render_template_with_indent_missing_key_skipped():
    """kwargs 中缺少的 key 不替换，占位符保留。"""
    template = "{{ a }} and {{ b }}"
    assert render_template_with_indent(template, a="A") == "A and {{ b }}"


def test_render_template_with_indent_deeper_indent():
    """更深缩进的多行值。"""
    template = "List:\n    {{ items }}"
    items = "1\n2\n3"
    out = render_template_with_indent(template, items=items)
    assert out == "List:\n    1\n    2\n    3"


def test_render_template_with_indent_docstring_example():
    """与 render_template_with_indent 文档字符串示例一致。"""
    template = """
        I am {{ char }}, I have been many places:
          {{ places }}
        """
    out = render_template_with_indent(
        template,
        char="Yaxiong",
        places="places:\n  - Beijing\n  - New York\n  - etc.",
    )
    expected = """
        I am Yaxiong, I have been many places:
          places:
            - Beijing
            - New York
            - etc.
        """
    assert out == expected


def test_render_template_with_indent_multiline_kwarg_stripped():
    """多行 kwargs 值会先经 strip_multiline_str 规范化缩进再按占位符行缩进折叠。"""
    template = "Intro:\n  {{ block }}"
    # 多行值带多余首行缩进，应被 strip_multiline_str 规范化
    block = """
      - first
      - second
    """
    out = render_template_with_indent(template, block=block)
    # 规范化后为 "- first\n- second"，再按 "  " 折叠得：
    assert out == "Intro:\n  - first\n  - second"


def test_strip_multiline_str_example():
    """与需求示例一致：去首尾空行，以最左行为基准去缩进。"""
    a = """
     I am a great person
       but I am short
   haha
"""
    out = strip_multiline_str(a)
    # 最左行 "   haha" 有 3 个前导空格，每行去掉 3 格：5→2, 7→4, 3→0
    assert out == "  I am a great person\n    but I am short\nhaha"


def test_strip_multiline_str_leading_trailing_blank_lines():
    """去掉首部与尾部空行；行内尾部空白不处理。"""
    s = "\n\n  a\n\n"
    assert strip_multiline_str(s) == "a"


def test_strip_multiline_str_empty():
    """空串或仅空行返回空串。"""
    assert strip_multiline_str("") == ""
    assert strip_multiline_str("\n\n  \n") == ""


def test_strip_multiline_str_single_line():
    """单行时去掉前导空白（以最左为基准），不 strip 行尾。"""
    assert strip_multiline_str("  hello") == "hello"
    assert strip_multiline_str("\n  hello\n") == "hello"


def test_strip_multiline_str_relative_indent_preserved():
    """相对缩进保持不变。"""
    s = "    a\n      b\n    c"
    assert strip_multiline_str(s) == "a\n  b\nc"


def test_render_template_with_indent_multiline_placeholder_stripped():
    """多行占位符按所在行缩进折叠，与用户示例一致。"""
    template = """
        I am {{ char }}, I have been many places:
          {{ places }}"""
    char = "Yaxiong"
    places = """
        - Beijing
        - New York
        - etc."""
    template_stripped = strip_multiline_str(template)
    places_stripped = strip_multiline_str(places)
    out = render_template_with_indent(template_stripped, char=char, places=places_stripped)
    print(out)
    assert out.splitlines() == [
        "I am Yaxiong, I have been many places:",
        "  - Beijing",
        "  - New York",
        "  - etc.",
    ]


def test_render_template_with_indent_roleplay_text_output_format_expanded():
    """多行 ROLEPLAY_TEXT_OUTPUT_FORMAT 占位符被完整替换；续行缩进对齐到占位符起始列。"""
    template = "- Output Format\n        - {{ ROLEPLAY_TEXT_OUTPUT_FORMAT }}\n        - Avoid reusing."
    value = """Roleplay Text Output Format:
  - All dialogues must be enclosed in double quotation marks "".
  - All non-dialogue descriptions, like actions, thoughts, feelings, descriptions of surrounding environment, etc.:
    - must be enclosed in parentheses ().
    - should be short and concise.
    - should be vivid and detailed."""
    out = render_template_with_indent(template, ROLEPLAY_TEXT_OUTPUT_FORMAT=value.strip())
    # 续行缩进对齐到占位符起始列（此处为 10 格），value 内行自带 "  "，故首条续行为 12 格
    expected_lines = [
        "- Output Format",
        "        - Roleplay Text Output Format:",
        "            - All dialogues must be enclosed in double quotation marks \"\".",
        "            - All non-dialogue descriptions, like actions, thoughts, feelings, descriptions of surrounding environment, etc.:",
        "              - must be enclosed in parentheses ().",
        "              - should be short and concise.",
        "              - should be vivid and detailed.",
        "        - Avoid reusing.",
    ]
    assert out.splitlines() == expected_lines


def test_experimental_prompts_mode_contains_roleplay_text_output_format():
    """experimental.agentic_ai_companion.prompts 使用 prompt_utils 渲染后，mode 系统消息中应包含 ROLEPLAY_TEXT_OUTPUT_FORMAT 的完整内容。"""
    from experimental.agentic_ai_companion.prompts import build_system_messages_openai

    msgs = build_system_messages_openai("Char", "User")
    # 第二条 system 为 mode prompt（main, mode, tool_instruction, 可选 photo_album）
    mode_lines = msgs[1]["content"].splitlines()
    # 期望至少有一行包含下列子串
    expected_in_some_line = [
        "Roleplay Text Output Format",
        "double quotation marks",
        "parentheses ()",
    ]
    for exp in expected_in_some_line:
        assert any(exp in line for line in mode_lines), f"Expected substring {exp!r} in some line of mode content"


def test_build_system_messages_openai_output():
    """验证 build_system_messages_openai 返回结构、条数及前三条 system 消息的内容。"""
    from experimental.agentic_ai_companion.prompts import (
        DEFAULT_FOUNDATIONAL_GOAL,
        DEFAULT_MAX_WORDS,
        build_system_messages_openai,
    )

    char_name = "小尊"
    user_name = "小明"
    msgs = build_system_messages_openai(char_name, user_name)

    print(msgs)

    assert isinstance(msgs, list), "返回值应为 list"
    assert len(msgs) >= 3, "至少包含 main、mode、tool_instruction 三条 system 消息"
    for i, m in enumerate(msgs[:3]):
        assert m.get("role") == "system", f"第 {i+1} 条应为 system 消息"
        assert "content" in m and isinstance(m["content"], str), f"第 {i+1} 条应有 content 字符串"

    main_content = msgs[0]["content"]
    assert char_name in main_content, "main 中应包含 char_name"
    assert user_name in main_content, "main 中应包含 user_name"
    assert DEFAULT_FOUNDATIONAL_GOAL in main_content, "main 中应包含 foundational_goal"

    mode_content = msgs[1]["content"]
    assert char_name in mode_content, "mode 中应包含 char_name"
    assert user_name in mode_content, "mode 中应包含 user_name"
    assert DEFAULT_MAX_WORDS in mode_content, "mode 中应包含 max_words"
    assert "Roleplay Text Output Format" in mode_content, "mode 中应包含 ROLEPLAY_TEXT_OUTPUT_FORMAT 标题"
    assert 'double quotation marks ""' in mode_content or "double quotation marks" in mode_content
    assert "parentheses ()" in mode_content

    tool_content = msgs[2]["content"]
    assert "## Tool Usage" in tool_content, "第三条应为 Tool Usage 块"
    assert "erotic_scene_generate" in tool_content, "应提及 erotic_scene_generate"

    if len(msgs) > 3:
        assert msgs[3].get("role") == "system"
        assert "Photo Album" in msgs[3].get("content", "") or "photo" in msgs[3].get("content", "").lower()
