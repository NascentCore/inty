"""Sleeping-state dreaming memory consolidation (end-of-day rollup).

Batch-curates **the day's full arc** into ``memory/daily/<date>.md`` (daily gist),
``MEMORY.md``, ``USER.md``, ``STYLE.md``, ``SOUL.md``, ``COMPANIONSHIP.md``, and ``LIVING_SPHERE.md`` —
user-visible ``transcript.jsonl`` (chat, proactive, scheduled) plus silent awake
inner-tick material (autonomy, monolog) once ``TODO(dreaming-day-rollup)`` — #3376
merges inner-tick / ``ai_private.jsonl`` / ``LIFE_CURRENTS.md`` into the slice (#3376;
optional long-cycle reflection #3366).
Only invoked from the dreaming inner-tick path — no awake post-turn updates.

**Slot algebra (target, offline)**: GENERATE / AGGREGATE (day→week→month) / SPLIT with
``derived_from`` provenance; compaction ladder places durable gist at prompt head and
verbatim turns at tail (#3522). **Today**: day→daily gist→MEMORY rollup only.

Memory-phase invariant **DreamingBatch**: see ``companion.turn_invariants`` — batch
curation entry is ``consolidate_memory_during_dreaming`` only.

TODO(slot-algebra-compaction): Week/month AGGREGATE and SPLIT morphs in dreaming batch. — #3522

TODO(!3634): Replace headless curator chain with persona AgenticLoop entry when ready.

TODO(world-engine-l2-echo): On sub-agent dismiss, merge bounded encounter echo
into companion ``MEMORY.md``; generalize bounded-coherent curation — #3709 (epic #3700).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Event
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.dreaming import (
    parse_transcript_datetime,
)
from app.core.companion_harness.companion.models import ChatMessage
from app.core.companion_harness.companion.transcript_ai_private import (
    dreaming_transcript_block,
)
from app.core.companion_harness.companion.utc import local_date_str

from .living_sphere_curator import compact_living_sphere_if_pending
from .memory_store import MemoryStore
from .memory_store_path_constants import (
    COMPANIONSHIP_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    USER_MD_REL,
)
from .memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    load_template_seed_text,
)

_MEMORY_DAILY_GIST_CTX_MAX = 12_000
_SOUL_MEMORY_CTX_MAX = 12_000

_SOUL_FROZEN_APPEARANCE_MARKER = "<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>"

_MEMORY_CURATOR_SYSTEM = """You are a memory curator for semantic long-term memory (MEMORY.md). Given the current MEMORY.md, optional current-day gist summary (memory/daily/<date>.md), and the latest user/assistant turn, output ONLY the full updated MEMORY.md body (markdown).

Rules:
- Preserve useful prior facts; merge new stable facts; remove clear contradictions.
- The day summary (if provided) is structured notes for today; use it to extract stable long-term facts when appropriate.
- Stay concise (at most about 2000 characters of substantive content).
- **## 事件日志** (if present): Record only **important** events—outcomes, agreements, boundary shifts, failures, durable facts. **Do not** log turn-by-turn play-by-play, micro body language, facial expressions, voice tone, or posture. Merge same-day trivia into one line per theme when possible.
- **## 稳定事实** (if present): Short durable patterns only; **do not** duplicate the event log with extra scenic detail. One sentence per bullet where possible; avoid enumerating trivial reactions.
- Output raw markdown only: no preamble, no code fences around the whole document.
"""

_SOUL_CURATOR_SYSTEM = """You are a SOUL document curator. SOUL.md is injected into the assistant's system prompt on every turn; it must stay aligned with durable values, boundaries, consent/safety lines, and persistent interaction commitments.

You run during sleeping-state dreaming with other long-term documents. Your job is to update **only** durable values, boundaries, and interaction commitments—not scene play-by-play, not episodic flavor, not visual/physical 形象 or 外貌.

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

_DAY_SUMMARY_SYSTEM = """You are a day memory summarizer (daily gist layer: memory/daily/<date>.md). You maintain a single markdown file for the calendar day: structured, human-readable notes (not a raw chat log).

Given the previous version of that file (may be empty) and a dreaming transcript slice for that day, output ONLY the full updated markdown body for that day.

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

_COMPANIONSHIP_CURATOR_SYSTEM = """You are a COMPANIONSHIP.md curator. This document is the **bond narrative** between the user and the assistant: user wording for the relationship, relationship_phase (bond maturity), distance/commitment framing, and mutual agreements visible to the user.

COMPANIONSHIP.md is injected post-bootstrap. It is **not**:
- `context.json` `context_mode`, `experience_directives.intent`, or `experience_directives.tone` (fast session experience — dreaming **never** edits context.json)
- `STYLE.md` (how Inty speaks) or `IDENTITY.md` (who Inty is)

Given the current COMPANIONSHIP.md, the latest MEMORY.md (already updated this turn), and the dreaming transcript slice, output ONLY the full updated COMPANIONSHIP.md body (markdown).

Rules:
- Preserve template sections: 用户原话, relationship_phase, 相处 framing, 对用户可见的相处约定, 更新记录.
- **relationship_phase**: change cautiously (e.g. exploring → settled) only when the slice shows clear mutual stabilization; prefer incremental bond shifts, not drama.
- Record durable user relationship wording; keep quoted user voice where appropriate.
- Update mutual agreements and distance/commitment when clearly negotiated; do not invent commitments.
- Do **not** encode session intent (casual_chat / roleplay / …) or tone (warm/playful) — those belong in context.json `experience_directives`.
- When bond state changes, append a brief dated note under 更新记录.
- If the slice has no bond-relevant signal, return COMPANIONSHIP.md unchanged (verbatim aside from trivial whitespace).
- Output raw markdown only; same language as the document (usually Chinese).
- Stay within ~4000 characters substantive unless the document is already longer.
"""


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


def _log_dreaming_consolidation_curated(
    *, step: str, ws: str, ms: float
) -> None:
    logger.info(
        "dreaming_consolidation curated step={} ms={:.0f} ws={}",
        step,
        ms,
        ws,
    )


def _dreaming_transcript_block(
    store: MemoryStore, rows: list[ChatMessage], *, day_iso: str
) -> str:
    """Render a compact transcript block for batch curation prompts."""
    return dreaming_transcript_block(store, rows, day_iso=day_iso)


def _rewrite_dreaming_daily_gist_md(
    store: MemoryStore,
    *,
    day: str,
    rows: list[ChatMessage],
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist(day)
    prev_gist = store.read_document_if_exists(rel) or ""
    user_block = (
        f"Previous daily gist ({rel}):\n\n{prev_gist}\n\n"
        f"---\n\nDreaming transcript slice:\n{_dreaming_transcript_block(store, rows, day_iso=day)}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _DAY_SUMMARY_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "dreaming_day_summary")
    store.write_document(rel, new_body.strip() + "\n")


def _rewrite_memory_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    day = local_date_str()
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist(day)
    day_summary_ctx = ""
    ds = store.read_document_if_exists(rel)
    if ds is not None:
        if len(ds) > _MEMORY_DAILY_GIST_CTX_MAX:
            day_summary_ctx = ds[: _MEMORY_DAILY_GIST_CTX_MAX - 1] + "…"
        else:
            day_summary_ctx = ds
    memory_body = store.read_document(MEMORY_MD_REL)
    user_block = (
        f"Current day gist ({rel}):\n\n{day_summary_ctx}\n\n---\n\n"
        f"Current MEMORY.md:\n\n{memory_body}\n\n---\n\n"
        f"Latest turn:\nUser:\n{user_text}\n\nAssistant:\n{assistant_text}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _MEMORY_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "memory")
    store.write_document(MEMORY_MD_REL, new_body.strip() + "\n")


def _rewrite_user_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    user_body = store.read_document(USER_MD_REL)
    memory_body = store.read_document(MEMORY_MD_REL)
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
    store.write_document(USER_MD_REL, new_body.strip() + "\n")


def _rewrite_style_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    style_body = store.read_document(STYLE_MD_REL)
    memory_body = store.read_document(MEMORY_MD_REL)
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
    store.write_document(STYLE_MD_REL, new_body.strip() + "\n")


def _rewrite_soul_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    soul_body = store.read_document(SOUL_MD_REL)
    curator_doc, frozen_appearance = _split_soul_appearance_section(soul_body)
    memory_body = store.read_document(MEMORY_MD_REL)
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
    store.write_document(SOUL_MD_REL, new_body.strip() + "\n")


def _rewrite_companionship_md(
    store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> None:
    # assistant_text unused: bond curation reads the full dreaming slice via user_text.
    companionship_body = store.read_document_if_exists(COMPANIONSHIP_MD_REL)
    if companionship_body is None:
        companionship_body = load_template_seed_text(COMPANIONSHIP_MD_REL)
    memory_body = store.read_document(MEMORY_MD_REL)
    if len(memory_body) > _SOUL_MEMORY_CTX_MAX:
        memory_ctx = memory_body[: _SOUL_MEMORY_CTX_MAX - 1] + "…"
    else:
        memory_ctx = memory_body
    user_block = (
        f"Current COMPANIONSHIP.md:\n\n{companionship_body}\n\n---\n\n"
        f"Current MEMORY.md (long-term, for consistency):\n\n{memory_ctx}\n\n---\n\n"
        f"{user_text}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _COMPANIONSHIP_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "companionship")
    store.write_document(COMPANIONSHIP_MD_REL, new_body.strip() + "\n")


def consolidate_memory_during_dreaming(
    store: MemoryStore,
    rows: list[ChatMessage],
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    *,
    tool_bg_idle_event: Event,
) -> bool:
    """Batch-curate all applicable memory docs from a sleeping-state transcript slice.

    ``rows`` come from ``dreaming_candidate_slice`` (main ``transcript.jsonl`` only
    today). TODO(dreaming-day-rollup): merge inner-tick transcript and inject — #3376
    ``LIFE_CURRENTS.md`` per candidate day into curator prompts (#3376).
    ai_private manifest hydrate + unconsumed section: partial #3420.
    """
    assert rows
    t_all = time.perf_counter()
    ws = store.scope.registry_key()
    rows_by_day: dict[str, list[ChatMessage]] = {}
    for row in rows:
        day = parse_transcript_datetime(row.ts).date().isoformat()
        rows_by_day.setdefault(day, []).append(row)
    day_blocks = [
        _dreaming_transcript_block(store, day_rows, day_iso=day)
        for day, day_rows in sorted(rows_by_day.items())
    ]
    transcript_block = "\n\n".join(day_blocks)
    # TODO(dreaming-day-rollup): append LIFE_CURRENTS.md body per day in — #3376
    # rows_by_day before memory/user/style/soul curator steps (#3376).
    logger.info(
        "dreaming_consolidation start ws={} rows={} chars={}",
        ws,
        len(rows),
        len(transcript_block),
    )

    any_curation = False
    for day, day_rows in sorted(rows_by_day.items()):
        t = time.perf_counter()
        _rewrite_dreaming_daily_gist_md(
            store,
            day=day,
            rows=day_rows,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_dreaming_consolidation_curated(
            step=f"daily_gist_md:{day}",
            ws=ws,
            ms=(time.perf_counter() - t) * 1000.0,
        )

    user_text = "Dreaming transcript slice:\n" + transcript_block
    assistant_text = ""
    for step, rewrite_fn in (
        ("dreaming_memory_md", _rewrite_memory_md),
        ("dreaming_user_md", _rewrite_user_md),
        ("dreaming_style_md", _rewrite_style_md),
        ("dreaming_soul_md", _rewrite_soul_md),
        ("dreaming_companionship_md", _rewrite_companionship_md),
    ):
        t = time.perf_counter()
        rewrite_fn(
            store,
            user_text=user_text,
            assistant_text=assistant_text,
            complete_fn=complete_fn,
        )
        any_curation = True
        _log_dreaming_consolidation_curated(
            step=step,
            ws=ws,
            ms=(time.perf_counter() - t) * 1000.0,
        )

    t = time.perf_counter()
    if compact_living_sphere_if_pending(
        store, complete_fn, tool_bg_idle_event=tool_bg_idle_event
    ):
        any_curation = True
        _log_dreaming_consolidation_curated(
            step="dreaming_living_sphere_md",
            ws=ws,
            ms=(time.perf_counter() - t) * 1000.0,
        )

    logger.info(
        "dreaming_consolidation done total_ms={:.0f} ws={} curated={}",
        (time.perf_counter() - t_all) * 1000.0,
        ws,
        any_curation,
    )
    return any_curation
