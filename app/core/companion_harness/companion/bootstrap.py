"""Tool-driven MemoryStore bootstrap for first-run relationship setup.

When ``context.json`` marks ``context_mode=bootstrap`` and the interactive
bootstrap flag is incomplete, ``run_companion_user_chat_turn`` enters
``USER_CHAT_BOOTSTRAP``.  That track uses a single in-turn tool loop so the
assistant can update prompt slices, optionally choose a post-bootstrap
``context_mode``, then mark setup complete before normal user-chat routing
resumes.

WebSocket startup does not inject a synthetic kickoff user message.  A signed-on
client emits the implicit sign-on greeting track, whose system stack carries the
bootstrap procedure while the tail user line frames the user coming online.  The
bootstrap tool path is still responsible for persisting the relationship seed
documents and flipping ``context.json`` out of bootstrap.
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


def build_interactive_bootstrap_system_message_parts(
    *,
    max_chars_per_seed: int = 6000,
) -> list[str]:
    """
    Ordered system bodies while interactive bootstrap is active.

    The first body is the bootstrap procedure; following bodies are template
    references for the writable prompt slices.  Returning one string per future
    system message keeps the procedure and examples from being collapsed into one
    large block, which makes stack inspection and model weighting clearer.
    """
    spec = load_bootstrap_spec_text()
    blocks: list[str] = [spec]
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

    If the current mode is ``bootstrap``, the stored
    ``post_bootstrap_context_mode`` becomes the next ``context_mode``; otherwise
    the current mode is preserved.  Tool callers receive a plain ``OK`` or
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
    bootstrap_id = ExperienceContextMode.BOOTSTRAP.value
    try:
        cm = normalize_experience_profile_id(str(data.get("context_mode", "")))
    except ValueError:
        cm = ""
    if cm == bootstrap_id:
        pb_raw = data.get("post_bootstrap_context_mode")
        next_mode = "intimate"
        if pb_raw is not None and str(pb_raw).strip():
            try:
                next_mode = normalize_experience_profile_id(str(pb_raw))
            except ValueError:
                next_mode = "intimate"
            if next_mode == bootstrap_id:
                next_mode = "intimate"
        data["context_mode"] = next_mode
    if "post_bootstrap_context_mode" in data:
        del data["post_bootstrap_context_mode"]
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
    """Persist a non-bootstrap ``context_mode`` in ``context.json`` with audit note."""

    try:
        normalized = normalize_experience_profile_id(context_mode)
    except ValueError as exc:
        return f"ERROR: {exc}"
    if normalized == ExperienceContextMode.BOOTSTRAP:
        return (
            "ERROR: context_mode 'bootstrap' is reserved for the interactive workspace "
            "bootstrap phase (not user-selectable via companion_set_experience_profile)"
        )

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
