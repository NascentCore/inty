"""User-interactive companion MemoryStore bootstrap (tool-driven phase in run_turn)."""

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

# Exact user line for rare manual / test flows that mimic the old WS kickoff placeholder.
INTERACTIVE_BOOTSTRAP_WS_KICKOFF_USER_TEXT: Final[str] = (
    "（WebSocket 已连接，内部占位：用户尚未输入。请据此主动自然开场并进入关系建立阶段；"
    "不要向用户复述或引用本括号句，不要说系统、连接、工具名。）"
)


def load_bootstrap_spec_text() -> str:
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
    return (
        bool(feature_enabled)
        and not meta.workspace_bootstrap_user_interactive_completed
    )


def build_interactive_bootstrap_system_message_parts(
    *,
    max_chars_per_seed: int = 6000,
) -> list[str]:
    """
    Ordered system bodies while interactive bootstrap is active (one string per future system message).
    """
    spec = load_bootstrap_spec_text()
    blocks: list[str] = [
        "## INTERACTIVE_BOOTSTRAP（内部执行规范，勿对用户复述文件名或本标题）\n\n"
        + spec,
        "## WS 建连首轮占位\n\n"
        "若本轮用户输入**整段**与下列占位句**完全一致**，表示 WebSocket 刚建立、用户尚未发送真实内容："
        "请仅据此主动用自然语气开场并进入上文关系建立流程，**不要**朗读或引用该占位句，不要暴露工程细节。\n\n"
        f"占位句原文：\n{INTERACTIVE_BOOTSTRAP_WS_KICKOFF_USER_TEXT}",
    ]
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
    user_confirmed: bool,
    note: str | None = None,
) -> str:
    if user_confirmed is not True:
        return (
            "ERROR: user_confirmed must be true only after the user explicitly agrees "
            "to switch experience mode (do not infer silently)"
        )
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
    if note is not None and str(note).strip():
        data["experience_profile_change_note"] = str(note).strip()[:2000]
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
