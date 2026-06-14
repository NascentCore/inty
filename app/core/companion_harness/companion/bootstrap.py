"""Tool-driven MemoryStore bootstrap for first-run relationship setup.

When ``context.json`` marks the interactive bootstrap flag incomplete,
``run_companion_user_chat_turn`` enters ``USER_CHAT_BOOTSTRAP``.  That track
uses a single in-turn tool loop so the assistant can persist relationship seed
documents via ``memory_store_write_document`` and mark setup complete before
normal user-chat routing resumes.

WebSocket startup does not inject a synthetic kickoff user message.  A signed-on
client emits the implicit sign-on greeting track, whose system stack carries the
bootstrap procedure while the tail user line frames the user coming online.  The
bootstrap tool path is still responsible for persisting the relationship seed
documents and flipping the bootstrap completion flag.


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from loguru import logger
from pydantic import BaseModel, Field

from app.core.companion_harness.experience_profile import (
    ExperienceContextMode,
    ExperienceDirectiveTone,
    ExperienceDirectives,
    normalize_experience_profile_id,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    BOOTSTRAP_WRITABLE_REL_PATHS,
    CompanionToolName,
)

from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import ContextMeta
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)

_PKG_DIR = Path(__file__).resolve().parent
_BOOTSTRAP_SPEC_PATH = _PKG_DIR / "prompts" / "BOOTSTRAP.md"

# TODO(memdoc-path-constants): Seed-only rels from canonical MemDoc path constants. #3413
_BOOTSTRAP_TEMPLATE_SEED_ONLY_RELS: Final[tuple[str, ...]] = (
    "MEMORY.md",
    "SOUL.md",
)

_INTERACTIVE_TEMPLATE_RELS: Final[tuple[str, ...]] = tuple(
    sorted({*BOOTSTRAP_WRITABLE_REL_PATHS, *_BOOTSTRAP_TEMPLATE_SEED_ONLY_RELS})
)

# TODO(person-identity-schema): TEMPLATE_REFERENCE should show generic templates/IDENTITY.md schema once,
# not separate USER.md + IDENTITY.md package seeds; runtime bootstrap still writes both paths. #3390

# TODO(bootstrap-prompt-single-source): Bootstrap write/tool rules duplicated across
# ``prompts/BOOTSTRAP.md``, ``build_bootstrap_tool_call_section``, and
# ``_output_contract_text_interactive_bootstrap_tools``; derive all three from one typed
# policy next to ``BOOTSTRAP_WRITABLE_REL_PATHS`` / ``BOOTSTRAP_TRACK_TOOL_NAMES``.
# CRS bootstrap relationship seed — #3328; consolidate with ``TrackWritePolicy`` — #3367.


def build_bootstrap_tool_call_section() -> str:
    """工具调用 section rendered from typed tool names; accompanies BOOTSTRAP.md."""

    docs = " / ".join(BOOTSTRAP_WRITABLE_REL_PATHS)
    return "\n".join(
        [
            "## 工具调用",
            "",
            "- Bootstrap only done once",
            f"- Call **{CompanionToolName.MEMORY_STORE_READ_DOCUMENT.value}** to read persisted docs before updating",
            f"- Call **{CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT.value}** to update **{docs}** (full markdown body per path)",
            f"- Call **{CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE.value}** when the user picks a built-in companionship pattern "
            f"(e.g. `{ExperienceContextMode.REMOTE_LOVER.value}` for 异地爱人, `{ExperienceContextMode.INTIMATE.value}`, `{ExperienceContextMode.EMOTIONAL_COMPANION.value}`)",
            f"- Call **{CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE.value}** to conclude bootstrap",
            "- 尽快收尾：已有对话足以写初稿时，先 **memory_store_write_document** 写 IDENTITY / STYLE / USER，再 complete；禁止跳过写入直接 complete",
            "- 即使用户配合度低，也基于已有对话写 best-effort 初稿；用户想进入日常相处或已连续多轮无新信息时可提前 complete（仍须先写初稿）",
            "- 不向用户说「初始化完成」「已同步」等工程话术；用关系语境带过即可。",
        ]
    )


def load_bootstrap_spec_text() -> str:
    """Load the internal bootstrap procedure injected into bootstrap turns."""

    if not _BOOTSTRAP_SPEC_PATH.is_file():
        raise FileNotFoundError(
            f"missing bootstrap spec: {_BOOTSTRAP_SPEC_PATH}"
        )
    return _BOOTSTRAP_SPEC_PATH.read_text(encoding="utf-8").rstrip()


def interactive_bootstrap_active(
    *,
    feature_enabled: bool,
    meta: ContextMeta,
) -> bool:
    """Whether a user chat turn should run on ``USER_CHAT_BOOTSTRAP``.

    The decision is intentionally just feature flag plus completion state.  The
    current experience profile may already be ``bootstrap`` or a non-bootstrap
    mode because completion can preserve an externally chosen relationship mode.

    TODO(bootstrap-max-turns): Harness-level cap (max user-chat rounds or wall
    clock) before forcing best-effort MemoryDoc writes + complete — prompt-only
    pacing in ``BOOTSTRAP.md`` is insufficient when the model skips tools.
    But the principle is to let the LLM decide when to complete, not to force it.
    So leave this TODO open for debate and evaluation.
    """

    return (
        bool(feature_enabled)
        and not meta.workspace_bootstrap_user_interactive_completed
    )


def build_interactive_bootstrap_template_reference_parts(
    *,
    max_chars_per_seed: int = 6000,
) -> list[str]:
    """Template seed bodies for bootstrap context (incl. SOUL/MEMORY package defaults)."""

    blocks: list[str] = []
    for rel in _INTERACTIVE_TEMPLATE_RELS:
        try:
            seed = load_template_seed_text(rel)
        except FileNotFoundError:
            seed = ""
        body = seed.strip()
        if max_chars_per_seed > 0 and len(body) > max_chars_per_seed:
            body = body[: max_chars_per_seed - 1] + "\n…[truncated]"
        blocks.append(f"## TEMPLATE_REFERENCE {rel}\n\n{body}")
    return blocks


def tool_companion_bootstrap_user_interactive_complete(
    store: MemoryStore,
    note: str | None = None,
) -> str:
    """Mark interactive bootstrap complete in ``context.json``.

    ``context_mode`` remains the real experience profile for the session;
    bootstrap is only a completion flag. Tool callers receive a plain ``OK`` or
    ``ERROR`` status string because the LLM tool loop consumes the result text.
    """

    rel = "context.json"
    st = store
    raw_body = st.read_document_if_exists(rel)
    if raw_body is None or not raw_body.strip():
        return "ERROR: missing context.json"
    try:
        data: dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid context.json: {exc}"
    if not isinstance(data, dict):
        return "ERROR: context.json must be a JSON object"
    data["workspace_bootstrap_user_interactive_completed"] = True
    if note is not None and str(note).strip():
        data["workspace_bootstrap_user_interactive_complete_note"] = str(
            note
        ).strip()[:2000]
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    st.write_document(rel, out)
    logger.info(
        "companion_bootstrap_user_interactive_complete scope={}",
        st.scope.registry_key(),
    )
    return (
        "OK interactive bootstrap marked complete. IDENTITY / STYLE / USER / MEMORY / SOUL "
        "may still be updated via memory_store_write_document where permitted on later turns."
    )


class CompanionSetExperienceProfileToolInput(BaseModel):
    """Arguments for ``companion_set_experience_profile`` tool handler."""

    context_mode: str = Field(description="Target experience profile id (context_mode).")
    note: str = Field(description="Short internal audit note (not shown to user).")
    tone: ExperienceDirectiveTone | None = Field(
        default=None,
        description="Optional experience_directives.tone overlay; omit to leave unchanged.",
    )


def tool_companion_set_experience_profile(
    store: MemoryStore,
    tool_input: CompanionSetExperienceProfileToolInput,
) -> str:
    """Persist ``context_mode`` and optional ``experience_directives`` in ``context.json``."""

    try:
        normalized = normalize_experience_profile_id(tool_input.context_mode)
    except ValueError as exc:
        return f"ERROR: {exc}"
    rel_ctx = "context.json"
    st = store
    raw_body = st.read_document_if_exists(rel_ctx)
    if raw_body is None or not str(raw_body).strip():
        return "ERROR: missing context.json"
    try:
        data: dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid context.json: {exc}"
    if not isinstance(data, dict):
        return "ERROR: context.json must be a JSON object"
    previous = str(data.get("context_mode", "")).strip() or "(unset)"
    meta = ContextMeta.model_validate(data)
    directives = meta.experience_directives
    if tool_input.tone is not None:
        directives = ExperienceDirectives(tone=tool_input.tone)
    updated = meta.model_copy(
        update={
            "context_mode": normalized,
            "experience_directives": directives,
        }
    )
    data = updated.model_dump(mode="json")
    data["experience_profile_change_note"] = tool_input.note.strip()[:2000]
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    st.write_document(rel_ctx, out)
    logger.info(
        "companion_set_experience_profile scope={} {} -> {} tone={}",
        st.scope.registry_key(),
        previous,
        normalized,
        directives.tone.value if directives.tone is not None else None,
    )
    tone_suffix = ""
    if tool_input.tone is not None:
        tone_suffix = f"; experience_directives.tone={tool_input.tone.value!r}"
    return (
        f"OK experience profile (context_mode) set to {normalized!r} "
        f"(previous {previous!r}){tone_suffix}; applies starting the next companion turn."
    )
