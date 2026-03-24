"""记忆更新：日记追加（A）+ 二次 LLM 覆盖 MEMORY.md（B）；仅由 orchestrator 调用。"""

from __future__ import annotations

from .client import complete, memory_model
from .file_store import append_line, read_text, write_text_atomic
from .paths import WorkspacePaths
from .utc import utc_date_str, utc_iso_ts

_DIARY_USER_MAX = 240
_DIARY_ASSISTANT_MAX = 320

_MEMORY_CURATOR_SYSTEM = """You are a memory curator. Given the current MEMORY.md and the latest user/assistant turn, output ONLY the full updated MEMORY.md body (markdown).

Rules:
- Preserve useful prior facts; merge new stable facts; remove clear contradictions.
- Stay concise (at most about 2000 characters of substantive content).
- Output raw markdown only: no preamble, no code fences around the whole document.
"""


def _clip(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _append_diary(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    day = utc_date_str()
    diary_path = paths.memory_dir / f"{day}.md"
    line = (
        f"[{utc_iso_ts()}] 用户: {_clip(user_text, _DIARY_USER_MAX)} / "
        f"助手: {_clip(assistant_text, _DIARY_ASSISTANT_MAX)}"
    )
    append_line(diary_path, line)


def _rewrite_memory_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    memory_body = read_text(paths.memory_md)
    user_block = (
        f"Current MEMORY.md:\n\n{memory_body}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages = [
        {"role": "system", "content": _MEMORY_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete(messages, model=memory_model())
    write_text_atomic(paths.memory_md, new_body.strip() + "\n")


def memory_update_after_turn(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    _append_diary(paths, user_text=user_text, assistant_text=assistant_text)
    _rewrite_memory_md(paths, user_text=user_text, assistant_text=assistant_text)
