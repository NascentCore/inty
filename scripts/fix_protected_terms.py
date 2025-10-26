#!/usr/bin/env python3
import os
import re
from pathlib import Path

ROOT = Path(os.getenv("WORKSPACE", ".")).resolve()
MD_GLOB = list(ROOT.rglob("*.md"))
INCLUDE_EXTS = {".md", ".py", ".ts", ".tsx", ".js", ".jsx", ".kt", ".kts", ".xml", ".html", ".sh"}

# 编译规则
re_heading_cursor = re.compile(r"^(\s*##\s*)光标摘要(\s*)$", re.MULTILINE)
re_title_claude_md = re.compile(r"^(\s*#\s*)Claude\.md(\s*)$", re.MULTILINE)
re_word_claude = re.compile(r"Claude")

changed_files = []

# 1) 仅在 Markdown 中修复“光标摘要”标题与 CLAUDE 标题
for md in MD_GLOB:
    try:
        text = md.read_text(encoding="utf-8")
    except Exception:
        continue
    new_text = text
    new_text = re_heading_cursor.sub(r"\1Cursor 摘要\2", new_text)
    new_text = re_title_claude_md.sub(r"\1CLAUDE.md\2", new_text)
    if new_text != text:
        md.write_text(new_text, encoding="utf-8")
        changed_files.append(str(md))

# 2) 全局将中文“Claude”替换成“Claude”（限定文件类型）
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if p.suffix not in INCLUDE_EXTS:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        continue
    if "Claude" not in text:
        continue
    new_text = re_word_claude.sub("Claude", text)
    if new_text != text:
        p.write_text(new_text, encoding="utf-8")
        changed_files.append(str(p))

print(f"fixed files: {len(set(changed_files))}")
