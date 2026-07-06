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

**Curator modes** (``agent.companion_harness.dreaming_curator_mode``):
``one_shot`` (default) — one LLM request with parallel ``update_dreaming_document``
tool calls; ``sequential`` — legacy per-document chain. One-shot cannot see sibling
tool outputs mid-flight (no fresh MEMORY.md between USER/STYLE/SOUL steps); the prompt
instructs in-context chaining instead. Unchanged docs use explicit no-op calls
(``content_changed=false``); only changed docs are written. Set ``sequential`` in
config to roll back.

TODO(dreaming-one-shot-retire-sequential): Delete the sequential per-doc chain and the — #3757
curator-mode knob once one-shot curation quality is validated (#3757).

TODO(slot-algebra-compaction): Week/month AGGREGATE and SPLIT morphs in dreaming batch. — #3522

TODO(!3634): Replace headless curator chain with persona AgenticLoop entry when ready.

TODO(world-engine-l2-echo): On sub-agent dismiss, merge bounded encounter echo — #3709
into companion ``MEMORY.md``; generalize bounded-coherent curation (epic #3700).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import Event
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, model_validator

from app.core.companion_harness.companion.dreaming import (
    parse_transcript_datetime,
)
from app.core.companion_harness.companion.models import ChatMessage
from app.core.companion_harness.companion.transcript_ai_private import (
    dreaming_transcript_block,
)
from app.core.companion_harness.companion.utc import local_date_str
from app.core.companion_harness.tools.openai_tools_prepare import (
    openai_function_tool,
    prepare_openai_tools_for_chat_completions,
)
from app.core.llms.client import LlmClient
from app.utils.config import DreamingCuratorMode

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

_DREAMING_DOCUMENT_UPDATE_TOOL_NAME = "update_dreaming_document"

# LangSmith model-role label for the single one-shot curator LLM request; the
# REPL regression skill matches run names ending with this value.
DREAMING_ONE_SHOT_LLM_ROLE = "dreaming_one_shot"

_ONE_SHOT_CURATOR_PREAMBLE = """You are a dreaming memory curator. During sleeping-state dreaming you update multiple long-term MemoryDocs in one pass.

Before emitting any tool calls, reason briefly (in your head, not in tool output) about what the updated daily gist(s) and MEMORY.md should become, then derive USER.md, STYLE.md, SOUL.md, and COMPANIONSHIP.md from that draft so documents stay mutually consistent.

Emit exactly one ``update_dreaming_document`` tool call per required document path listed below.
Set ``content_changed`` to true and include the full updated markdown body when that document should change.
Set ``content_changed`` to false for an explicit no-op when the transcript has no relevant signal for that document (``body`` may be empty; explain in ``changed_reason``).
"""


class DreamingDocumentKind(StrEnum):
    """Semantic target for a one-shot dreaming document update tool call."""

    DAILY_GIST = "daily_gist"
    MEMORY = "memory"
    USER = "user"
    STYLE = "style"
    SOUL = "soul"
    COMPANIONSHIP = "companionship"


class DreamingDocumentUpdate(BaseModel):
    """Validated arguments for one ``update_dreaming_document`` tool call."""

    document_kind: DreamingDocumentKind = Field(
        description="Which MemoryDoc role this update applies to."
    )
    relative_path: str = Field(
        description="Repo-relative MemoryStore path being updated."
    )
    content_changed: bool = Field(
        description=(
            "True when this document should be rewritten; false for explicit no-op "
            "(store keeps the current body)."
        )
    )
    body: str = Field(
        description=(
            "Full updated markdown body when content_changed is true; "
            "empty when content_changed is false."
        )
    )
    changed_reason: str = Field(
        description="Short note on why this document changed or stayed unchanged."
    )

    @model_validator(mode="after")
    def _body_required_when_changed(self) -> DreamingDocumentUpdate:
        if self.content_changed and not self.body.strip():
            raise ValueError(
                "dreaming document update body required when content_changed is true"
            )
        return self


@dataclass(frozen=True)
class DreamingCuratorInput:
    """Snapshot of current MemoryDocs and transcript slice for one-shot curation.

    ``current_bodies`` maps every required MemoryStore path to the curator-visible
    body (SOUL.md holds the frozen-appearance marker instead of the 形象 section).
    """

    required_paths: tuple[str, ...]
    current_bodies: dict[str, str]
    soul_frozen_appearance: str | None
    transcript_block: str


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
    memory_ctx = _truncate_memory_ctx(store.read_document(MEMORY_MD_REL))
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
    memory_ctx = _truncate_memory_ctx(store.read_document(MEMORY_MD_REL))
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
    memory_ctx = _truncate_memory_ctx(store.read_document(MEMORY_MD_REL))
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
    memory_ctx = _truncate_memory_ctx(store.read_document(MEMORY_MD_REL))
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


def _truncate_memory_ctx(body: str) -> str:
    if len(body) > _SOUL_MEMORY_CTX_MAX:
        return body[: _SOUL_MEMORY_CTX_MAX - 1] + "…"
    return body


def _rows_by_day(rows: list[ChatMessage]) -> dict[str, list[ChatMessage]]:
    grouped: dict[str, list[ChatMessage]] = {}
    for row in rows:
        day = parse_transcript_datetime(row.ts).date().isoformat()
        grouped.setdefault(day, []).append(row)
    return grouped


def _build_dreaming_curator_input(
    store: MemoryStore,
    rows: list[ChatMessage],
) -> DreamingCuratorInput:
    """Package current MemoryDoc bodies and transcript for one-shot curation."""
    by_day = _rows_by_day(rows)
    daily_paths = tuple(
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist(day)
        for day in sorted(by_day.keys())
    )
    soul_body = store.read_document(SOUL_MD_REL)
    soul_curator_doc, soul_frozen = _split_soul_appearance_section(soul_body)
    companionship_body = store.read_document_if_exists(COMPANIONSHIP_MD_REL)
    if companionship_body is None:
        companionship_body = load_template_seed_text(COMPANIONSHIP_MD_REL)
    day_blocks = [
        _dreaming_transcript_block(store, day_rows, day_iso=day)
        for day, day_rows in sorted(by_day.items())
    ]
    required_paths = daily_paths + (
        MEMORY_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    )
    current_bodies = {
        rel: store.read_document_if_exists(rel) or "" for rel in daily_paths
    }
    current_bodies[MEMORY_MD_REL] = store.read_document(MEMORY_MD_REL)
    current_bodies[USER_MD_REL] = store.read_document(USER_MD_REL)
    current_bodies[STYLE_MD_REL] = store.read_document(STYLE_MD_REL)
    current_bodies[SOUL_MD_REL] = soul_curator_doc
    current_bodies[COMPANIONSHIP_MD_REL] = companionship_body
    return DreamingCuratorInput(
        required_paths=required_paths,
        current_bodies=current_bodies,
        soul_frozen_appearance=soul_frozen,
        transcript_block="\n\n".join(day_blocks),
    )


def _one_shot_system_message() -> str:
    sections = [
        _ONE_SHOT_CURATOR_PREAMBLE,
        f"## Rules for daily gist (memory/daily/<date>.md)\n\n{_DAY_SUMMARY_SYSTEM}",
        f"## Rules for {MEMORY_MD_REL}\n\n{_MEMORY_CURATOR_SYSTEM}",
        f"## Rules for {USER_MD_REL}\n\n{_USER_CURATOR_SYSTEM}",
        f"## Rules for {STYLE_MD_REL}\n\n{_STYLE_CURATOR_SYSTEM}",
        f"## Rules for {SOUL_MD_REL}\n\n{_SOUL_CURATOR_SYSTEM}",
        f"## Rules for {COMPANIONSHIP_MD_REL}\n\n{_COMPANIONSHIP_CURATOR_SYSTEM}",
    ]
    return "\n\n".join(sections)


def _build_one_shot_dreaming_messages(
    curator_input: DreamingCuratorInput,
) -> list[dict[str, Any]]:
    """Build one prompt with all current docs and the dreaming transcript slice.

    Every doc body (MEMORY.md included) already appears once as a
    ``### Current `<path>``` block, so no extra consistency copy is appended.
    """
    doc_blocks = [
        f"### Current `{rel}`\n\n{curator_input.current_bodies[rel]}"
        for rel in curator_input.required_paths
    ]
    user_block = (
        "\n\n".join(doc_blocks) + "\n\n---\n\n"
        f"Dreaming transcript slice:\n{curator_input.transcript_block}\n"
    )
    return [
        {"role": "system", "content": _one_shot_system_message()},
        {"role": "user", "content": user_block},
    ]


def _dreaming_document_update_tool_schema(
    required_paths: tuple[str, ...],
) -> dict[str, Any]:
    """OpenAI tool schema for parallel ``update_dreaming_document`` calls."""
    kind_values = [member.value for member in DreamingDocumentKind]
    tool = openai_function_tool(
        _DREAMING_DOCUMENT_UPDATE_TOOL_NAME,
        "Update one dreaming MemoryDoc, or declare an explicit no-op for that path.",
        {
            "type": "object",
            "properties": {
                "document_kind": {
                    "type": "string",
                    "enum": kind_values,
                    "description": "Semantic document role being updated.",
                },
                "relative_path": {
                    "type": "string",
                    "enum": list(required_paths),
                    "description": "Exact MemoryStore relative path to write.",
                },
                "content_changed": {
                    "type": "boolean",
                    "description": (
                        "True to write body; false for explicit no-op (keep current doc)."
                    ),
                },
                "body": {
                    "type": "string",
                    "description": (
                        "Full updated markdown body when content_changed is true; "
                        "empty for no-op."
                    ),
                },
                "changed_reason": {
                    "type": "string",
                    "description": "Brief reason for the change or no-op.",
                },
            },
            "required": [
                "document_kind",
                "relative_path",
                "content_changed",
                "body",
                "changed_reason",
            ],
            "additionalProperties": False,
        },
    )
    return prepare_openai_tools_for_chat_completions([tool])[0]


def _parse_dreaming_tool_calls(response: Any) -> list[DreamingDocumentUpdate]:
    """Extract and validate one-shot dreaming document update tool calls."""
    message = response.choices[0].message
    raw_tool_calls = getattr(message, "tool_calls", None) or []
    updates: list[DreamingDocumentUpdate] = []
    for tc in raw_tool_calls:
        fn = tc.function
        if fn.name != _DREAMING_DOCUMENT_UPDATE_TOOL_NAME:
            raise ValueError(
                f"unexpected dreaming tool name {fn.name!r}; "
                f"expected {_DREAMING_DOCUMENT_UPDATE_TOOL_NAME!r}"
            )
        args_raw = fn.arguments if fn.arguments is not None else ""
        payload = json.loads(args_raw)
        updates.append(DreamingDocumentUpdate.model_validate(payload))
    return updates


def _apply_dreaming_document_updates(
    store: MemoryStore,
    curator_input: DreamingCuratorInput,
    updates: list[DreamingDocumentUpdate],
) -> bool:
    """Apply one-shot updates; skip explicit no-ops; fail before partial writes."""
    by_path: dict[str, DreamingDocumentUpdate] = {}
    for update in updates:
        if update.relative_path in by_path:
            raise ValueError(
                f"duplicate dreaming document update for {update.relative_path!r}"
            )
        by_path[update.relative_path] = update

    missing = [
        path for path in curator_input.required_paths if path not in by_path
    ]
    if missing:
        raise ValueError(
            f"missing required dreaming document updates: {sorted(missing)!r}"
        )

    extra = sorted(set(by_path.keys()) - set(curator_input.required_paths))
    if extra:
        raise ValueError(
            f"unexpected dreaming document update paths: {extra!r}"
        )

    if not any(
        by_path[rel].content_changed for rel in curator_input.required_paths
    ):
        raise ValueError("no content_changed=true dreaming document updates")

    any_written = False
    for rel in curator_input.required_paths:
        update = by_path[rel]
        if not update.content_changed:
            continue
        body = update.body.strip()
        if (
            rel == SOUL_MD_REL
            and curator_input.soul_frozen_appearance is not None
        ):
            body = _merge_soul_frozen_appearance(
                body, curator_input.soul_frozen_appearance
            )
        store.write_document(rel, body.strip() + "\n")
        any_written = True
    return any_written


def _consolidate_memory_sequential(
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
    rows_by_day = _rows_by_day(rows)
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


def _consolidate_memory_one_shot(
    store: MemoryStore,
    rows: list[ChatMessage],
    llm_client: LlmClient,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    *,
    langsmith_extra: dict[str, Any],
    tool_bg_idle_event: Event,
) -> bool:
    """One-shot MemoryDoc curation via parallel tool calls in a single LLM request."""
    assert rows
    t_all = time.perf_counter()
    ws = store.scope.registry_key()
    curator_input = _build_dreaming_curator_input(store, rows)
    logger.info(
        "dreaming_consolidation one_shot start ws={} rows={} paths={} chars={}",
        ws,
        len(rows),
        len(curator_input.required_paths),
        len(curator_input.transcript_block),
    )

    messages = _build_one_shot_dreaming_messages(curator_input)
    tools = [
        _dreaming_document_update_tool_schema(curator_input.required_paths)
    ]
    t = time.perf_counter()
    response = llm_client.chat_completion_unified(
        messages=messages,
        model=llm_client.resolve_model("memory"),
        tools=tools,
        tool_choice="required",
        langsmith_extra=langsmith_extra,
    )
    updates = _parse_dreaming_tool_calls(response)
    any_curation = _apply_dreaming_document_updates(
        store, curator_input, updates
    )
    _log_dreaming_consolidation_curated(
        step=DREAMING_ONE_SHOT_LLM_ROLE,
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


def consolidate_memory_during_dreaming(
    store: MemoryStore,
    rows: list[ChatMessage],
    curator_mode: DreamingCuratorMode,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    llm_client: LlmClient,
    *,
    langsmith_extra: dict[str, Any],
    tool_bg_idle_event: Event,
) -> bool:
    """Batch-curate MemoryDocs; dispatches to sequential or one-shot curator mode."""
    # TODO(!3634): group (complete_fn, llm_client, langsmith_extra, tool_bg_idle_event)
    # into one curator-runtime dataclass when the persona AgenticLoop entry replaces
    # the headless curator chain.
    match curator_mode:
        case DreamingCuratorMode.SEQUENTIAL:
            return _consolidate_memory_sequential(
                store,
                rows,
                complete_fn,
                tool_bg_idle_event=tool_bg_idle_event,
            )
        case DreamingCuratorMode.ONE_SHOT:
            return _consolidate_memory_one_shot(
                store,
                rows,
                llm_client,
                complete_fn,
                langsmith_extra=langsmith_extra,
                tool_bg_idle_event=tool_bg_idle_event,
            )
