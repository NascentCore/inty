"""记忆更新：原始流水追加 + 当日总结 LLM + MEMORY.md 策展 + USER.md 策展 + SOUL.md 策展；仅由 orchestrator 调用。"""

from __future__ import annotations

import json
import os
import queue
import re
import threading
import time

from loguru import logger

from .client import complete, day_summary_model, memory_model, soul_model, user_model
from .file_store import read_text, write_text_atomic
from .memory_store_registry import get_memory_store
from .paths import WorkspacePaths
from .utc import local_date_str, local_iso_ts

_DIARY_USER_MAX = 240
_DIARY_ASSISTANT_MAX = 320
_RAW_FOR_SUMMARY_MAX = 48_000
_MEMORY_DAY_SUMMARY_CTX_MAX = 12_000
_SOUL_MEMORY_CTX_MAX = 12_000

# 策展器输入中占位；输出必须原样保留一行，否则合并失败并抛错（避免 HTML 注释被模型吃掉）。
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


def _day_summary_disabled() -> bool:
    return os.getenv("INTY_V2_PROTO_DAY_SUMMARY_DISABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _positive_int_env(env_name: str, *, default: int = 100) -> int:
    """Read a positive integer from env; used for *EVERY_N_TURNS cadence knobs."""
    raw = os.getenv(env_name, str(default)).strip()
    if not raw:
        return default
    try:
        n = int(raw, 10)
    except ValueError as e:
        raise ValueError(
            f"{env_name} must be a positive integer, got {raw!r}"
        ) from e
    if n < 1:
        raise ValueError(f"{env_name} must be >= 1, got {n}")
    return n


def _day_summary_every_n_turns() -> int:
    """当日总结 LLM 每完成 N 次记忆管线调用跑一次；默认 100。设为 1 等价于每轮都跑。"""
    return _positive_int_env("INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS", default=100)


def _bump_memory_pipeline_turn(paths: WorkspacePaths) -> int:
    """持久化累计「记忆管线已处理轮次」，返回递增后的序号（从 1 起）。"""
    p = paths.memory_pipeline_state_json
    data: dict[str, object] = {}
    if p.is_file():
        loaded = json.loads(read_text(p))
        if not isinstance(loaded, dict):
            raise ValueError(
                f"{p} must be a JSON object with optional key turns_completed (int)"
            )
        data = loaded
    prev = int(data.get("turns_completed", 0))
    n = prev + 1
    data["turns_completed"] = n
    write_text_atomic(p, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return n


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


def _user_update_every_n_turns() -> int:
    """USER.md 策展 LLM 每完成 N 次记忆管线调用跑一次；默认 100。设为 1 等价于每轮都跑。"""
    return _positive_int_env("INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS", default=100)


def _memory_update_every_n_turns() -> int:
    """MEMORY.md 策展 LLM 每完成 N 次记忆管线调用跑一次；默认 100。设为 1 等价于每轮都跑。"""
    return _positive_int_env("INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS", default=100)


def _soul_update_every_n_turns() -> int:
    """SOUL.md 策展 LLM 每完成 N 次记忆管线调用跑一次；默认 100。设为 1 等价于每轮都跑。"""
    return _positive_int_env("INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS", default=100)


def _soul_fundamental_signal_gate_enabled() -> bool:
    """默认开启：仅当本回合对话出现「基础模式/边界/底线」等信号时才跑 SOUL 策展 LLM。"""
    val = os.getenv("INTY_V2_PROTO_SOUL_UPDATE_REQUIRE_FUNDAMENTAL_SIGNAL", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


def _soul_turn_has_fundamental_signal(user_text: str, assistant_text: str) -> bool:
    combined = f"{user_text}\n{assistant_text}"
    if _SOUL_FUNDAMENTAL_SIGNAL_RE.search(combined):
        return True
    return _SOUL_FUNDAMENTAL_SIGNAL_EN_RE.search(combined) is not None


def _split_soul_appearance_section(soul_body: str) -> tuple[str, str | None]:
    """
    若存在以 `## ` 开头且标题含「形象」的节，整节抽出（直到下一个 `## ` 或文末）。
    返回 (供策展 LLM 的正文, 被抽出的原文)；无形象节时第二项为 None。
    """
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
    get_memory_store(paths.root).append_line(rel, line)


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
    store = get_memory_store(paths.root)
    raw_full = store.read_document_if_exists(f"memory/daily/{day}.md") or ""
    prev_summary = store.read_document_if_exists(f"memory/{day}.md") or ""
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
        trace_day=day,
    )
    store.write_document(f"memory/{day}.md", new_body.strip() + "\n")


def _rewrite_memory_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool,
) -> None:
    day = local_date_str()
    store = get_memory_store(paths.root)
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
        trace_day=day,
    )
    store.write_document("MEMORY.md", new_body.strip() + "\n")


def _rewrite_user_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool,
) -> None:
    if _user_update_disabled():
        return
    store = get_memory_store(paths.root)
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
    store.write_document("USER.md", new_body.strip() + "\n")


def _rewrite_soul_md(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool,
) -> None:
    if _soul_update_disabled():
        return
    store = get_memory_store(paths.root)
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
    new_body = new_body.strip()
    if frozen_appearance is not None:
        new_body = _merge_soul_frozen_appearance(new_body, frozen_appearance)
    store.write_document("SOUL.md", new_body.strip() + "\n")


def memory_update_after_turn(
    paths: WorkspacePaths,
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool = False,
) -> None:
    t_all = time.perf_counter()
    ws = paths.root.name
    turn_n = _bump_memory_pipeline_turn(paths)
    every_n = _day_summary_every_n_turns()
    user_every_n = _user_update_every_n_turns()
    memory_every_n = _memory_update_every_n_turns()
    soul_every_n = _soul_update_every_n_turns()
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
        _day_summary_disabled(),
        _user_update_disabled(),
        _soul_update_disabled(),
    )
    logger.debug(
        "memory_pipeline turn_preview user_chars={} assistant_chars={} user={} assistant={}",
        len(user_text),
        len(assistant_text),
        _clip(user_text, 160),
        _clip(assistant_text, 160),
    )

    t = time.perf_counter()
    _append_diary(paths, user_text=user_text, assistant_text=assistant_text)
    logger.info(
        "memory_pipeline step=append_diary ms={:.0f} ws={}",
        (time.perf_counter() - t) * 1000.0,
        ws,
    )

    t = time.perf_counter()
    run_day_summary_llm = (not _day_summary_disabled()) and (turn_n % every_n == 0)
    if run_day_summary_llm:
        _rewrite_day_summary_md(
            paths,
            user_text=user_text,
            assistant_text=assistant_text,
            llm_trace=llm_trace,
        )
    elif not _day_summary_disabled():
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
            paths,
            user_text=user_text,
            assistant_text=assistant_text,
            llm_trace=llm_trace,
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
    run_user_llm = (not _user_update_disabled()) and (turn_n % user_every_n == 0)
    if run_user_llm:
        _rewrite_user_md(
            paths,
            user_text=user_text,
            assistant_text=assistant_text,
            llm_trace=llm_trace,
        )
    elif not _user_update_disabled():
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
    soul_interval_hits = (not _soul_update_disabled()) and (turn_n % soul_every_n == 0)
    soul_signal_ok = (not _soul_fundamental_signal_gate_enabled()) or _soul_turn_has_fundamental_signal(
        user_text, assistant_text
    )
    run_soul_llm = soul_interval_hits and soul_signal_ok
    if run_soul_llm:
        _rewrite_soul_md(
            paths,
            user_text=user_text,
            assistant_text=assistant_text,
            llm_trace=llm_trace,
        )
    elif soul_interval_hits and not soul_signal_ok:
        logger.debug(
            "memory_pipeline step=soul_md skipped turn={} every_n={} ws={} reason=no_fundamental_signal",
            turn_n,
            soul_every_n,
            ws,
        )
    elif not _soul_update_disabled():
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


_memory_queue: queue.Queue[tuple[WorkspacePaths, str, str, bool]] | None = None
_worker_lock = threading.Lock()


def _memory_worker_loop() -> None:
    assert _memory_queue is not None
    while True:
        paths, user_text, assistant_text, llm_trace = _memory_queue.get()
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
                user_text=user_text,
                assistant_text=assistant_text,
                llm_trace=llm_trace,
            )
        except Exception:
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
    *,
    user_text: str,
    assistant_text: str,
    llm_trace: bool = False,
) -> None:
    """Enqueue 记忆管线（日记、按间隔的当日总结与 MEMORY/USER/SOUL 策展）；daemon thread；REPL 不阻塞。"""
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
