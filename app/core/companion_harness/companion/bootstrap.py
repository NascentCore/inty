"""Tool-driven MemoryStore bootstrap for first-run relationship setup.

When ``context.json`` marks the interactive bootstrap flag incomplete,
``run_companion_user_chat_turn`` enters ``USER_CHAT_BOOTSTRAP``.  That track
uses a single in-turn tool loop so the assistant can update prompt slices and
mark setup complete before normal user-chat routing resumes.

WebSocket startup does not inject a synthetic kickoff user message.  A signed-on
client emits the implicit sign-on greeting track, whose system stack carries the
bootstrap procedure while the tail user line frames the user coming online.  The
bootstrap tool path is still responsible for persisting the relationship seed
documents and flipping the bootstrap completion flag.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from loguru import logger

from app.core.companion_harness.experience_profile import (
    ExperienceContextMode,
    normalize_experience_profile_id,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
)

from app.core.companion_harness.memory.memory_store import (
    MemoryStore,
    normalize_memory_store_relative_path,
)
from .models import ContextMeta
from .prompt_slices import (
    PROMPT_SLICE_TO_REL,
    SYSTEM_PROMPT_SLICE_SEPARATOR,
    PromptSliceId,
    parse_persistable_prompt_slice_id,
    persistable_slice_names_csv,
    slice_to_workspace_rel,
)
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)

_PKG_DIR = Path(__file__).resolve().parent
_BOOTSTRAP_SPEC_PATH = _PKG_DIR / "prompts" / "BOOTSTRAP.md"

_INTERACTIVE_TEMPLATE_RELS: Final[tuple[str, ...]] = (
    "IDENTITY.md",
    "SOUL.md",
    "STYLE.md",
    "USER.md",
    "MEMORY.md",
)

_BOOTSTRAP_TOOL_SLICE_IDS: Final[tuple[PromptSliceId, ...]] = (
    PromptSliceId.IDENTITY,
    PromptSliceId.SOUL,
    PromptSliceId.STYLE,
    PromptSliceId.USER,
)


def build_bootstrap_tool_call_section() -> str:
    """工具调用 section rendered from typed tool/slice/profile names; accompanies BOOTSTRAP.md."""

    slices = " / ".join(
        slice_to_workspace_rel(sid) for sid in _BOOTSTRAP_TOOL_SLICE_IDS
    )
    return "\n".join(
        [
            "## 工具调用",
            "",
            "- Bootstrap only done once",
            f"- Call **{CompanionToolName.COMPANION_UPDATE_PROMPT_SLICE.value}** to update **{slices}** prompt slices",
            f"- Call **{CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE.value}** when the user picks a built-in companionship pattern "
            f"(e.g. `{ExperienceContextMode.REMOTE_LOVER.value}` for 异地爱人, `{ExperienceContextMode.INTIMATE.value}`, `{ExperienceContextMode.EMOTIONAL_COMPANION.value}`)",
            f"- Call **{CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE.value}** to conclude bootstrap",
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
    """

    return (
        bool(feature_enabled)
        and not meta.workspace_bootstrap_user_interactive_completed
    )


def build_interactive_bootstrap_template_reference_parts(
    *,
    max_chars_per_seed: int = 6000,
) -> list[str]:
    """Template seed bodies for writable bootstrap prompt slices."""

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


def build_interactive_bootstrap_system_message_parts(
    *,
    max_chars_per_seed: int = 6000,
) -> list[str]:
    """
    Ordered system bodies while interactive bootstrap is active.

    Returns ``BOOTSTRAP.md``, typed ``## 工具调用`` (``build_bootstrap_tool_call_section``),
    then template references for writable prompt slices.  One string per system message
    keeps stack inspection and model weighting clearer.
    """
    return [
        load_bootstrap_spec_text(),
        build_bootstrap_tool_call_section(),
        *build_interactive_bootstrap_template_reference_parts(
            max_chars_per_seed=max_chars_per_seed
        ),
    ]


def build_interactive_bootstrap_system_append(
    *,
    max_chars_per_seed: int = 6000,
) -> str:
    """Legacy single-string join of bootstrap blocks (prefer build_interactive_bootstrap_system_message_parts)."""
    return SYSTEM_PROMPT_SLICE_SEPARATOR.join(
        build_interactive_bootstrap_system_message_parts(
            max_chars_per_seed=max_chars_per_seed
        )
    )


def tool_companion_update_prompt_slice(
    store: MemoryStore,
    slice_name: str,
    content: str,
) -> str:
    """Write an allowed prompt slice and return ``OK`` or ``ERROR`` text."""

    from app.core.companion_harness.memory.memory_store_document_mapping import (
        parse_memory_store_relative_path,
    )

    sid = parse_persistable_prompt_slice_id(slice_name)
    if sid is None:
        return f"ERROR: unknown slice {slice_name!r}; use one of: {persistable_slice_names_csv()}"
    rel = PROMPT_SLICE_TO_REL[sid]
    rel_posix = normalize_memory_store_relative_path(rel)
    try:
        parse_memory_store_relative_path(rel_posix)
    except ValueError as exc:
        return f"ERROR: {exc}"
    st = store
    st.write_document(rel_posix, content)
    logger.info(
        "companion_update_prompt_slice slice={} rel={} chars={}",
        sid.value,
        rel_posix,
        len(content),
    )
    return f"OK wrote prompt slice {sid.value} to {rel_posix} ({len(content)} chars)"


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
        "OK interactive bootstrap marked complete. IDENTITY / SOUL / STYLE / USER / MEMORY may "
        "still be updated via companion_update_prompt_slice or memory_store_write_document "
        "(where permitted)."
    )


def tool_companion_set_experience_profile(
    store: MemoryStore,
    context_mode: str,
    *,
    note: str,
) -> str:
    """Persist ``context_mode`` in ``context.json`` with audit note."""

    try:
        normalized = normalize_experience_profile_id(context_mode)
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
    data["context_mode"] = normalized
    data["experience_profile_change_note"] = note.strip()[:2000]
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    st.write_document(rel_ctx, out)
    logger.info(
        "companion_set_experience_profile scope={} {} -> {}",
        st.scope.registry_key(),
        previous,
        normalized,
    )
    return (
        f"OK experience profile (context_mode) set to {normalized!r} "
        f"(previous {previous!r}); applies starting the next companion turn."
    )
