# 模板替换工具：支持按占位符所在行缩进折叠多行替换值。
# 与 Jinja2 不同，仅做 {{ name }} 的简单替换，便于在 prompt 中嵌入多行内容并保持缩进。

from __future__ import annotations

import re
from typing import Any


# 匹配 {{ 标识符 }}，允许标识符前后有空格
_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _get_line_indent(template: str, position: int) -> str:
    """返回 template 中 position 所在行的行首空白（不含换行）。"""
    line_start = template.rfind("\n", 0, position)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1  # 从换行符后开始
    end = position
    indent_len = 0
    while line_start + indent_len < end and template[line_start + indent_len] in " \t":
        indent_len += 1
    return template[line_start : line_start + indent_len]


def _indented_value(value: str, line_indent: str) -> str:
    """对多行 value：首行不加重 indentation（占位符已在缩进行内），后续行每行前加 line_indent。单行则原样返回。"""
    value = value.strip()
    if "\n" not in value:
        return value
    lines = value.split("\n")
    # 首行直接接在占位符后（该行已有缩进），仅后续行前加 line_indent
    return lines[0] + "\n" + "\n".join(line_indent + line for line in lines[1:])


def render_template_with_indent(template: str, **kwargs: Any) -> str:
    """
    将模板中的 {{ name }} 占位符替换为 kwargs 中对应值；若值为多行，则按占位符所在行的缩进折叠后续行。

    示例:
        template = \"\"\"
        I am {{ char }}, I have been many places:
          {{ places }}
        \"\"\"
        render_template_with_indent(template, char="Yaxiong", places="- Beijing\\n- New York\\n- etc.")
        =>
        I am Yaxiong, I have been many places:
          - Beijing
          - New York
          - etc.
    """
    # 从后往前替换，避免偏移变化
    matches = list(_PLACEHOLDER_PATTERN.finditer(template))
    if not matches:
        return template

    result = template
    for m in reversed(matches):
        key = m.group(1)
        if key not in kwargs:
            continue
        raw = kwargs[key]
        value = str(raw).strip() if raw is not None else ""
        line_indent = _get_line_indent(result, m.start())
        replacement = _indented_value(value, line_indent)
        result = result[: m.start()] + replacement + result[m.end() :]

    return result


def strip_multiline_str(s: str) -> str:
    """
    规范化多行字符串：
    1. 去掉首部空行；
    2. 去掉尾部空行；
    3. 以“最左行”（非空行中行首空白最少的一行）为基准，去掉各行相同数量的前导缩进；
    4. 其余行相对缩进保持不变。

    例如:
        a = \"\"\"
             I am a great person
               but I am short
           haha
        \"\"\"
        strip_multiline_str(a) => \"  I am a great person\\n    but I am short\\nhaha\"
        （最左行 "   haha" 有 3 个前导空格，每行去掉 3 格后相对缩进一致）
    """
    if not s:
        return ""
    lines = s.splitlines()
    # 1. 去掉首部空行
    while lines and not lines[0].strip():
        lines.pop(0)
    # 2. 去掉尾部空行
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    # 3. 非空行中最小的行首空白长度（字符数）
    min_indent = None
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            n = len(line) - len(stripped)
            if min_indent is None or n < min_indent:
                min_indent = n
    if min_indent is None:
        min_indent = 0
    # 4. 每行最多去掉 min_indent 个前导空白字符（不足则只去掉该行已有的前导空白）
    result_lines: list[str] = []
    for line in lines:
        strip_count = 0
        for c in line:
            if strip_count < min_indent and c in " \t":
                strip_count += 1
            else:
                break
        result_lines.append(line[strip_count:])
    return "\n".join(result_lines)
