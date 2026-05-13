"""Profile/image gating, generated_images index access, and chat_history generated_image helpers."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from .memory_store import MemoryStore
from .utc import utc_iso_ts
from .memory_store_scope import DEFAULT_MEMORY_STORE_SCOPE_PATHS

_CORE_PROFILE_DOCS: frozenset[str] = frozenset({"IDENTITY.md", "SOUL.md", "USER.md"})
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
_PENDING_REGENERATE_CHOICE_RE = re.compile(
    r"^\s*(?:选(?:择)?|选项|方案|按)?\s*[aAＡａ]\s*"
    r"(?:[。．.!！,，、:：;；)\]】）]*\s*)?"
    r"(?:$|按新设定|新设定|重生图|重新|从零|从头|new|regenerate|scratch)",
    re.IGNORECASE,
)
_PENDING_MODIFY_CHOICE_RE = re.compile(
    r"^\s*(?:选(?:择)?|选项|方案|按)?\s*[bBＢｂ]\s*"
    r"(?:[。．.!！,，、:：;；)\]】）]*\s*)?"
    r"(?:$|基于旧图|旧图|原图|改图|修改|modify|edit|existing)",
    re.IGNORECASE,
)
_PENDING_REGENERATE_PHRASE_RE = re.compile(
    r"(重新来画|重新画|从头画|从零画|按新设定画|照新设定画|按现在设定画|"
    r"按新版设定画|按新设定重画|use new profile|new profile)",
    re.IGNORECASE,
)
_PENDING_MODIFY_PHRASE_RE = re.compile(
    r"(基于旧图改|基于原图改|在旧图基础上改|在原图基础上改|照旧图改|"
    r"继续改旧图|用旧图改|modify existing|edit existing)",
    re.IGNORECASE,
)


def _image_gate_rel() -> str:
    return DEFAULT_MEMORY_STORE_SCOPE_PATHS.image_gate_json


def _default_state(store: MemoryStore) -> dict[str, Any]:
    return {
        "persona_revision_id": compute_persona_revision_id(store),
        "pending_confirmation": None,
        "turn_guard": {
            "turn_id": "",
            "requires_profile_persist_before_image": False,
            "profile_persisted_in_turn": False,
        },
    }


def _load_state(store: MemoryStore) -> dict[str, Any]:
    rel = _image_gate_rel()
    raw_body = store.read_document_if_exists(rel)
    if raw_body is None or not raw_body.strip():
        return _default_state(store)
    raw = json.loads(raw_body)
    if not isinstance(raw, dict):
        raise ValueError("image_gate document must contain a JSON object")
    out = _default_state(store)
    out.update(raw)
    return out


def _save_state(store: MemoryStore, state: dict[str, Any]) -> None:
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    rel = _image_gate_rel()
    store.write_document(rel, payload)


def _read_profile_doc(store: MemoryStore, relative_path: str) -> str:
    body = store.read_document_if_exists(relative_path)
    if body is not None:
        return body
    return ""


def _core_profile_payload(store: MemoryStore) -> dict[str, str]:
    return {
        "IDENTITY.md": _read_profile_doc(store, "IDENTITY.md"),
        "SOUL.md": _read_profile_doc(store, "SOUL.md"),
        "USER.md": _read_profile_doc(store, "USER.md"),
    }


def compute_persona_revision_id(store: MemoryStore) -> str:
    payload = _core_profile_payload(store)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _pending_choice_mode_from_text(txt: str) -> str | None:
    if _PENDING_REGENERATE_CHOICE_RE.search(txt):
        return "regenerate"
    if _PENDING_MODIFY_CHOICE_RE.search(txt):
        return "modify"
    if _PENDING_REGENERATE_PHRASE_RE.search(txt):
        return "regenerate"
    if _PENDING_MODIFY_PHRASE_RE.search(txt):
        return "modify"
    return None


def prepare_image_gate_for_turn(store: MemoryStore, user_text: str) -> None:
    state = _load_state(store)
    state["persona_revision_id"] = compute_persona_revision_id(store)

    txt = (user_text or "").strip()
    mode: str | None = None
    if _MODE_REGENERATE_RE.search(txt):
        mode = "regenerate"
    elif _MODE_MODIFY_RE.search(txt):
        mode = "modify"

    pending = state.get("pending_confirmation")
    if isinstance(pending, dict):
        if mode is None:
            mode = _pending_choice_mode_from_text(txt)
        if mode is not None:
            pending["selected_mode"] = mode
            pending["confirmed_at"] = utc_iso_ts()
            state["pending_confirmation"] = pending

    requires_persist = bool(
        _PROFILE_CHANGE_HINT_RE.search(txt) and _IMAGE_REQUEST_HINT_RE.search(txt)
    )
    state["turn_guard"] = {
        "turn_id": str(uuid.uuid4()),
        "requires_profile_persist_before_image": requires_persist,
        "profile_persisted_in_turn": False,
    }
    _save_state(store, state)


def register_profile_write(
    store: MemoryStore,
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
    state = _load_state(store)
    before_revision = str(state.get("persona_revision_id") or "")
    if not before_revision:
        before_revision = compute_persona_revision_id(store)
    if new_content is not None:
        payload = _core_profile_payload(store)
        payload[rel] = new_content
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        after_revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    else:
        after_revision = compute_persona_revision_id(store)
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
        turn_guard["requires_profile_persist_before_image"] = False
        state["turn_guard"] = turn_guard
    _save_state(store, state)


def check_image_tool_allowed(store: MemoryStore, *, tool_name: str) -> str | None:
    if tool_name not in {"generate_image", "modify_image"}:
        raise ValueError(f"unsupported tool for image gate: {tool_name}")
    state = _load_state(store)
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


def mark_image_tool_completed(store: MemoryStore, *, tool_name: str) -> None:
    if tool_name not in {"generate_image", "modify_image"}:
        raise ValueError(f"unsupported tool for image gate: {tool_name}")
    state = _load_state(store)
    pending = state.get("pending_confirmation")
    if isinstance(pending, dict):
        selected_mode = str(pending.get("selected_mode") or "").strip().lower()
        if (selected_mode == "regenerate" and tool_name == "generate_image") or (
            selected_mode == "modify" and tool_name == "modify_image"
        ):
            state["pending_confirmation"] = None
    state["persona_revision_id"] = compute_persona_revision_id(store)
    _save_state(store, state)


def current_persona_revision_id(store: MemoryStore) -> str:
    return compute_persona_revision_id(store)


def append_image_asset_record(store: MemoryStore, record: dict[str, Any]) -> None:
    store.append_jsonl_record(_IMAGE_ASSET_INDEX_REL, record)


def list_image_asset_records(store: MemoryStore) -> list[dict[str, Any]]:
    body = store.read_document_if_exists(_IMAGE_ASSET_INDEX_REL)
    if body is None or not body.strip():
        return []
    out: list[dict[str, Any]] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        if isinstance(row, dict):
            out.append(row)
    return out


def generated_image_meta_from_asset_record(
    row: dict[str, Any],
) -> dict[str, Any] | None:
    """Build chat_history ``generated_image`` metadata from one ``generated_images`` index row.

    With **real** GCS, prefers a canonical ``gs://`` URI when present or derivable from
    ``gcs_http_url``. If no ``gs://`` is available, accepts absolute ``http(s)://`` URLs
    (e.g. Fal CDN stored in the row).

    With **fake** GCS (``use_fake_gcs``), ``gcs_uri`` may still look like ``gs://`` but only
    maps to the local fake layout; the fetchable URL is ``gcs_http_url`` (typically
    ``file://...`` from ``Blob.public_url``), which we use as ``image_url`` when set.
    """
    from app.core.config import global_config_loaded_from_config_yaml
    from app.external_services.gcs import gs_uri_from_storage_reference_url

    w = row.get("width")
    h = row.get("height")
    base = {
        "width": w,
        "height": h,
        "format": "png",
    }

    if global_config_loaded_from_config_yaml.gcs.use_fake_gcs:
        http_u = str(row.get("gcs_http_url") or "").strip()
        if http_u:
            return {"image_url": http_u, **base}

    gcs_uri = str(row.get("gcs_uri") or "").strip()
    if not gcs_uri.startswith("gs://"):
        ref = str(row.get("gcs_http_url") or "").strip()
        if ref:
            mapped = gs_uri_from_storage_reference_url(ref)
            if mapped:
                gcs_uri = mapped

    if gcs_uri.startswith("gs://"):
        return {"image_url": gcs_uri, **base}

    for candidate in (
        str(row.get("gcs_uri") or "").strip(),
        str(row.get("gcs_http_url") or "").strip(),
    ):
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return {"image_url": candidate, **base}
    return None


def generated_image_meta_from_index_slice(
    store: MemoryStore, baseline_index: int
) -> dict[str, Any] | None:
    """Return metadata for the latest new asset rows since ``baseline_index`` (list length offset)."""
    records = list_image_asset_records(store)
    if baseline_index < 0 or baseline_index > len(records):
        return None
    for row in reversed(records[baseline_index:]):
        meta = generated_image_meta_from_asset_record(row)
        if meta is not None:
            return meta
    return None


def _normalize_relative_path_for_index(path: str) -> str:
    return (path or "").strip().replace("\\", "/")


def find_latest_asset_by_local_relative_path(
    store: MemoryStore, relative_path: str
) -> dict[str, Any] | None:
    target = _normalize_relative_path_for_index(relative_path)
    if not target:
        return None
    for row in reversed(list_image_asset_records(store)):
        if (
            _normalize_relative_path_for_index(
                str(row.get("local_path_relative") or "")
            )
            == target
        ):
            return row
    return None


def relative_path_under_workspace(store: MemoryStore, absolute_path: Path) -> str:
    """Map a local absolute path to a scope-relative key segment (basename when not under synthetic root)."""
    return PurePosixPath(absolute_path.resolve().as_posix()).name
