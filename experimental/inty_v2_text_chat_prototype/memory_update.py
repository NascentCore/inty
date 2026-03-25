"""记忆更新：原始流水追加 + 当日总结 LLM + MEMORY.md 策展 + USER.md 策展 + SOUL.md 策展；仅由 orchestrator 调用。"""

from __future__ import annotations

import logging
import os
import queue
import threading

from .client import complete, day_summary_model, memory_model, soul_model, user_model
from .file_store import append_line, read_text, write_text_atomic
from .paths import WorkspacePaths
from .utc import local_date_str, local_iso_ts

logger = logging.getLogger(__name__)

_DIARY_USER_MAX = 240
_DIARY_ASSISTANT_MAX = 320
_RAW_FOR_SUMMARY_MAX = 48_000
_MEMORY_DAY_SUMMARY_CTX_MAX = 12_000
_SOUL_MEMORY_CTX_MAX = 12_000

_MEMORY_CURATOR_SYSTEM = """You are a memory curator. Given the current MEMORY.md, optional current-day summary, and the latest user/assistant turn, output ONLY the full updated MEMORY.md body (markdown).

Rules:
- Preserve useful prior facts; merge new stable facts; remove clear contradictions.
- The day summary (if provided) is structured notes for today; use it to extract stable long-term facts when appropriate.
- Stay concise (at most about 2000 characters of substantive content).
- Output raw markdown only: no preamble, no code fences around the whole document.
"""

_SOUL_CURATOR_SYSTEM = """You are a SOUL document curator. SOUL.md is injected into the assistant's system prompt on every turn; it must stay aligned with durable values, boundaries, consent/safety lines, and persistent interaction commitments.

Given the current SOUL.md, the latest MEMORY.md (after this turn's memory step, for consistency), and the latest user/assistant turn, output ONLY the full updated SOUL.md body (markdown).

Hard requirements (must follow):
- If the assistant's reply in the latest turn states refusal, firm limits, non-negotiable boundaries, discomfort, or that some requests cannot be met (e.g. 无法满足、边界、保留、不越过、不舒服、存在方式), you MUST consolidate those into concrete bullets under `## 底线` (or rename `## 底线（待你定义）` to `## 底线` and fill it). The next model turn must be able to read stable limits without relying on chat history.
- If the user pushes for total compliance / "满足一切幻想" / similar and the assistant declines or redirects, record the assistant's stance under `## 底线` and, if helpful, one line under `## 核心` on mutual pacing (e.g. 彼此都舒服).
- Do NOT leave placeholder-only `## 底线（待你定义）` sections unchanged when the assistant has already defined limits in this turn—replace placeholders with real bullets.
- Do not paste raw chat; paraphrase into short durable rules.

Other rules:
- Preserve useful existing content; merge and deduplicate; resolve contradictions in favor of the clearest, most recent mutually stable stance.
- Stay concise (substantive content at most about 4000 characters unless the existing SOUL is already longer—then preserve length).
- If the latest turn is purely small talk with no boundary or values content, return the current SOUL.md unchanged (verbatim aside from trivial whitespace).
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

_USER_CURATOR_SYSTEM = """You are a USER.md curator. USER.md records the assistant's durable understanding of the user (how to address them, preferences, collaboration habits). It is injected into the system prompt as ## USER on every turn.

Given the current USER.md, the latest MEMORY.md (already updated this turn for consistency), and the latest user/assistant turn, output ONLY the full updated USER.md body (markdown).

Rules:
- Preserve the document's intended structure and tone: keep section headings such as `# USER.md - 关于你的用户`, `## 身份信息`, `## 慢慢了解的事`, `## 延续` unless the file uses a simpler template—do not strip guiding prose that sets boundaries (e.g. 知人方能善助).
- Merge new stable facts into the appropriate sections; deduplicate; resolve contradictions in favor of the clearest, most recent mutually stable information.
- Use MEMORY.md as supporting context for facts; do not paste raw chat—paraphrase into short durable lines.
- Stay concise (substantive content at most about 4000 characters unless the existing USER.md is already longer—then preserve length).
- If the latest turn is purely small talk with no new durable user-facing facts or preferences, return the current USER.md unchanged (verbatim aside from trivial whitespace).
- Output raw markdown only: no preamble, no code fences around the whole document.
- Write in the same language as USER.md and the conversation (usually Chinese for Chinese content).
"""


def _day_summary_disabled() -> bool:
    return os.getenv("INTY_V2_PROTO_DAY_SUMMARY_DISABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _soul_update_disabled() -> bool:
    return os.getenv("INTY_V2_PROTO_SOUL_UPDATE_DISABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _user_update_disabled() -> bool:
    return os.getenv("INTY_V2_PROTO_USER_UPDATE_DISABLED", "").strip().lower() in (
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
    day = local_date_str()
    diary_path = paths.memory_raw_diary(day)
    line = (
        f"[{local_iso_ts()}] 用户: {_clip(user_text, _DIARY_USER_MAX)} / "
        f"助手: {_clip(assistant_text, _DIARY_ASSISTANT_MAX)}"
    )
    append_line(diary_path, line)


def _rewrite_day_summary_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool,
) -> None:
    if _day_summary_disabled():
        return
    day = local_date_str()
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
    new_body = complete(
        messages,
        model=day_summary_model(),
        llm_trace=llm_trace,
        trace_where="memory.day_summary",
        ws_label=paths.root.name,
        trace_day=local_date_str(),
    )
    write_text_atomic(summary_path, new_body.strip() + "\n")


def _rewrite_memory_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool,
) -> None:
    day = local_date_str()
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
    new_body = complete(
        messages,
        model=memory_model(),
        llm_trace=llm_trace,
        trace_where="memory.curator",
        ws_label=paths.root.name,
        trace_day=local_date_str(),
    )
    write_text_atomic(paths.memory_md, new_body.strip() + "\n")


def _rewrite_user_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool,
) -> None:
    if _user_update_disabled():
        return
    user_body = read_text(paths.user_md)
    memory_body = read_text(paths.memory_md)
    if len(memory_body) > _SOUL_MEMORY_CTX_MAX:
        memory_ctx = memory_body[: _SOUL_MEMORY_CTX_MAX - 1] + "…"
    else:
        memory_ctx = memory_body
    user_block = (
        f"Current USER.md:\n\n{user_body}\n\n---\n\n"
        f"Current MEMORY.md (long-term, for consistency):\n\n{memory_ctx}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages = [
        {"role": "system", "content": _USER_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete(
        messages,
        model=user_model(),
        llm_trace=llm_trace,
        trace_where="memory.user",
        ws_label=paths.root.name,
        trace_day=local_date_str(),
    )
    write_text_atomic(paths.user_md, new_body.strip() + "\n")


def _rewrite_soul_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool,
) -> None:
    if _soul_update_disabled():
        return
    soul_body = read_text(paths.soul)
    memory_body = read_text(paths.memory_md)
    if len(memory_body) > _SOUL_MEMORY_CTX_MAX:
        memory_ctx = memory_body[: _SOUL_MEMORY_CTX_MAX - 1] + "…"
    else:
        memory_ctx = memory_body
    user_block = (
        f"Current SOUL.md:\n\n{soul_body}\n\n---\n\n"
        f"Current MEMORY.md (long-term, for consistency):\n\n{memory_ctx}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages = [
        {"role": "system", "content": _SOUL_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete(
        messages,
        model=soul_model(),
        llm_trace=llm_trace,
        trace_where="memory.soul",
        ws_label=paths.root.name,
        trace_day=local_date_str(),
    )
    write_text_atomic(paths.soul, new_body.strip() + "\n")


def memory_update_after_turn(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool = False,
) -> None:
    _append_diary(paths, user_text=user_text, assistant_text=assistant_text)
    _rewrite_day_summary_md(
        paths,
        user_text=user_text,
        assistant_text=assistant_text,
        llm_trace=llm_trace,
    )
    _rewrite_memory_md(
        paths,
        user_text=user_text,
        assistant_text=assistant_text,
        llm_trace=llm_trace,
    )
    _rewrite_user_md(
        paths,
        user_text=user_text,
        assistant_text=assistant_text,
        llm_trace=llm_trace,
    )
    _rewrite_soul_md(
        paths,
        user_text=user_text,
        assistant_text=assistant_text,
        llm_trace=llm_trace,
    )


_memory_queue: queue.Queue[tuple[WorkspacePaths, str, str, bool]] | None = None
_worker_lock = threading.Lock()


def _memory_worker_loop() -> None:
    assert _memory_queue is not None
    while True:
        paths, user_text, assistant_text, llm_trace = _memory_queue.get()
        try:
            memory_update_after_turn(
                paths,
                user_text=user_text,
                assistant_text=assistant_text,
                llm_trace=llm_trace,
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
    llm_trace: bool = False,
) -> None:
    """Enqueue raw diary + day summary + MEMORY/USER/SOUL curator; daemon thread; REPL 不阻塞。"""
    global _memory_queue
    with _worker_lock:
        if _memory_queue is None:
            _memory_queue = queue.Queue()
            threading.Thread(
                target=_memory_worker_loop,
                name="inty-memory-update",
                daemon=True,
            ).start()
    _memory_queue.put((paths, user_text, assistant_text, llm_trace))
