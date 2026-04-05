"""Profile/image gating and image asset metadata helpers for P0 consistency."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

from .file_store import read_text, write_text_atomic
from .jsonl_db_store import append_jsonl_with_db
from .memory_store_registry import get_memory_store
from .utc import utc_iso_ts

_CORE_PROFILE_DOCS: frozenset[str] = frozenset({"IDENTITY.md", "SOUL.md", "USER.md"})
_STATE_FILE = ".inty_v2_image_gate.json"
_IMAGE_ASSET_INDEX_REL = "generated_images/index.jsonl"

_PROFILE_CHANGE_HINT_RE = re.compile(
    r"(修改|改|更新|切换|变更).*(性别|外貌|形象|人设|设定|称呼)|"
    r"(性别|外貌|形象|人设|设定|称呼).*(修改|改|更新|切换|变更)|"
    r"(gender|persona|appearance|identity)\s*(change|update|switch)",
    re.IGNORECASE,
)
_IMAGE_REQUEST_HINT_RE = re.compile(
    r"(生成图片|生图|文生图|图生图|改图|重画|画一张|来张图|修图|换风格|"
    r"给我画|画个|画一|肖像照|插图|"
    r"generate\s*image|text-?to-?image|image\s*to\s*image|modify\s*image)",
    re.IGNORECASE,
)
_MODE_REGENERATE_RE = re.compile(
    r"(按新设定|新设定).*(重生图|重新生成|从零生成|新图)|"
    r"(regenerate|from scratch|new image)",
    re.IGNORECASE,
)
_MODE_MODIFY_RE = re.compile(
    r"(基于旧图|在旧图基础).*(改图|修改|重画)|"
    r"(modify old image|edit existing image|image to image)",
    re.IGNORECASE,
)


def _state_path(root: Path) -> Path:
    return root.resolve() / _STATE_FILE


def _default_state(root: Path) -> dict[str, Any]:
    return {
        "persona_revision_id": compute_persona_revision_id(root),
        "pending_confirmation": None,
        "turn_guard": {
            "turn_id": "",
            "requires_profile_persist_before_image": False,
            "profile_persisted_in_turn": False,
        },
    }


def _load_state(root: Path) -> dict[str, Any]:
    p = _state_path(root)
    if not p.is_file():
        return _default_state(root)
    raw = json.loads(read_text(p))
    if not isinstance(raw, dict):
        raise ValueError(f"{p} must contain a JSON object")
    out = _default_state(root)
    out.update(raw)
    return out


def _save_state(root: Path, state: dict[str, Any]) -> None:
    write_text_atomic(_state_path(root), json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def _read_profile_doc(root: Path, relative_path: str) -> str:
    # MemoryStore is the authoritative write path for workspace markdown docs.
    # Prefer it so persona revision stays correct even when file mirroring is disabled.
    body = get_memory_store(root).read_document_if_exists(relative_path)
    if body is not None:
        return body
    p = root.resolve() / relative_path
    if p.is_file():
        return read_text(p)
    return ""


def _core_profile_payload(root: Path) -> dict[str, str]:
    return {
        "IDENTITY.md": _read_profile_doc(root, "IDENTITY.md"),
        "SOUL.md": _read_profile_doc(root, "SOUL.md"),
        "USER.md": _read_profile_doc(root, "USER.md"),
    }


def compute_persona_revision_id(root: Path) -> str:
    payload = _core_profile_payload(root)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def prepare_image_gate_for_turn(root: Path, user_text: str) -> None:
    state = _load_state(root)
    state["persona_revision_id"] = compute_persona_revision_id(root)

    txt = (user_text or "").strip()
    mode: str | None = None
    if _MODE_REGENERATE_RE.search(txt):
        mode = "regenerate"
    elif _MODE_MODIFY_RE.search(txt):
        mode = "modify"

    pending = state.get("pending_confirmation")
    if isinstance(pending, dict) and mode is not None:
        pending["selected_mode"] = mode
        pending["confirmed_at"] = utc_iso_ts()
        state["pending_confirmation"] = pending

    requires_persist = bool(_PROFILE_CHANGE_HINT_RE.search(txt) and _IMAGE_REQUEST_HINT_RE.search(txt))
    state["turn_guard"] = {
        "turn_id": str(uuid.uuid4()),
        "requires_profile_persist_before_image": requires_persist,
        "profile_persisted_in_turn": False,
    }
    _save_state(root, state)


def register_profile_write(
    root: Path,
    relative_path: str,
    *,
    changed: bool,
    new_content: str | None = None,
) -> None:
    rel = (relative_path or "").strip().replace("\\", "/")
    if rel not in _CORE_PROFILE_DOCS:
        return
    if not changed:
        return
    state = _load_state(root)
    before_revision = str(state.get("persona_revision_id") or "")
    if not before_revision:
        before_revision = compute_persona_revision_id(root)
    if new_content is not None:
        payload = _core_profile_payload(root)
        payload[rel] = new_content
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        after_revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    else:
        after_revision = compute_persona_revision_id(root)
    if before_revision == after_revision:
        return

    pending = state.get("pending_confirmation")
    changed_docs: list[str] = []
    if isinstance(pending, dict):
        raw_changed_docs = pending.get("changed_docs")
        if isinstance(raw_changed_docs, list):
            changed_docs = [str(x) for x in raw_changed_docs]
    if rel not in changed_docs:
        changed_docs.append(rel)

    state["persona_revision_id"] = after_revision
    state["pending_confirmation"] = {
        "before_revision_id": before_revision,
        "after_revision_id": after_revision,
        "changed_docs": changed_docs,
        "selected_mode": None,
        "created_at": utc_iso_ts(),
    }
    turn_guard = state.get("turn_guard")
    if isinstance(turn_guard, dict):
        turn_guard["profile_persisted_in_turn"] = True
        # Once persisted in this turn, ordering requirement is satisfied.
        turn_guard["requires_profile_persist_before_image"] = False
        state["turn_guard"] = turn_guard
    _save_state(root, state)


def check_image_tool_allowed(root: Path, *, tool_name: str) -> str | None:
    if tool_name not in {"generate_image", "modify_image"}:
        raise ValueError(f"unsupported tool for image gate: {tool_name}")
    state = _load_state(root)
    turn_guard = state.get("turn_guard")
    if isinstance(turn_guard, dict):
        req = bool(turn_guard.get("requires_profile_persist_before_image"))
        persisted = bool(turn_guard.get("profile_persisted_in_turn"))
        if req and not persisted:
            return (
                "ERROR: this turn requests profile change + image generation; "
                "persist profile docs (IDENTITY.md/USER.md/SOUL.md) first, then call image tool."
            )

    pending = state.get("pending_confirmation")
    if not isinstance(pending, dict):
        return None
    selected_mode = str(pending.get("selected_mode") or "").strip().lower()
    if not selected_mode:
        return (
            "ERROR: profile changed recently. Ask user to choose image mode first: "
            "A) 按新设定重生图 / regenerate from scratch, "
            "B) 基于旧图改图 / modify existing image."
        )
    if selected_mode == "regenerate" and tool_name != "generate_image":
        return (
            "ERROR: user selected regenerate-from-scratch mode; "
            "use generate_image, not modify_image."
        )
    if selected_mode == "modify" and tool_name != "modify_image":
        return (
            "ERROR: user selected modify-existing mode; "
            "use modify_image, not generate_image."
        )
    return None


def mark_image_tool_completed(root: Path, *, tool_name: str) -> None:
    if tool_name not in {"generate_image", "modify_image"}:
        raise ValueError(f"unsupported tool for image gate: {tool_name}")
    state = _load_state(root)
    pending = state.get("pending_confirmation")
    if isinstance(pending, dict):
        selected_mode = str(pending.get("selected_mode") or "").strip().lower()
        if (selected_mode == "regenerate" and tool_name == "generate_image") or (
            selected_mode == "modify" and tool_name == "modify_image"
        ):
            state["pending_confirmation"] = None
    state["persona_revision_id"] = compute_persona_revision_id(root)
    _save_state(root, state)


def current_persona_revision_id(root: Path) -> str:
    return compute_persona_revision_id(root)


def _image_asset_index_path(root: Path) -> Path:
    return root.resolve() / _IMAGE_ASSET_INDEX_REL


def append_image_asset_record(root: Path, record: dict[str, Any]) -> None:
    append_jsonl_with_db(_image_asset_index_path(root), record)


def list_image_asset_records(root: Path) -> list[dict[str, Any]]:
    p = _image_asset_index_path(root)
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in read_text(p).splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        if isinstance(row, dict):
            out.append(row)
    return out


def _normalize_relative_path_for_index(path: str) -> str:
    return (path or "").strip().replace("\\", "/")


def find_latest_asset_by_local_relative_path(root: Path, relative_path: str) -> dict[str, Any] | None:
    target = _normalize_relative_path_for_index(relative_path)
    if not target:
        return None
    for row in reversed(list_image_asset_records(root)):
        if _normalize_relative_path_for_index(str(row.get("local_path_relative") or "")) == target:
            return row
    return None


def relative_path_under_workspace(root: Path, absolute_path: Path) -> str:
    return absolute_path.resolve().relative_to(root.resolve()).as_posix()
