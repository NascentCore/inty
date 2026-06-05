"""记忆更新管线：情景记忆 episodic（``memory/daily/<date>.md`` 追加）、gist 单日摘要（``memory/<date>.md``）、
语义记忆 semantic（``MEMORY.md``）与 USER/STYLE/SOUL 策展。"""

from __future__ import annotations

import json
import queue
import threading
import time
from threading import Event
from collections.abc import Callable
from typing import Any

from loguru import logger
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field

from app.core.companion_harness.companion.llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
)
from app.core.companion_harness.companion.utc import (
    local_date_str,
    local_iso_ts,
)
from app.core.companion_harness.companion.dreaming import (
    parse_transcript_datetime,
)
from app.core.companion_harness.companion.models import ChatMessage

from .living_sphere_curator import compact_living_sphere_if_pending

from .memory_store import MemoryStore
from .memory_store_scope import DEFAULT_MEMORY_STORE_SCOPE_PATHS

_DIARY_USER_MAX = 240
_DIARY_ASSISTANT_MAX = 320
_RAW_FOR_SUMMARY_MAX = 48_000
_MEMORY_DAY_SUMMARY_CTX_MAX = 12_000
_SOUL_MEMORY_CTX_MAX = 12_000

_SOUL_FROZEN_APPEARANCE_MARKER = "<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>"

_MEMORY_CURATOR_SYSTEM = """You are a memory curator for semantic long-term memory (MEMORY.md). Given the current MEMORY.md, optional current-day gist summary (memory/<date>.md), and the latest user/assistant turn, output ONLY the full updated MEMORY.md body (markdown).

Rules:
- Preserve useful prior facts; merge new stable facts; remove clear contradictions.
- The day summary (if provided) is structured notes for today; use it to extract stable long-term facts when appropriate.
- Stay concise (at most about 2000 characters of substantive content).
- **## 事件日志** (if present): Record only **important** events—outcomes, agreements, boundary shifts, failures, durable facts. **Do not** log turn-by-turn play-by-play, micro body language, facial expressions, voice tone, or posture. Merge same-day trivia into one line per theme when possible.
- **## 稳定事实** (if present): Short durable patterns only; **do not** duplicate the event log with extra scenic detail. One sentence per bullet where possible; avoid enumerating trivial reactions.
- Output raw markdown only: no preamble, no code fences around the whole document.
"""

_SOUL_CURATOR_SYSTEM = """You are a SOUL document curator. SOUL.md is injected into the assistant's system prompt on every turn; it must stay aligned with durable values, boundaries, consent/safety lines, and persistent interaction commitments.

You run on the scheduled memory-curation turn with other long-term documents. Your job is to update **only** durable values, boundaries, and interaction commitments—not scene play-by-play, not episodic flavor, not visual/physical 形象 or 外貌.

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

_DAY_SUMMARY_SYSTEM = """You are a day memory summarizer (gist memory layer: memory/<date>.md). You maintain a single markdown file for the calendar day: structured, human-readable notes (not a raw chat log).

Given the previous version of that file (may be empty), today's raw diary lines, and the latest user/assistant turn, output ONLY the full updated markdown body for that day.

Rules:
- Use Markdown: a top-level date title (# YYYY-MM-DD), then ## sections for themes (e.g. 互动模式, 工作记录), optional ## 亲密记录 with subsections for distinct scenes if relevant, optional time-of-day ## 上午/下午/晚上 when helpful.
- Merge and deduplicate; update contradictions; keep high-signal facts and user preferences.
- Bullet lines may start with "- 用户" / "- " to record key points; avoid repeating the same fact many times.
- Stay within roughly 8000 characters of substantive content unless the day requires more.
- Output raw markdown only: no preamble, no code fences around the whole document.
- Write in the same language as the conversation (usually Chinese for Chinese user content).
"""

_USER_CURATOR_SYSTEM = """You are a USER.md curator. USER.md records the assistant's durable understanding of the user (how to address them, preferences, collaboration habits). It is injected into the system prompt as its own system message (raw USER.md body) on every turn.

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

_STYLE_CURATOR_SYSTEM = """You are a STYLE.md curator. STYLE.md is the assistant's durable **communication style** (how to speak: tone, pacing, respect for user comfort). It is injected into the companion system prompt stack as plain STYLE.md body text on every turn (no injected markdown H2 title line before the body).

The workspace STYLE.md template includes the following update rules (follow them when deciding whether and how to edit):
- 直接响应用户明确的修改指令
- 记录与用户的交互，谨慎、稳步调整
- 根据用户的情绪反应和我的思考适时调整

Given the current STYLE.md, the latest MEMORY.md (already updated this turn for consistency), and the latest user/assistant turn, output ONLY the full updated STYLE.md body (markdown).

Rules:
- Do **not** copy durable values, consent lines, or relationship commitments from SOUL.md into STYLE.md—STYLE is only **how** to communicate; SOUL remains the source for **what** the relationship stands for.
- Preserve the document's intended structure: keep headings such as `# 沟通风格`, `## 更新方式`, `## 初始（可随交互修改）` unless the file uses a simpler template—do not strip the guiding update rules block.
- Apply the three template update rules: honor explicit user requests to change style; otherwise adjust **cautiously and incrementally** from interaction; when the user's emotional signals or your reflective stance clearly warrant a tone/pacing/boundary tweak, update accordingly.
- Use MEMORY.md as supporting context; do not paste raw chat—paraphrase into short durable lines where needed.
- Stay concise (substantive content at most about 4000 characters unless the existing STYLE.md is already longer—then preserve length).
- If the latest turn is purely small talk with no new communication-style signal and no explicit style instruction, return the current STYLE.md unchanged (verbatim aside from trivial whitespace).
- Output raw markdown only: no preamble, no code fences around the whole document.
- Write in the same language as STYLE.md and the conversation (usually Chinese for Chinese content).
"""


class MemoryPipelineConfig(BaseModel):
    memory_update_every_n_turns: int = Field(default=100, ge=1)


def _bump_memory_pipeline_turn(store: MemoryStore) -> int:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_pipeline_state_json
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
    store.write_document(
        rel, json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    return n


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
    return curator_out.replace(
        _SOUL_FROZEN_APPEARANCE_MARKER, frozen.rstrip("\n"), 1
    )


def _clip(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _log_memory_pipeline_skipped(
    *,
    step: str,
    ws: str,
    turn_n: int,
    every_n: int | None = None,
    reason: str | None = None,
) -> None:
    if reason is not None:
        logger.debug(
            "memory_pipeline skipped step={} turn={} ws={} reason={}",
            step,
            turn_n,
            ws,
            reason,
        )
        return
    assert every_n is not None
    logger.debug(
        "memory_pipeline skipped step={} turn={} every_n={} ws={}",
        step,
        turn_n,
        every_n,
        ws,
    )


def _log_memory_pipeline_curated(
    *,
    step: str,
    ws: str,
    turn_n: int,
    ms: float,
) -> None:
    logger.info(
        "memory_pipeline curated step={} ms={:.0f} ws={} turn={}",
        step,
        ms,
        ws,
        turn_n,
    )


def _raw_for_summary_prompt(raw: str) -> str:
    if len(raw) <= _RAW_FOR_SUMMARY_MAX:
        return raw
    return (
        "(Earlier lines omitted; tail only.)\n\n"
        + raw[-(_RAW_FOR_SUMMARY_MAX - 80) :]
    )


def _append_diary(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
) -> None:
    """Append one line to episodic memory (memory/daily/<date>.md)."""
    day = local_date_str()
    rel = f"memory/daily/{day}.md"
    line = (
        f"[{local_iso_ts()}] 用户: {_clip(user_text, _DIARY_USER_MAX)} / "
        f"助手: {_clip(assistant_text, _DIARY_ASSISTANT_MAX)}"
    )
    store.append_line(rel, line)


def _append_dreaming_diary_entries(
    store: MemoryStore,
    *,
    rows: list[ChatMessage],
) -> None:
    """Append every dreamed transcript row to its calendar day's episodic memory."""
    for row in rows:
        day = parse_transcript_datetime(row.ts).date().isoformat()
        role = "用户" if row.role == "user" else "助手"
        line = f"[{row.ts}] {role}: {_clip(row.content, _DIARY_ASSISTANT_MAX)}"
        store.append_line(f"memory/daily/{day}.md", line)


def _dreaming_transcript_block(rows: list[ChatMessage]) -> str:
    """Render a compact transcript block for batch curation prompts."""
    lines: list[str] = []
    for row in rows:
        role = "User" if row.role == "user" else "Assistant"
        lines.append(f"[{row.ts}] {role}: {row.content}")
    return "\n".join(lines)


def _rewrite_day_summary_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
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


def _rewrite_dreaming_day_summary_md(
    store: MemoryStore,
    *,
    day: str,
    rows: list[ChatMessage],
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    raw_full = store.read_document_if_exists(f"memory/daily/{day}.md") or ""
    prev_summary = store.read_document_if_exists(f"memory/{day}.md") or ""
    user_block = (
        f"Previous day summary (memory/{day}.md):\n\n{prev_summary}\n\n"
        f"---\n\nRaw diary (memory/daily/{day}.md):\n\n"
        f"{_raw_for_summary_prompt(raw_full)}\n\n"
        f"---\n\nDreaming transcript slice:\n{_dreaming_transcript_block(rows)}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _DAY_SUMMARY_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "dreaming_day_summary")
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
) -> None:
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


def _rewrite_style_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    style_body = store.read_document("STYLE.md")
    memory_body = store.read_document("MEMORY.md")
    if len(memory_body) > _SOUL_MEMORY_CTX_MAX:
        memory_ctx = memory_body[: _SOUL_MEMORY_CTX_MAX - 1] + "…"
    else:
        memory_ctx = memory_body
    user_block = (
        f"Current STYLE.md:\n\n{style_body}\n\n---\n\n"
        f"Current MEMORY.md (long-term, for consistency):\n\n{memory_ctx}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _STYLE_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "style")
    store.write_document("STYLE.md", new_body.strip() + "\n")


def _rewrite_soul_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
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


# TODO(dreaming-curator-ownership): Move LLM-heavy long-term curation
# ownership out of the post-turn pipeline once sleeping-state dreaming is
# product-stable. Today ``memory_update_after_turn`` and
# ``memory_update_after_dreaming`` both call the same curator prompts for
# ``memory/<date>.md``, ``MEMORY.md``, ``USER.md``, ``STYLE.md``, and
# ``SOUL.md``. That means a chat segment can be interpreted once during an
# awake post-turn curation tick and again during a later sleeping dream.
# Keep the immediate post-turn path for cheap, lossless capture such as raw
# diary append and state needed by active conversation, but make dreaming the
# batch consolidation owner for durable memory docs: day summary, semantic
# memory, user understanding, communication style, and relationship/personality
# boundaries. When cleaning this up, also define the handoff invariant clearly:
# raw chat should stay auditably preserved in transcript, raw diary can be
# appended promptly, and checkpoint advancement must happen only after dreaming
# has successfully consolidated the slice.
def memory_update_after_turn(
    store: MemoryStore,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    config: MemoryPipelineConfig,
    *,
    tool_bg_idle_event: Event,
) -> bool:
    """Run post-turn memory pipeline. Returns True if any LLM curation step ran."""
    t_all = time.perf_counter()
    ws = store.scope.registry_key()
    turn_n = _bump_memory_pipeline_turn(store)
    every_n = config.memory_update_every_n_turns
    curation_turn = turn_n % every_n == 0
    logger.debug(
        "memory_pipeline start ws={} turn={} memory_update_every_n={} curation_turn={}",
        ws,
        turn_n,
        every_n,
        curation_turn,
    )
    logger.debug(
        "memory_pipeline turn_preview user_chars={} assistant_chars={} user={} assistant={}",
        len(user_text),
        len(assistant_text),
        _clip(user_text, 160),
        _clip(assistant_text, 160),
    )

    t = time.perf_counter()
    _append_diary(store, user_text=user_text, assistant_text=assistant_text)
    logger.debug(
        "memory_pipeline append_diary ms={:.0f} ws={} turn={}",
        (time.perf_counter() - t) * 1000.0,
        ws,
        turn_n,
    )

    any_curation = False

    t = time.perf_counter()
    if curation_turn:
        _rewrite_day_summary_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_memory_pipeline_curated(
            step="day_summary_md",
            ws=ws,
            turn_n=turn_n,
            ms=(time.perf_counter() - t) * 1000.0,
        )
    else:
        _log_memory_pipeline_skipped(
            step="day_summary_md", ws=ws, turn_n=turn_n, every_n=every_n
        )

    t = time.perf_counter()
    if curation_turn:
        _rewrite_memory_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_memory_pipeline_curated(
            step="memory_md",
            ws=ws,
            turn_n=turn_n,
            ms=(time.perf_counter() - t) * 1000.0,
        )
    else:
        _log_memory_pipeline_skipped(
            step="memory_md", ws=ws, turn_n=turn_n, every_n=every_n
        )

    t = time.perf_counter()
    if curation_turn:
        _rewrite_user_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_memory_pipeline_curated(
            step="user_md",
            ws=ws,
            turn_n=turn_n,
            ms=(time.perf_counter() - t) * 1000.0,
        )
    else:
        _log_memory_pipeline_skipped(
            step="user_md", ws=ws, turn_n=turn_n, every_n=every_n
        )

    t = time.perf_counter()
    if curation_turn:
        _rewrite_style_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_memory_pipeline_curated(
            step="style_md",
            ws=ws,
            turn_n=turn_n,
            ms=(time.perf_counter() - t) * 1000.0,
        )
    else:
        _log_memory_pipeline_skipped(
            step="style_md", ws=ws, turn_n=turn_n, every_n=every_n
        )

    t = time.perf_counter()
    if curation_turn:
        _rewrite_soul_md(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_memory_pipeline_curated(
            step="soul_md",
            ws=ws,
            turn_n=turn_n,
            ms=(time.perf_counter() - t) * 1000.0,
        )
    else:
        _log_memory_pipeline_skipped(
            step="soul_md", ws=ws, turn_n=turn_n, every_n=every_n
        )

    t = time.perf_counter()
    if compact_living_sphere_if_pending(
        store, complete_fn, tool_bg_idle_event=tool_bg_idle_event
    ):
        _log_memory_pipeline_curated(
            step="living_sphere_md",
            ws=ws,
            turn_n=turn_n,
            ms=(time.perf_counter() - t) * 1000.0,
        )
    else:
        _log_memory_pipeline_skipped(
            step="living_sphere_md",
            ws=ws,
            turn_n=turn_n,
            reason="no_pending_living_sphere_updates",
        )

    total_ms = (time.perf_counter() - t_all) * 1000.0
    if any_curation:
        logger.info(
            "memory_pipeline done total_ms={:.0f} ws={} turn={}",
            total_ms,
            ws,
            turn_n,
        )
    else:
        logger.debug(
            "memory_pipeline done total_ms={:.0f} ws={} turn={}",
            total_ms,
            ws,
            turn_n,
        )
    return any_curation


def memory_update_during_dreaming(
    store: MemoryStore,
    rows: list[ChatMessage],
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    *,
    tool_bg_idle_event: Event,
) -> bool:
    """Batch-curate all applicable memory docs from a sleeping-state transcript slice."""
    assert rows
    t_all = time.perf_counter()
    ws = store.scope.registry_key()
    transcript_block = _dreaming_transcript_block(rows)
    logger.info(
        "memory_pipeline dreaming_start ws={} rows={} chars={}",
        ws,
        len(rows),
        len(transcript_block),
    )
    _append_dreaming_diary_entries(store, rows=rows)

    any_curation = False
    rows_by_day: dict[str, list[ChatMessage]] = {}
    for row in rows:
        day = parse_transcript_datetime(row.ts).date().isoformat()
        rows_by_day.setdefault(day, []).append(row)

    for day, day_rows in sorted(rows_by_day.items()):
        t = time.perf_counter()
        _rewrite_dreaming_day_summary_md(
            store,
            day=day,
            rows=day_rows,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_memory_pipeline_curated(
            step=f"dreaming_day_summary_md:{day}",
            ws=ws,
            turn_n=0,
            ms=(time.perf_counter() - t) * 1000.0,
        )

    user_text = "Dreaming transcript slice:\n" + transcript_block
    assistant_text = ""
    for step, rewrite_fn in (
        ("dreaming_memory_md", _rewrite_memory_md),
        ("dreaming_user_md", _rewrite_user_md),
        ("dreaming_style_md", _rewrite_style_md),
        ("dreaming_soul_md", _rewrite_soul_md),
    ):
        t = time.perf_counter()
        rewrite_fn(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_memory_pipeline_curated(
            step=step,
            ws=ws,
            turn_n=0,
            ms=(time.perf_counter() - t) * 1000.0,
        )

    t = time.perf_counter()
    if compact_living_sphere_if_pending(
        store, complete_fn, tool_bg_idle_event=tool_bg_idle_event
    ):
        any_curation = True
        _log_memory_pipeline_curated(
            step="dreaming_living_sphere_md",
            ws=ws,
            turn_n=0,
            ms=(time.perf_counter() - t) * 1000.0,
        )

    logger.info(
        "memory_pipeline dreaming_done total_ms={:.0f} ws={} curated={}",
        (time.perf_counter() - t_all) * 1000.0,
        ws,
        any_curation,
    )
    return any_curation


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
            MemoryStore,
            str,
            str,
            Callable[[list[dict[str, Any]], str], str],
            MemoryPipelineConfig,
            str,
            str,
            Event,
        ]
    ]
    | None
) = None
_worker_lock = threading.Lock()


def _memory_worker_loop() -> None:
    if _memory_queue is None:
        raise RuntimeError("memory worker started before queue initialization")
    while True:
        (
            store,
            user_text,
            assistant_text,
            complete_fn,
            config,
            trace_id,
            user_msg_uuid,
            tool_bg_idle_event,
        ) = _memory_queue.get()
        t_job = time.perf_counter()
        logger.debug(
            "memory_pipeline worker_job_start scope={} user_chars={} assistant_chars={}",
            store.scope.registry_key(),
            len(user_text),
            len(assistant_text),
        )
        mem_bind_tok = companion_llm_runtime_event_bind_ctx.set(
            LlmRuntimeEventBind(
                memory_store=store,
                trace_id=trace_id,
                user_msg_uuid=user_msg_uuid,
                phase="memory_pipeline",
                scene=None,
            )
        )
        try:
            curated = False
            try:
                curated = memory_update_after_turn(
                    store,
                    user_text,
                    assistant_text,
                    complete_fn,
                    config,
                    tool_bg_idle_event=tool_bg_idle_event,
                )
            except _MEMORY_WORKER_ERRORS:
                logger.exception("memory_update_after_turn failed")
        finally:
            companion_llm_runtime_event_bind_ctx.reset(mem_bind_tok)
            wall_ms = (time.perf_counter() - t_job) * 1000.0
            scope = store.scope.registry_key()
            if curated:
                logger.info(
                    "memory_pipeline worker_job wall_ms={:.0f} scope={}",
                    wall_ms,
                    scope,
                )
            else:
                logger.debug(
                    "memory_pipeline worker_job wall_ms={:.0f} scope={}",
                    wall_ms,
                    scope,
                )
            _memory_queue.task_done()


def schedule_memory_update_after_turn(
    store: MemoryStore,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    config: MemoryPipelineConfig,
    *,
    trace_id: str = "",
    user_msg_uuid: str = "",
    tool_bg_idle_event: Event,
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
        (
            store,
            user_text,
            assistant_text,
            complete_fn,
            config,
            trace_id,
            user_msg_uuid,
            tool_bg_idle_event,
        ),
    )
    logger.debug(
        "memory_pipeline enqueued scope={} pending_jobs={}",
        store.scope.registry_key(),
        _memory_queue.qsize(),
    )
    logger.debug(
        "memory_pipeline enqueue_preview scope={} user={} assistant={}",
        store.scope.registry_key(),
        _clip(user_text, 120),
        _clip(assistant_text, 120),
    )
