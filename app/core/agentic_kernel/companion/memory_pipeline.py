"""记忆更新管线：日记追加、按间隔的当日总结与 MEMORY/USER/SOUL 策展。"""

from __future__ import annotations

import json
import queue
import re
import threading
import time
from collections.abc import Callable
from typing import Any

from loguru import logger
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field

from .bootstrap_user_interactive import (
    soul_prompt_is_locked_after_interactive_bootstrap,
)
from .memory_store import MemoryStore
from .utc import local_date_str, local_iso_ts
from .workspace import WorkspacePaths

_DIARY_USER_MAX = 240
_DIARY_ASSISTANT_MAX = 320
_RAW_FOR_SUMMARY_MAX = 48_000
_MEMORY_DAY_SUMMARY_CTX_MAX = 12_000
_SOUL_MEMORY_CTX_MAX = 12_000

_SOUL_FROZEN_APPEARANCE_MARKER = "<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>"

_SOUL_FUNDAMENTAL_SIGNAL_RE = re.compile(
    r"底线|边界|原则|相处模式|互动模式|角色设定|基础模式|"
    r"IDENTITY\.md|SOUL\.md|USER\.md|"
    r"无法满足|不舒服|拒绝|不能满足|"
    r"创造者模式|亲密模式|正经做事|重启|"
    r"workspace_write_file|workspace_read_file",
    re.IGNORECASE,
)
_SOUL_FUNDAMENTAL_SIGNAL_EN_RE = re.compile(r"\bSOUL\b|\bIDENTITY\b|\bBOUNDARY\b")

_MEMORY_CURATOR_SYSTEM = """You are a memory curator. Given the current MEMORY.md, optional current-day summary, and the latest user/assistant turn, output ONLY the full updated MEMORY.md body (markdown).

Rules:
- Preserve useful prior facts; merge new stable facts; remove clear contradictions.
- The day summary (if provided) is structured notes for today; use it to extract stable long-term facts when appropriate.
- Stay concise (at most about 2000 characters of substantive content).
- **## 事件日志** (if present): Record only **important** events—outcomes, agreements, boundary shifts, failures, durable facts. **Do not** log turn-by-turn play-by-play, micro body language, facial expressions, voice tone, or posture. Merge same-day trivia into one line per theme when possible.
- **## 稳定事实** (if present): Short durable patterns only; **do not** duplicate the event log with extra scenic detail. One sentence per bullet where possible; avoid enumerating trivial reactions.
- Output raw markdown only: no preamble, no code fences around the whole document.
"""

_SOUL_CURATOR_SYSTEM = """You are a SOUL document curator. SOUL.md is injected into the assistant's system prompt on every turn; it must stay aligned with durable values, boundaries, consent/safety lines, and persistent interaction commitments.

You are only invoked when this turn already signals a **fundamental interaction mode / values / boundaries** change (see user message: latest turn). Your job is to update **only** those durable commitments—not scene play-by-play, not episodic flavor, not visual/physical 形象 or 外貌.

Given the current SOUL.md (the `<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>` line is a merge slot—see below), the latest MEMORY.md (after this turn's memory step, for consistency), and the latest user/assistant turn, output ONLY the full updated SOUL.md body (markdown).

Hard requirements (must follow):
- **Never** add, remove, or edit content about **形象、外貌、发型、瞳色、身材、服装、长相** except by leaving the merge marker untouched. Do not create new sections for visual appearance.
- The input may contain exactly one line `<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>` where a user-maintained 形象 block was removed. Your output MUST contain that exact line once; do not delete or alter it.
- If the assistant's reply in the latest turn states refusal, firm limits, non-negotiable boundaries, discomfort, or that some requests cannot be met (e.g. 无法满足、边界、保留、不越过、不舒服、存在方式), you MUST consolidate those into concrete bullets under `## 底线` (or rename `## 底线（待你定义）` to `## 底线` and fill it). The next model turn must be able to read stable limits without relying on chat history.
- If the user pushes for total compliance / "满足一切幻想" / similar and the assistant declines or redirects, record the assistant's stance under `## 底线` and, if helpful, one line under `## 核心` on mutual pacing (e.g. 彼此都舒服).
- Do NOT leave placeholder-only `## 底线（待你定义）` sections unchanged when the assistant has already defined limits in this turn—replace placeholders with real bullets.
- Do not paste raw chat; paraphrase into short durable rules.

Other rules:
- Preserve useful existing content; merge and deduplicate; resolve contradictions in favor of the clearest, most recent mutually stable stance.
- Stay concise (substantive content at most about 4000 characters unless the existing SOUL is already longer—then preserve length).
- If this turn does not actually require a change to durable values or mode (you would only duplicate what is already there), return the current SOUL.md unchanged (verbatim aside from trivial whitespace)—including the merge marker line if present.
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


class MemoryPipelineConfig(BaseModel):
    day_summary_every_n_turns: int = Field(default=100, ge=1)
    memory_update_every_n_turns: int = Field(default=100, ge=1)
    user_update_every_n_turns: int = Field(default=100, ge=1)
    soul_update_every_n_turns: int = Field(default=100, ge=1)
    day_summary_disabled: bool = False
    user_update_disabled: bool = False
    soul_update_disabled: bool = False
    soul_require_fundamental_signal: bool = True


def _bump_memory_pipeline_turn(paths: WorkspacePaths, store: MemoryStore) -> int:
    rel = paths.memory_pipeline_state_json.relative_to(paths.root).as_posix()
    data: dict[str, object] = {}
    raw = store.read_document_if_exists(rel)
    if raw is not None and raw.strip():
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError(
                f"{rel} must be a JSON object with optional key turns_completed (int)"
            )
        data = loaded
    prev = int(data.get("turns_completed", 0))
    n = prev + 1
    data["turns_completed"] = n
    store.write_document(rel, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return n


def _soul_turn_has_fundamental_signal(user_text: str, assistant_text: str) -> bool:
    combined = f"{user_text}\n{assistant_text}"
    if _SOUL_FUNDAMENTAL_SIGNAL_RE.search(combined):
        return True
    return _SOUL_FUNDAMENTAL_SIGNAL_EN_RE.search(combined) is not None


def _split_soul_appearance_section(soul_body: str) -> tuple[str, str | None]:
    lines = soul_body.splitlines(keepends=True)
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and "形象" in line:
            start_idx = i
            break
    if start_idx is None:
        return soul_body, None
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if lines[j].startswith("## "):
            end_idx = j
            break
    before = "".join(lines[:start_idx])
    frozen = "".join(lines[start_idx:end_idx])
    after = "".join(lines[end_idx:])
    if before and not before.endswith("\n"):
        before += "\n"
    curator_doc = before + _SOUL_FROZEN_APPEARANCE_MARKER + "\n" + after
    return curator_doc, frozen


def _merge_soul_frozen_appearance(curator_out: str, frozen: str) -> str:
    if curator_out.count(_SOUL_FROZEN_APPEARANCE_MARKER) != 1:
        raise ValueError(
            "SOUL curator output must contain the frozen appearance marker exactly once"
        )
    return curator_out.replace(_SOUL_FROZEN_APPEARANCE_MARKER, frozen.rstrip("\n"), 1)


def _clip(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _raw_for_summary_prompt(raw: str) -> str:
    if len(raw) <= _RAW_FOR_SUMMARY_MAX:
        return raw
    return (
        "(Earlier lines omitted; tail only.)\n\n" + raw[-(_RAW_FOR_SUMMARY_MAX - 80) :]
    )


def _append_diary(
    paths: WorkspacePaths,
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    day = local_date_str()
    rel = f"memory/daily/{day}.md"
    line = (
        f"[{local_iso_ts()}] 用户: {_clip(user_text, _DIARY_USER_MAX)} / "
        f"助手: {_clip(assistant_text, _DIARY_ASSISTANT_MAX)}"
    )
    store.append_line(rel, line)


def _rewrite_day_summary_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    config: MemoryPipelineConfig,
) -> None:
    if config.day_summary_disabled:
        return
    day = local_date_str()
    raw_full = store.read_document_if_exists(f"memory/daily/{day}.md") or ""
    prev_summary = store.read_document_if_exists(f"memory/{day}.md") or ""
    user_block = (
        f"Previous day summary (memory/{day}.md):\n\n{prev_summary}\n\n"
        f"---\n\nToday's raw diary (memory/daily/{day}.md):\n\n"
        f"{_raw_for_summary_prompt(raw_full)}\n\n"
        f"---\n\nLatest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _DAY_SUMMARY_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "day_summary")
    store.write_document(f"memory/{day}.md", new_body.strip() + "\n")


def _rewrite_memory_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    day = local_date_str()
    day_summary_ctx = ""
    ds = store.read_document_if_exists(f"memory/{day}.md")
    if ds is not None:
        if len(ds) > _MEMORY_DAY_SUMMARY_CTX_MAX:
            day_summary_ctx = ds[: _MEMORY_DAY_SUMMARY_CTX_MAX - 1] + "…"
        else:
            day_summary_ctx = ds
    memory_body = store.read_document("MEMORY.md")
    user_block = (
        f"Current day summary (memory/{day}.md):\n\n{day_summary_ctx}\n\n---\n\n"
        f"Current MEMORY.md:\n\n{memory_body}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _MEMORY_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "memory")
    store.write_document("MEMORY.md", new_body.strip() + "\n")


def _rewrite_user_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    config: MemoryPipelineConfig,
) -> None:
    if config.user_update_disabled:
        return
    user_body = store.read_document("USER.md")
    memory_body = store.read_document("MEMORY.md")
    if len(memory_body) > _SOUL_MEMORY_CTX_MAX:
        memory_ctx = memory_body[: _SOUL_MEMORY_CTX_MAX - 1] + "…"
    else:
        memory_ctx = memory_body
    user_block = (
        f"Current USER.md:\n\n{user_body}\n\n---\n\n"
        f"Current MEMORY.md (long-term, for consistency):\n\n{memory_ctx}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _USER_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "user")
    store.write_document("USER.md", new_body.strip() + "\n")


def _rewrite_soul_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    config: MemoryPipelineConfig,
) -> None:
    if config.soul_update_disabled:
        return
    soul_body = store.read_document("SOUL.md")
    curator_doc, frozen_appearance = _split_soul_appearance_section(soul_body)
    memory_body = store.read_document("MEMORY.md")
    if len(memory_body) > _SOUL_MEMORY_CTX_MAX:
        memory_ctx = memory_body[: _SOUL_MEMORY_CTX_MAX - 1] + "…"
    else:
        memory_ctx = memory_body
    user_block = (
        f"Current SOUL.md:\n\n{curator_doc}\n\n---\n\n"
        f"Current MEMORY.md (long-term, for consistency):\n\n{memory_ctx}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SOUL_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "soul")
    new_body = new_body.strip()
    if frozen_appearance is not None:
        new_body = _merge_soul_frozen_appearance(new_body, frozen_appearance)
    store.write_document("SOUL.md", new_body.strip() + "\n")


def memory_update_after_turn(
    paths: WorkspacePaths,
    store: MemoryStore,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    config: MemoryPipelineConfig,
) -> None:
    t_all = time.perf_counter()
    ws = paths.root.name
    turn_n = _bump_memory_pipeline_turn(paths, store)
    every_n = config.day_summary_every_n_turns
    user_every_n = config.user_update_every_n_turns
    memory_every_n = config.memory_update_every_n_turns
    soul_every_n = config.soul_update_every_n_turns
    logger.info(
        "memory_pipeline start ws={} turn={} day_summary_every_n={} "
        "memory_update_every_n={} user_update_every_n={} soul_update_every_n={} "
        "day_summary_disabled={} user_update_disabled={} soul_update_disabled={}",
        ws,
        turn_n,
        every_n,
        memory_every_n,
        user_every_n,
        soul_every_n,
        config.day_summary_disabled,
        config.user_update_disabled,
        config.soul_update_disabled,
    )
    logger.debug(
        "memory_pipeline turn_preview user_chars={} assistant_chars={} user={} assistant={}",
        len(user_text),
        len(assistant_text),
        _clip(user_text, 160),
        _clip(assistant_text, 160),
    )

    t = time.perf_counter()
    _append_diary(paths, store, user_text=user_text, assistant_text=assistant_text)
    logger.info(
        "memory_pipeline step=append_diary ms={:.0f} ws={}",
        (time.perf_counter() - t) * 1000.0,
        ws,
    )

    t = time.perf_counter()
    run_day_summary_llm = (not config.day_summary_disabled) and (turn_n % every_n == 0)
    if run_day_summary_llm:
        _rewrite_day_summary_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
            config=config,
        )
    elif not config.day_summary_disabled:
        logger.debug(
            "memory_pipeline step=day_summary_md skipped turn={} every_n={} ws={}",
            turn_n,
            every_n,
            ws,
        )
    logger.info(
        "memory_pipeline step=day_summary_md ms={:.0f} ws={} ran_llm={}",
        (time.perf_counter() - t) * 1000.0,
        ws,
        run_day_summary_llm,
    )

    t = time.perf_counter()
    run_memory_llm = turn_n % memory_every_n == 0
    if run_memory_llm:
        _rewrite_memory_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
    else:
        logger.debug(
            "memory_pipeline step=memory_md skipped turn={} every_n={} ws={}",
            turn_n,
            memory_every_n,
            ws,
        )
    logger.info(
        "memory_pipeline step=memory_md ms={:.0f} ws={} ran_llm={}",
        (time.perf_counter() - t) * 1000.0,
        ws,
        run_memory_llm,
    )

    t = time.perf_counter()
    run_user_llm = (not config.user_update_disabled) and (turn_n % user_every_n == 0)
    if run_user_llm:
        _rewrite_user_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
            config=config,
        )
    elif not config.user_update_disabled:
        logger.debug(
            "memory_pipeline step=user_md skipped turn={} every_n={} ws={}",
            turn_n,
            user_every_n,
            ws,
        )
    logger.info(
        "memory_pipeline step=user_md ms={:.0f} ws={} ran_llm={}",
        (time.perf_counter() - t) * 1000.0,
        ws,
        run_user_llm,
    )

    t = time.perf_counter()
    soul_interval_hits = (not config.soul_update_disabled) and (
        turn_n % soul_every_n == 0
    )
    soul_signal_ok = (not config.soul_require_fundamental_signal) or (
        _soul_turn_has_fundamental_signal(user_text, assistant_text)
    )
    soul_locked = soul_prompt_is_locked_after_interactive_bootstrap(store=store)
    run_soul_llm = (not soul_locked) and soul_interval_hits and soul_signal_ok
    if run_soul_llm:
        _rewrite_soul_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
            config=config,
        )
    elif soul_locked and soul_interval_hits:
        logger.debug(
            "memory_pipeline step=soul_md skipped turn={} every_n={} ws={} reason=soul_locked_after_interactive_bootstrap",
            turn_n,
            soul_every_n,
            ws,
        )
    elif soul_interval_hits and not soul_signal_ok:
        logger.debug(
            "memory_pipeline step=soul_md skipped turn={} every_n={} ws={} reason=no_fundamental_signal",
            turn_n,
            soul_every_n,
            ws,
        )
    elif not config.soul_update_disabled:
        logger.debug(
            "memory_pipeline step=soul_md skipped turn={} every_n={} ws={}",
            turn_n,
            soul_every_n,
            ws,
        )
    logger.info(
        "memory_pipeline step=soul_md ms={:.0f} ws={} ran_llm={}",
        (time.perf_counter() - t) * 1000.0,
        ws,
        run_soul_llm,
    )

    logger.info(
        "memory_pipeline done total_ms={:.0f} ws={}",
        (time.perf_counter() - t_all) * 1000.0,
        ws,
    )


_MEMORY_WORKER_ERRORS: tuple[type[BaseException], ...] = (
    APIError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    OSError,
    ValueError,
    json.JSONDecodeError,
    TypeError,
    KeyError,
    RuntimeError,
    FileNotFoundError,
)

_memory_queue: (
    queue.Queue[
        tuple[
            WorkspacePaths,
            MemoryStore,
            str,
            str,
            Callable[[list[dict[str, Any]], str], str],
            MemoryPipelineConfig,
        ]
    ]
    | None
) = None
_worker_lock = threading.Lock()


def _memory_worker_loop() -> None:
    assert _memory_queue is not None
    while True:
        paths, store, user_text, assistant_text, complete_fn, config = (
            _memory_queue.get()
        )
        t_job = time.perf_counter()
        logger.debug(
            "memory_pipeline worker_job_start ws={} user_chars={} assistant_chars={}",
            paths.root.name,
            len(user_text),
            len(assistant_text),
        )
        try:
            memory_update_after_turn(
                paths,
                store,
                user_text,
                assistant_text,
                complete_fn,
                config,
            )
        except _MEMORY_WORKER_ERRORS:
            logger.exception("memory_update_after_turn failed")
        finally:
            logger.info(
                "memory_pipeline worker_job wall_ms={:.0f} ws={}",
                (time.perf_counter() - t_job) * 1000.0,
                paths.root.name,
            )
            _memory_queue.task_done()


def schedule_memory_update_after_turn(
    paths: WorkspacePaths,
    store: MemoryStore,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    config: MemoryPipelineConfig,
) -> None:
    global _memory_queue
    with _worker_lock:
        if _memory_queue is None:
            _memory_queue = queue.Queue()
            threading.Thread(
                target=_memory_worker_loop,
                name="companion-memory-update",
                daemon=True,
            ).start()
    _memory_queue.put(
        (paths, store, user_text, assistant_text, complete_fn, config),
    )
    logger.info(
        "memory_pipeline enqueued ws={} pending_jobs={}",
        paths.root.name,
        _memory_queue.qsize(),
    )
    logger.debug(
        "memory_pipeline enqueue_preview ws={} user={} assistant={}",
        paths.root.name,
        _clip(user_text, 120),
        _clip(assistant_text, 120),
    )
