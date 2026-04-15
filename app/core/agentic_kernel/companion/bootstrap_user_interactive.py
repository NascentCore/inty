"""User-interactive companion workspace bootstrap (separate from bootstrap.py loop)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from loguru import logger

from .memory_store import MemoryStore
from .models import ContextMeta
from .workspace import load_workspace_seed_text

_PKG_DIR = Path(__file__).resolve().parent
_BOOTSTRAP_SPEC_PATH = _PKG_DIR / "templates" / "BOOTSTRAP.md"

# Slice names accepted by companion_update_prompt_slice (maps to workspace root files).
PROMPT_SLICE_TO_REL: Final[dict[str, str]] = {
    "IDENTITY": "IDENTITY.md",
    "SOUL": "SOUL.md",
    "USER": "USER.md",
    "MEMORY": "MEMORY.md",
    "AGENTS": "AGENTS.md",
    "HEARTBEAT": "HEARTBEAT.md",
    "TOOLS": "TOOLS.md",
    "CAPABILITIES": "CAPABILITIES.md",
}

_INTERACTIVE_TEMPLATE_RELS: Final[tuple[str, ...]] = (
    "IDENTITY.md",
    "SOUL.md",
    "USER.md",
    "MEMORY.md",
)

# Single exact user line for WebSocket connect-time kickoff (no real user text yet).
INTERACTIVE_BOOTSTRAP_WS_KICKOFF_USER_TEXT: Final[str] = (
    "（WebSocket 已连接，内部占位：用户尚未输入。请据此主动自然开场并进入关系建立阶段；"
    "不要向用户复述或引用本括号句，不要说系统、连接、工具名。）"
)


def _try_stored_context_as_dict(*, store: MemoryStore) -> dict[str, Any] | None:
    raw_body = store.read_document_if_exists("context.json")
    if raw_body is None or not str(raw_body).strip():
        return None
    try:
        data: Any = json.loads(raw_body)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def load_bootstrap_spec_text() -> str:
    if not _BOOTSTRAP_SPEC_PATH.is_file():
        raise FileNotFoundError(f"missing bootstrap spec: {_BOOTSTRAP_SPEC_PATH}")
    return _BOOTSTRAP_SPEC_PATH.read_text(encoding="utf-8").rstrip()


def interactive_bootstrap_active(
    *,
    feature_enabled: bool,
    meta: ContextMeta,
) -> bool:
    return bool(feature_enabled) and not meta.workspace_bootstrap_user_interactive_completed


def soul_prompt_is_locked_after_interactive_bootstrap(*, store: MemoryStore) -> bool:
    """
    True only when context.json explicitly sets workspace_bootstrap_user_interactive_completed.

    Missing key means legacy / non-interactive context: do not lock SOUL (ContextMeta defaults
    would otherwise treat unknown JSON as completed).
    """
    data = _try_stored_context_as_dict(store=store)
    if data is None:
        return False
    if "workspace_bootstrap_user_interactive_completed" not in data:
        return False
    return bool(data["workspace_bootstrap_user_interactive_completed"])


def build_interactive_bootstrap_system_append(
    *,
    max_chars_per_seed: int = 6000,
) -> str:
    """
    Internal-only text appended to system prompt while interactive bootstrap is active.
    Includes BOOTSTRAP.md plus package seed templates for orientation (not live store bodies).
    """
    spec = load_bootstrap_spec_text()
    blocks: list[str] = [
        "## INTERACTIVE_BOOTSTRAP（内部执行规范，勿对用户复述文件名或本标题）\n\n" + spec,
        "## WS 建连首轮占位\n\n"
        "若本轮用户输入**整段**与下列占位句**完全一致**，表示 WebSocket 刚建立、用户尚未发送真实内容："
        "请仅据此主动用自然语气开场并进入上文关系建立流程，**不要**朗读或引用该占位句，不要暴露工程细节。\n\n"
        f"占位句原文：\n{INTERACTIVE_BOOTSTRAP_WS_KICKOFF_USER_TEXT}",
    ]
    for rel in _INTERACTIVE_TEMPLATE_RELS:
        try:
            seed = load_workspace_seed_text(rel)
        except FileNotFoundError:
            seed = ""
        body = seed.strip()
        if max_chars_per_seed > 0 and len(body) > max_chars_per_seed:
            body = body[: max_chars_per_seed - 1] + "\n…[truncated]"
        blocks.append(f"## TEMPLATE_REFERENCE {rel}\n\n{body}")
    return "\n\n---\n\n".join(blocks)


def tool_companion_update_prompt_slice(
    root: Path,
    slice_name: str,
    content: str,
) -> str:
    from .image_gate import register_profile_write
    from .memory_registry import get_memory_store
    from .repl_workspace_tools import resolve_under_workspace
    from .workspace_doc_mapping import parse_workspace_relative_path

    key = (slice_name or "").strip().upper()
    rel = PROMPT_SLICE_TO_REL.get(key)
    if rel is None:
        allowed = ", ".join(sorted(PROMPT_SLICE_TO_REL))
        return f"ERROR: unknown slice {slice_name!r}; use one of: {allowed}"
    root_r = root.resolve()
    p = resolve_under_workspace(root_r, rel)
    rel_posix = p.relative_to(root_r).as_posix()
    try:
        parse_workspace_relative_path(rel_posix)
    except ValueError as exc:
        return f"ERROR: {exc}"
    st = get_memory_store(root_r)
    if key == "SOUL" and soul_prompt_is_locked_after_interactive_bootstrap(store=st):
        return (
            "ERROR: SOUL.md is immutable after interactive bootstrap completes; "
            "you may still update IDENTITY / USER / MEMORY and other non-SOUL slices "
            "via companion_update_prompt_slice or workspace_write_file (where permitted)."
        )
    prev = st.read_document_if_exists(rel_posix)
    st.write_document(rel_posix, content)
    register_profile_write(
        root_r,
        rel_posix,
        changed=(prev != content),
        new_content=content,
    )
    logger.info("companion_update_prompt_slice slice={} rel={} chars={}", key, rel_posix, len(content))
    return f"OK wrote prompt slice {key} to {rel_posix} ({len(content)} chars)"


def tool_companion_bootstrap_user_interactive_complete(
    root: Path,
    note: str | None = None,
) -> str:
    from .memory_registry import get_memory_store
    from .repl_workspace_tools import resolve_under_workspace

    root_r = root.resolve()
    rel = resolve_under_workspace(root_r, "context.json").relative_to(root_r).as_posix()
    st = get_memory_store(root_r)
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
        data["workspace_bootstrap_user_interactive_complete_note"] = str(note).strip()[:2000]
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    st.write_document(rel, out)
    logger.info("companion_bootstrap_user_interactive_complete ws={}", root_r.name)
    return (
        "OK interactive bootstrap marked complete; SOUL.md is now locked (no tool or background "
        "SOUL rewrites). IDENTITY / USER / MEMORY and other prompt slices may still be updated."
    )
