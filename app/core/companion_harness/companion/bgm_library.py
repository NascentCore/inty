"""Static BGM catalog (BGM_LIBRARY.jsonl) and tool-background delivery helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

SET_BGM_TOOL_NAME = "set_bgm"
SET_BGM_OK_PREFIX = "OK "

_BGM_LIBRARY_REL = Path(__file__).resolve().parent.parent / "data" / "BGM_LIBRARY.jsonl"
_cached_mtime_ns: int | None = None
_cached_tracks_by_id: dict[str, BgmLibraryTrack] = {}


class BgmLibraryTrack(BaseModel):
    """One row from BGM_LIBRARY.jsonl."""

    track_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    audio_url: str = Field(..., min_length=1)
    duration_sec: float = Field(..., gt=0.0)
    tags: list[str] = Field(default_factory=list)


def bgm_library_path() -> Path:
    return _BGM_LIBRARY_REL


def load_bgm_library() -> dict[str, BgmLibraryTrack]:
    """Load BGM_LIBRARY.jsonl; reload when mtime changes."""
    global _cached_mtime_ns, _cached_tracks_by_id
    path = bgm_library_path()
    assert path.is_file(), f"BGM_LIBRARY missing: {path}"
    mtime_ns = path.stat().st_mtime_ns
    if _cached_mtime_ns == mtime_ns and _cached_tracks_by_id:
        return _cached_tracks_by_id
    by_id: dict[str, BgmLibraryTrack] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"BGM_LIBRARY.jsonl line {line_no}: invalid JSON") from exc
        try:
            track = BgmLibraryTrack.model_validate(row)
        except ValidationError as exc:
            raise ValueError(f"BGM_LIBRARY.jsonl line {line_no}: {exc}") from exc
        if track.track_id in by_id:
            raise ValueError(
                f"BGM_LIBRARY.jsonl line {line_no}: duplicate track_id={track.track_id!r}"
            )
        by_id[track.track_id] = track
    assert by_id, "BGM_LIBRARY.jsonl must contain at least one track"
    _cached_mtime_ns = mtime_ns
    _cached_tracks_by_id = by_id
    return by_id


def get_bgm_track(track_id: str) -> BgmLibraryTrack | None:
    tid = track_id.strip()
    if not tid:
        return None
    return load_bgm_library().get(tid)


def format_bgm_catalog_for_system_message() -> str:
    lines: list[str] = []
    for track in load_bgm_library().values():
        tag_s = ",".join(track.tags) if track.tags else "-"
        lines.append(
            f"track_id={track.track_id} | title={track.title} | "
            f"tags={tag_s} | duration_sec={track.duration_sec}"
        )
    return "\n".join(lines)


def tool_set_bgm_payload(track: BgmLibraryTrack, reason: str) -> dict[str, Any]:
    return {
        "track_id": track.track_id,
        "title": track.title,
        "audio_url": track.audio_url,
        "duration_sec": track.duration_sec,
        "tags": list(track.tags),
        "reason": reason.strip(),
    }


def tool_set_bgm(_store: object, track_id: str, reason: str) -> str:
    track = get_bgm_track(track_id)
    if track is None:
        return f"ERROR: unknown track_id={track_id.strip()!r}"
    payload = tool_set_bgm_payload(track, reason)
    return SET_BGM_OK_PREFIX + json.dumps(payload, ensure_ascii=False)


def tools_include_set_bgm(openai_tools: list[dict[str, Any]]) -> bool:
    for t in openai_tools:
        if t.get("type") != "function":
            continue
        fn = t.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if isinstance(name, str) and name.strip() == SET_BGM_TOOL_NAME:
            return True
    return False


def extract_set_bgm_deliver_payload(
    appended_turn_msgs: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Parse successful set_bgm tool result from one background tool round."""
    pending: dict[str, str] = {}
    for m in appended_turn_msgs:
        if m.get("role") == "assistant":
            pending.clear()
            for tc in m.get("tool_calls") or []:
                if not isinstance(tc, dict):
                    continue
                tid = tc.get("id")
                fn = tc.get("function")
                if not isinstance(fn, dict):
                    continue
                raw_name = fn.get("name")
                if isinstance(tid, str) and isinstance(raw_name, str):
                    n = raw_name.strip()
                    if n:
                        pending[tid] = n
            continue
        if m.get("role") != "tool":
            continue
        tid = m.get("tool_call_id")
        if not isinstance(tid, str):
            continue
        name = pending.get(tid)
        if name != SET_BGM_TOOL_NAME:
            continue
        content = m.get("content")
        if not isinstance(content, str):
            continue
        piece = content.strip()
        if not piece.startswith(SET_BGM_OK_PREFIX):
            continue
        json_part = piece[len(SET_BGM_OK_PREFIX) :].strip()
        try:
            parsed = json.loads(json_part)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed
    return None
