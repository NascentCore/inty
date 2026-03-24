"""记忆更新：原始流水追加 + 当日总结 LLM + MEMORY.md 策展；仅由 orchestrator 调用。"""

from __future__ import annotations

import logging
import os
import queue
import threading

from .client import complete, day_summary_model, memory_model
from .file_store import append_line, read_text, write_text_atomic
from .paths import WorkspacePaths
from .utc import utc_date_str, utc_iso_ts

logger = logging.getLogger(__name__)

_DIARY_USER_MAX = 240
_DIARY_ASSISTANT_MAX = 320
_RAW_FOR_SUMMARY_MAX = 48_000
_MEMORY_DAY_SUMMARY_CTX_MAX = 12_000

_MEMORY_CURATOR_SYSTEM = """You are a memory curator. Given the current MEMORY.md, optional current-day summary, and the latest user/assistant turn, output ONLY the full updated MEMORY.md body (markdown).

Rules:
- Preserve useful prior facts; merge new stable facts; remove clear contradictions.
- The day summary (if provided) is structured notes for today; use it to extract stable long-term facts when appropriate.
- Stay concise (at most about 2000 characters of substantive content).
- Output raw markdown only: no preamble, no code fences around the whole document.
"""

_DAY_SUMMARY_SYSTEM = """You are a day memory summarizer. You maintain a single markdown file for the calendar day: structured, human-readable notes (not a raw chat log).

Given the previous version of that file (may be empty), today's raw diary lines, and the latest user/assistant turn, output ONLY the full updated markdown body for that day.

Rules:
- Use Markdown: a top-level date title (# YYYY-MM-DD), then ## sections for themes (e.g. 互动模式, 工作记录), optional ## 亲密记录 with subsections for distinct scenes if relevant, optional time-of-day ## 上午/下午/晚上 when helpful.
- Merge and deduplicate; update contradictions; keep high-signal facts and user preferences.
- Bullet lines may start with "- 用户" / "- " to record key points; avoid repeating the same fact many times.
- Stay within roughly 8000 characters of substantive content unless the day requires more.
- Output raw markdown only: no preamble, no code fences around the whole document.
- Write in the same language as the conversation (usually Chinese for Chinese user content).
"""


def _day_summary_disabled() -> bool:
    return os.getenv("INTY_V2_PROTO_DAY_SUMMARY_DISABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _clip(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _raw_for_summary_prompt(raw: str) -> str:
    if len(raw) <= _RAW_FOR_SUMMARY_MAX:
        return raw
    return (
        "(Earlier lines omitted; tail only.)\n\n"
        + raw[-(_RAW_FOR_SUMMARY_MAX - 80) :]
    )


def _append_diary(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    day = utc_date_str()
    diary_path = paths.memory_raw_diary(day)
    line = (
        f"[{utc_iso_ts()}] 用户: {_clip(user_text, _DIARY_USER_MAX)} / "
        f"助手: {_clip(assistant_text, _DIARY_ASSISTANT_MAX)}"
    )
    append_line(diary_path, line)


def _rewrite_day_summary_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    if _day_summary_disabled():
        return
    day = utc_date_str()
    summary_path = paths.memory_day_summary(day)
    raw_path = paths.memory_raw_diary(day)
    raw_full = read_text(raw_path) if raw_path.is_file() else ""
    prev_summary = read_text(summary_path) if summary_path.is_file() else ""
    user_block = (
        f"Previous day summary (memory/{day}.md):\n\n{prev_summary}\n\n"
        f"---\n\nToday's raw diary (memory/daily/{day}.md):\n\n"
        f"{_raw_for_summary_prompt(raw_full)}\n\n"
        f"---\n\nLatest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages = [
        {"role": "system", "content": _DAY_SUMMARY_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete(messages, model=day_summary_model())
    write_text_atomic(summary_path, new_body.strip() + "\n")


def _rewrite_memory_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    day = utc_date_str()
    summary_path = paths.memory_day_summary(day)
    day_summary_ctx = ""
    if summary_path.is_file():
        ds = read_text(summary_path)
        if len(ds) > _MEMORY_DAY_SUMMARY_CTX_MAX:
            day_summary_ctx = ds[: _MEMORY_DAY_SUMMARY_CTX_MAX - 1] + "…"
        else:
            day_summary_ctx = ds
    memory_body = read_text(paths.memory_md)
    user_block = (
        f"Current day summary (memory/{day}.md):\n\n{day_summary_ctx}\n\n---\n\n"
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
    _rewrite_day_summary_md(paths, user_text=user_text, assistant_text=assistant_text)
    _rewrite_memory_md(paths, user_text=user_text, assistant_text=assistant_text)


_memory_queue: queue.Queue[tuple[WorkspacePaths, str, str]] | None = None
_worker_lock = threading.Lock()


def _memory_worker_loop() -> None:
    assert _memory_queue is not None
    while True:
        paths, user_text, assistant_text = _memory_queue.get()
        try:
            memory_update_after_turn(
                paths, user_text=user_text, assistant_text=assistant_text
            )
        except Exception:
            logger.exception("memory_update_after_turn failed")
        finally:
            _memory_queue.task_done()


def schedule_memory_update_after_turn(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    """Enqueue raw diary + day summary + MEMORY curator; daemon thread; REPL 不阻塞。"""
    global _memory_queue
    with _worker_lock:
        if _memory_queue is None:
            _memory_queue = queue.Queue()
            threading.Thread(
                target=_memory_worker_loop,
                name="inty-memory-update",
                daemon=True,
            ).start()
    _memory_queue.put((paths, user_text, assistant_text))
