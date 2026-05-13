"""Companion tool runtime: schemas, dispatch, and ``execute_tool_call`` for the REPL/Companion Harness.

Persisted companion documents and transcript go through MemoryStore; tool paths align with
``memory_store_document_mapping``.
"""

from __future__ import annotations

import os
import asyncio
import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable

from pydantic import ValidationError

from app.core.companion_harness.tools.registry import ToolRegistry
from app.core.companion_harness.tools.dispatchers.media import (
    parse_optional_positive_int,
    parse_optional_strength,
)
from app.core.companion_harness.tools.dispatchers.memory_store import (
    dispatch_memory_store_tool,
)

from .fal_z_image_tool import (
    MAX_NUM_IMAGES_PER_CALL,
    reset_fal_async_client_after_short_lived_loop,
    run_generate_image_z_image_turbo,
    run_modify_image_z_image_turbo,
)
from .image_gate import (
    check_image_tool_allowed,
    current_persona_revision_id,
    find_latest_asset_by_local_relative_path,
    list_image_asset_records,
    mark_image_tool_completed,
    register_profile_write,
)
from .bootstrap_user_interactive import (
    PROMPT_SLICE_TO_REL,
    soul_prompt_is_locked_after_interactive_bootstrap,
    tool_companion_bootstrap_user_interactive_complete,
    tool_companion_set_experience_profile,
    tool_companion_update_prompt_slice,
)
from .message_format import openai_assistant_message_dict
from .memory_store_document_mapping import parse_memory_store_relative_path
from .memory_store import MemoryStore, normalize_memory_store_relative_path
from .models import ChatMessage, load_context_meta
from .google_web_search import run_google_web_search
from .read_web_page import run_read_web_page
from .runtime_inspect_tool import tool_companion_runtime_inspect
from .openai_tools_prepare import prepare_openai_tools_for_chat_completions
from .schedule_queue import add_schedule_task
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.global_services import subscription_service
from app.services.agent_status_line import tool_update_agent_status_line
from app.services.phone_call_service import (
    PhoneCallConfigError,
    PhoneCallLimitError,
    phone_call_service,
)
from sqlalchemy import select

_USER_MD_REL = "USER.md"
_USER_PROFILE_SECTION = "## 身份信息"
# GENERATION: 成功产出应对用户可见的交付物时, async tool_background **必须**下行到客户端;
# 是否附加 NL 由统一收尾信封中的 ``output_to_user`` 与产物回填共同决定（见 tool_background）。
TOOL_TAG_GENERATION = "GENERATION"
_TOOL_TAGS_BY_NAME: dict[str, frozenset[str]] = {
    "generate_image": frozenset({TOOL_TAG_GENERATION}),
    "modify_image": frozenset({TOOL_TAG_GENERATION}),
}

# memory_store_read_document：可选 max_chars 上限，避免单次 tool 返回撑爆上下文。
MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP: int = 120_000

# REPL 对话轮允许整文件覆盖写入的相对路径（根目录约定文档；不含 transcript/context 等）
REPL_WRITABLE_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "IDENTITY.md",
        "MEMORY.md",
        "SOUL.md",
        "USER.md",
    }
)


def _latest_generated_image_http_url_from_index(store: MemoryStore) -> str | None:
    for row in reversed(list_image_asset_records(store)):
        u = str(row.get("gcs_http_url") or "").strip()
        if u.startswith("http://") or u.startswith("https://"):
            return u
    return None


def _is_orm_mapped_store_relative_path(relative_path: str) -> bool:
    rel = (relative_path or "").strip().replace("\\", "/")
    try:
        parse_memory_store_relative_path(rel)
    except ValueError:
        return False
    return True


def _list_dir_prefix_for_store_query(rel_dir: str) -> str:
    """Treat Path.relative_to(workspace) of '.' or '' as workspace root for DB prefix matching."""
    s = rel_dir.strip().replace("\\", "/").rstrip("/")
    if s in (".", ""):
        return ""
    return s


def _tool_rel_posix_from_arg(relative_path: str) -> str:
    s = (relative_path or "").strip().replace("\\", "/")
    if s in (".", ""):
        return ""
    return normalize_memory_store_relative_path(s)


def _list_dir_extra_names_from_store(store: MemoryStore, rel_dir: str) -> set[str]:
    paths = store.iter_stored_relative_paths()
    prefix = _list_dir_prefix_for_store_query(rel_dir)
    pfx = f"{prefix}/" if prefix else ""
    out: set[str] = set()
    for sp in paths:
        sp = sp.strip().replace("\\", "/")
        if prefix:
            if not sp.startswith(pfx):
                continue
            rest = sp[len(pfx) :]
        else:
            rest = sp
        if not rest:
            continue
        if "/" in rest:
            out.add(rest.split("/")[0] + "/")
        else:
            out.add(rest)
    return out


_BASE_TOOL_REGISTRY = ToolRegistry(
    (
        "memory_store_list_paths",
        "memory_store_read_document",
        "memory_store_write_document",
        "memory_store_mkdir",
        "user_profile_record",
        "schedule_task",
        "google_web_search",
        "read_web_page",
        "phone_call_user",
        "generate_image",
        "modify_image",
        "companion_runtime_inspect",
        "companion_set_experience_profile",
        "companion_update_prompt_slice",
        "companion_bootstrap_user_interactive_complete",
        "tool_update_agent_status_line",
    )
)


def tool_has_tag(tool_name: str, tag: str) -> bool:
    """Return whether a tool declares a given behavior tag."""
    tags = _TOOL_TAGS_BY_NAME.get(tool_name, frozenset())
    return tag in tags


def tool_requires_client_delivery_on_success(tool_name: str) -> bool:
    """True when the tool produces user-visible artifacts that must reach the client if successful."""
    return tool_has_tag(tool_name, TOOL_TAG_GENERATION)


def round_includes_generation_tool(tool_names: Iterable[str]) -> bool:
    return any(tool_requires_client_delivery_on_success(n) for n in tool_names)


def append_user_profile_facts_to_user_md(text: str, new_bullets: list[str]) -> str:
    """
    在 USER.md 的「身份信息」小节追加条目；若尚无该小节则在文末追加。
    new_bullets 每项应为完整一行（含前导 `- `）。
    """
    lines = text.splitlines()
    if _USER_PROFILE_SECTION not in lines:
        block = "\n\n" + _USER_PROFILE_SECTION + "\n\n" + "\n".join(new_bullets)
        return text.rstrip() + block + "\n"
    idx = lines.index(_USER_PROFILE_SECTION)
    j = idx + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    insert_at = j
    while insert_at < len(lines) and not lines[insert_at].startswith("## "):
        insert_at += 1
    for k, b in enumerate(new_bullets):
        lines.insert(insert_at + k, b)
    return "\n".join(lines) + "\n"


def tool_user_profile_record(store: MemoryStore, items: list[dict[str, Any]]) -> str:
    """
    将用户自愿透露的基本信息追加写入 USER.md 的「身份信息」小节。
    items：每项含 label、value（均为非空短文本）。
    """
    rel = _USER_MD_REL
    prev = store.read_document_if_exists(rel)
    if prev is None:
        return f"ERROR: missing {_USER_MD_REL!r}"
    today = date.today().isoformat()
    bullets: list[str] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label", "")).strip()
        value = str(raw.get("value", "")).strip()
        if not label or not value:
            continue
        bullets.append(f"- {label}：{value}（记录日期 {today}）")
    if not bullets:
        return "ERROR: no valid items (need label and value for each entry)"
    merged = append_user_profile_facts_to_user_md(prev, bullets)
    store.write_document(rel, merged)
    register_profile_write(
        store,
        rel,
        changed=(merged != prev),
        new_content=merged,
    )
    return f"OK appended {len(bullets)} line(s) to {_USER_MD_REL}"


def tool_memory_store_list_paths(
    store: MemoryStore,
    relative_path: str,
    *,
    repository_only_store_text: bool = False,
) -> str:
    """列出目录下的直接子项（文件与目录名）；目录名以 / 结尾；仅来自 MemoryStore。"""
    _ = repository_only_store_text
    rel_dir_raw = _tool_rel_posix_from_arg(relative_path)
    list_prefix = _list_dir_prefix_for_store_query(rel_dir_raw)
    lines = _list_dir_extra_names_from_store(store, list_prefix)
    ordered = sorted(lines, key=lambda s: s.lower())
    return "\n".join(ordered) if ordered else "(empty)"


def _parse_optional_max_chars(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ValueError("max_chars must be a positive integer or omitted")
    n: int
    if isinstance(raw, int):
        n = raw
    elif isinstance(raw, float) and raw.is_integer():
        n = int(raw)
    else:
        raise ValueError("max_chars must be a positive integer or omitted")
    if n < 1:
        raise ValueError("max_chars must be at least 1")
    if n > MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP:
        raise ValueError(
            f"max_chars must be at most {MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP}"
        )
    return n


def tool_memory_store_read_document(
    store: MemoryStore,
    relative_path: str,
    max_chars: int | None = None,
    *,
    repository_only_store_text: bool = False,
) -> str:
    _ = repository_only_store_text
    rel = _tool_rel_posix_from_arg(relative_path)
    st = store
    if not _is_orm_mapped_store_relative_path(rel):
        return f"ERROR: path is not a persisted companion document: {relative_path!r}"
    body = st.read_document_if_exists(rel)
    if body is None:
        return f"ERROR: not a file: {relative_path!r}"
    if max_chars is None:
        return body
    if len(body) <= max_chars:
        return body
    return (
        body[:max_chars] + "\n…[truncated: prefix only; file is longer than max_chars]"
    )


def _transcript_jsonl_validate_for_tool_write(content: str) -> str | None:
    if not content.strip():
        return None
    for i, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as e:
            return f"ERROR: transcript JSONL line {i} is not valid JSON: {e}"
        try:
            ChatMessage.model_validate(raw)
        except ValidationError as e:
            return (
                f"ERROR: transcript JSONL line {i} must be JSON with "
                f'role ("user"|"assistant"|"system"), content (string), '
                f"ts (ISO8601 UTC, e.g. ...Z). Example: "
                f'{{"role":"system","content":"marker","ts":"2026-01-01T00:00:00Z"}}. '
                f"Details: {e}"
            )
    return None


def tool_memory_store_write_document(
    store: MemoryStore,
    relative_path: str,
    content: str,
    *,
    repository_only_store_text: bool = False,
) -> str:
    _ = repository_only_store_text
    rel = _tool_rel_posix_from_arg(relative_path)
    st = store
    if not _is_orm_mapped_store_relative_path(rel):
        return f"ERROR: cannot write {relative_path!r} (not a persisted companion document)"
    if rel == "SOUL.md" and soul_prompt_is_locked_after_interactive_bootstrap(store=st):
        return (
            "ERROR: SOUL.md is immutable after interactive bootstrap completes; "
            "you may still update IDENTITY.md, USER.md, MEMORY.md, and other allowed paths."
        )
    prev_body = st.read_document_if_exists(rel)
    if rel in ("transcript.jsonl", "transcript_inner_tick.jsonl"):
        v_err = _transcript_jsonl_validate_for_tool_write(content)
        if v_err is not None:
            return v_err
    st.write_document(rel, content)
    changed = prev_body != content
    register_profile_write(store, rel, changed=changed, new_content=content)
    return f"OK wrote {len(content)} chars to {relative_path}"


def tool_memory_store_mkdir(store: MemoryStore, relative_path: str) -> str:
    _ = store, relative_path
    return "OK mkdir (logical prefix only; companion MemoryStore has no host filesystem dirs)"


def tool_schedule_task(store: MemoryStore, exec_time_utc: str, task_text: str) -> str:
    task_id = add_schedule_task(
        store,
        exec_time_utc=exec_time_utc,
        task_text=task_text,
    )
    return (
        "OK scheduled task "
        f"id={task_id} exec_time_utc={exec_time_utc} text={task_text.strip()}"
    )


async def tool_phone_call_user(root: Path, phone_number: str, reason: str) -> str:
    store = get_memory_store(root)
    context = load_context_meta(root / "context.json", store=store)
    user_id = context.user_id.strip()
    agent_id = context.companion_id.strip()
    if not user_id or not agent_id:
        return "ERROR: phone call requires active user and companion context"
    async with AsyncSessionLocal() as db:
        row = await db.execute(select(User).where(User.id == user_id))
        user = row.scalar_one_or_none()
        if user is None or user.deleted_at:
            return "ERROR: phone call user context no longer exists"
        try:
            result = await phone_call_service.start_outbound_call(
                db=db,
                current_user=user,
                agent_id=agent_id,
                phone_number=phone_number,
                subscription_svc=subscription_service,
                reason=reason,
            )
        except PhoneCallLimitError as exc:
            return f"ERROR: {exc}"
        except (PhoneCallConfigError, ValueError) as exc:
            return f"ERROR: {exc}"
    return (
        "OK phone call queued "
        f"to={result.to_number_masked} status={result.status} call_sid={result.call_sid}"
    )


def build_openai_tools() -> list[dict[str, Any]]:
    """OpenAI Chat Completions `tools` 列表。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "memory_store_list_paths",
                "description": (
                    "List immediate children under the synthetic MemoryStore scope root. "
                    "Use empty relative_path for the scope root. "
                    "Directory names are shown with a trailing slash. "
                    "Backing store is MemoryStore; listing is derived from stored paths, not a host filesystem scan."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Directory relative to scope root; use '' for root.",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory_store_read_document",
                "description": (
                    "Read a UTF-8 logical document from MemoryStore. "
                    "Optional max_chars returns only the beginning of the document (prefix), "
                    f"up to {MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP}, to limit tool output size. "
                    "Paths are scope-relative (e.g. IDENTITY.md, memory/daily/YYYY-MM-DD.md)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Document path relative to MemoryStore scope root.",
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": (
                                "If set, return at most this many characters from the start of the document "
                                f"(1..{MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP}). Omit to read the full document."
                            ),
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory_store_write_document",
                "description": (
                    "Create or overwrite a UTF-8 logical document in MemoryStore. "
                    "Paths are scope-relative; no host mkdir is required."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Document path relative to MemoryStore scope root.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full file content.",
                        },
                    },
                    "required": ["relative_path", "content"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory_store_mkdir",
                "description": (
                    "No-op compatibility hook: MemoryStore has no host directories; "
                    "logical prefixes are implied by relative paths."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Ignored logical prefix (scope-relative path convention).",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "user_profile_record",
                "description": (
                    "Append structured facts about the user to USER.md under «身份信息». "
                    "Call when the user shares durable basic info (e.g. age, how they wish to be called, "
                    "timezone) that should persist. Do not use for secrets unless the user clearly wants "
                    "them remembered. Speak to the user in companion language only; never mention tools, "
                    "JSON, or filenames."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "description": "One or more label/value pairs to append.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {
                                        "type": "string",
                                        "description": "Short field name, e.g. 年龄、称呼偏好.",
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "What the user said or agreed to store.",
                                    },
                                },
                                "required": ["label", "value"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["items"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "schedule_task",
                "description": (
                    "Persist a timed reminder task into the local schedule queue. "
                    "Use when the user explicitly asks for a reminder/timer/alarm at a future time. "
                    "exec_time_utc must be an absolute timestamp with timezone offset (ISO8601); "
                    "prefer UTC (e.g. 2026-04-03T05:30:00+00:00). "
                    "task_text should be the concise reminder content shown at trigger time."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exec_time_utc": {
                            "type": "string",
                            "description": (
                                "Absolute execution timestamp with timezone offset. "
                                "Example: 2026-04-03T05:30:00+00:00"
                            ),
                        },
                        "task_text": {
                            "type": "string",
                            "description": ("Reminder text to execute at that time."),
                        },
                    },
                    "required": ["exec_time_utc", "task_text"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "tool_update_agent_status_line",
                "description": (
                    "Set the short one-line status shown under your name in the user's chat header "
                    "(mood, vibe, or current thought). Use the same language as the user. "
                    "Keep it brief (roughly one short sentence). Pass an empty string to clear it. "
                    "Do not mention this tool or raw JSON to the user. "
                    "The tool returns a single line: status line cleared, or "
                    'status line updated to "..."; mirror that in your natural reply when needed.'
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status_line": {
                            "type": "string",
                            "description": (
                                "Header subtitle text, or empty string to clear."
                            ),
                        },
                    },
                    "required": ["status_line"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "phone_call_user",
                "description": (
                    "Place an outbound phone call to the user through the configured PSTN provider. "
                    "Use only when the current user message explicitly asks you to call now and provides "
                    "the phone number in that same message (for example, 'Call me at 1234560123'). "
                    "Never call a number inferred from memory, old messages, or guesses. "
                    "Do not use from proactive/implicit greeting contexts."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "User-provided phone number from the current message.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Short reason for audit logs, based on the user's explicit request.",
                        },
                    },
                    "required": ["phone_number", "reason"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def _openai_interactive_bootstrap_tools() -> list[dict[str, Any]]:
    slice_enum = sorted(s.value for s in PROMPT_SLICE_TO_REL)
    return [
        {
            "type": "function",
            "function": {
                "name": "companion_update_prompt_slice",
                "description": (
                    "Overwrite one workspace prompt slice (root markdown) in MemoryStore. "
                    "Use during interactive relationship bootstrap instead of memory_store_write_document. "
                    "Pass the full updated markdown as content. "
                    "After companion_bootstrap_user_interactive_complete, SOUL is locked; "
                    "IDENTITY / USER / MEMORY may still be updated. "
                    "TOOLS / significance-perception operator text are fixed package templates, not slices."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slice": {
                            "type": "string",
                            "enum": slice_enum,
                            "description": "Which prompt document to replace.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full UTF-8 body to write for that slice.",
                        },
                    },
                    "required": ["slice", "content"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "companion_bootstrap_user_interactive_complete",
                "description": (
                    "Mark interactive workspace bootstrap as finished in context.json. "
                    "Bootstrap here means the SOUL slice has been initialized for this relationship; "
                    "after this call SOUL.md must not change (tools and background updates). "
                    "Call when that phase is done; IDENTITY / USER / MEMORY slices may still be edited later."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note": {
                            "type": "string",
                            "description": "Optional short internal note (not shown to user).",
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
        },
    ]


def build_openai_repl_tools(
    *, interactive_bootstrap_active: bool = False
) -> list[dict[str, Any]]:
    """
    REPL 对话轮：用户档案追加 + 工作区文档读写（写入仅限 REPL_WRITABLE_RELATIVE_PATHS）。
    """
    disable_status = os.getenv(
        "INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL", ""
    ).strip().lower() in ("1", "true", "yes", "on")

    full = build_openai_tools()
    by_name = {
        t["function"]["name"]: t
        for t in full
        if t.get("type") == "function" and "function" in t
    }
    if interactive_bootstrap_active:
        names = (
            "user_profile_record",
            "schedule_task",
            "tool_update_agent_status_line",
            "memory_store_list_paths",
            "memory_store_read_document",
        )
    else:
        names = (
            "user_profile_record",
            "schedule_task",
            "tool_update_agent_status_line",
            "memory_store_list_paths",
            "memory_store_read_document",
            "memory_store_write_document",
            "phone_call_user",
        )
    if disable_status:
        names = tuple(n for n in names if n != "tool_update_agent_status_line")
    out: list[dict[str, Any]] = []
    for n in names:
        t = by_name.get(n)
        if not t:
            raise KeyError(f"missing tool definition: {n!r}")
        if n == "memory_store_list_paths":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "List immediate children under the MemoryStore scope root. "
                "Use empty relative_path for the scope root. "
                "Directory names end with /. Backing store is MemoryStore; listing is derived from stored paths, "
                "not a host filesystem scan. Prefer memory_store_read_document when the path is known; list mainly "
                "when you need sibling names or layout before reading."
            )
            w["function"] = wfn
            out.append(w)
        elif n == "memory_store_read_document":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "Read a UTF-8 document from MemoryStore for self-orientation (profile docs, "
                "context.json, memory/*) or before editing allowed root markdown files. "
                "Optional max_chars (1.."
                + str(MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP)
                + ") returns only a prefix of the file to avoid huge tool results; omit for full file. "
                "transcript.jsonl can be very large—prefer the conversation already in the message "
                "history; if you must read it via this tool from the persisted store, always pass max_chars."
            )
            w["function"] = wfn
            out.append(w)
        elif n == "memory_store_write_document":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "Create or overwrite a UTF-8 logical document in MemoryStore. "
                "In REPL, only these root files are writable: "
                + ", ".join(sorted(REPL_WRITABLE_RELATIVE_PATHS))
                + ". When the user explicitly asks to change how you relate, boundaries, or "
                "persistent preferences, read the current file first (e.g. SOUL.md, USER.md), "
                "then write the full updated content. Do not use for transcript.jsonl or context.json."
            )
            w["function"] = wfn
            out.append(w)
        elif n == "schedule_task":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "Persist a timed reminder task into the durable local schedule queue. "
                "Use only when user explicitly requests a reminder/timer/alarm at a future time. "
                "You must pass an absolute ISO8601 timestamp with timezone offset in exec_time_utc "
                "(prefer UTC)."
            )
            w["function"] = wfn
            out.append(w)
        else:
            out.append(t)
    out.append(
        {
            "type": "function",
            "function": {
                "name": "companion_runtime_inspect",
                "description": (
                    "Return a JSON snapshot of the current companion runtime: in-process LLM config, "
                    "last chat.completions request (model, messages, tools_summary, OpenRouter extra kwargs), "
                    "runtime events, and optionally workspace documents from MemoryStore "
                    "(SOUL, USER, MEMORY.md, episodic/gist day paths). "
                    "Use when the user asks for verifiable facts about the active model, parameters, or injected "
                    "prompt stack. For self-check only: answer the user in natural language without reading "
                    "this JSON aloud verbatim."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_chars_per_doc": {
                            "type": "integer",
                            "description": "Max characters per stored document body (default 8000, min 100).",
                        },
                        "max_chars_llm_messages": {
                            "type": "integer",
                            "description": (
                                "Max serialized size for last request messages array "
                                "(default 120000, min 1000)."
                            ),
                        },
                        "include_store_documents": {
                            "type": "boolean",
                            "description": "If false, omit MemoryStore document bodies (default true).",
                        },
                        "max_runtime_events": {
                            "type": "integer",
                            "description": "Max newest runtime event records to include (default 20, min 0).",
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
        }
    )
    out.append(
        {
            "type": "function",
            "function": {
                "name": "companion_set_experience_profile",
                "description": (
                    "Persist the session experience profile id into context.json as context_mode "
                    "(normalized lowercase). Call only after the user explicitly agrees to switch "
                    "(e.g. roleplay vs emotional companion). Requires user_confirmed=true; never "
                    "infer silently. Takes effect on the next companion turn; do not use "
                    "memory_store_write_document on context.json."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "context_mode": {
                            "type": "string",
                            "description": (
                                "Target experience profile id (e.g. intimate, emotional_companion, "
                                "roleplay, interactive_fiction, public)."
                            ),
                        },
                        "user_confirmed": {
                            "type": "boolean",
                            "description": (
                                "Must be true only when the user clearly confirmed the mode switch "
                                "in this conversation."
                            ),
                        },
                        "note": {
                            "type": "string",
                            "description": "Optional short internal note (not shown to user).",
                        },
                    },
                    "required": ["context_mode", "user_confirmed"],
                    "additionalProperties": False,
                },
            },
        }
    )
    out.append(
        {
            "type": "function",
            "function": {
                "name": "google_web_search",
                "description": (
                    "Search the public web via Google Custom Search JSON API. "
                    "Use when the user needs current events, verifiable facts, or information "
                    "not present in the workspace or conversation. "
                    "Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID in the environment. "
                    "Summarize results in natural language to the user without exposing raw JSON or tool names."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query in the user's language or English.",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "How many results to return (1..10). Omit for 10.",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        }
    )
    out.append(
        {
            "type": "function",
            "function": {
                "name": "read_web_page",
                "description": (
                    "Download an HTML page over HTTP(S), extract readable text, and return a concise "
                    "markdown bullet-point summary of key information. "
                    "Also appends the same takeaway bullets under a dated heading in workspace MEMORY.md "
                    "for long-term recall. "
                    "Use for one URL at a time when the user wants article/page content (not just search snippets). "
                    "Does not execute JavaScript; script-heavy SPAs may yield sparse text."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": (
                                "Absolute http(s) URL of the page to fetch (public hosts only; "
                                "localhost is blocked)."
                            ),
                        },
                        "max_bullets": {
                            "type": "integer",
                            "description": (
                                "Maximum markdown bullet points in the summary (3..20). Omit for 10."
                            ),
                        },
                    },
                    "required": ["url"],
                    "additionalProperties": False,
                },
            },
        }
    )
    out.append(
        {
            "type": "function",
            "function": {
                "name": "generate_image",
                "x-tags": [TOOL_TAG_GENERATION],
                "description": (
                    "Generate **new** image(s) from text only using Fal z-image-turbo (text-to-image). "
                    "Do **not** use this tool when the user wants to edit, restyle, or inpaint an **existing** image—"
                    "use modify_image (image-to-image) instead, with the source file or URL. "
                    "Call only when the user clearly asks for new picture(s), illustration(s), or visuals from scratch. "
                    "**Identity / portrait lock:** If the output must depict the companion’s agreed look "
                    "(e.g. zodiac-year portrait 生肖像, themed or holiday portrait), treat the **appearance** subsection "
                    "in workspace **IDENTITY.md** (e.g. section titled like 外貌与形象) as the **fixed visual blueprint**: "
                    "copy hair, eyes, face, and other stated traits into `prompt`; do **not** invent, swap, or weaken "
                    "those locked traits—zodiac/theme may only add costume, props, setting, or mood on top. "
                    "Set num_images from conversation context: e.g. user asks for three variants or "
                    "multiple angles → pass that count; single scene or unspecified → omit num_images "
                    f"(defaults to 1). Maximum {MAX_NUM_IMAGES_PER_CALL} per call. "
                    "Requires repo-root config.yaml (fal.api_key, gcs.*, app.gcp_service_account_key) when importing app. "
                    "After success, describe in companion language without reading raw URLs aloud unless helpful."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": (
                                "Full English or Chinese scene description for the image "
                                "(style, subject, mood, composition). "
                                "For companion portraits (incl. zodiac 生肖像): embed traits from IDENTITY.md "
                                "appearance section; do not contradict locked hair/face/eye details."
                            ),
                        },
                        "image_size": {
                            "type": "string",
                            "description": (
                                "Optional fal preset, e.g. portrait_4_3, square_hd, landscape_16_9. "
                                "Omit for prototype default (portrait_4_3)."
                            ),
                        },
                        "num_inference_steps": {
                            "type": "integer",
                            "description": "Optional inference steps (default 8). Must be >= 1.",
                        },
                        "num_images": {
                            "type": "integer",
                            "description": (
                                "How many images to generate this call: infer from the user message "
                                "(e.g. «三张」「几个版本» → matching count). Omit for a single image (default 1). "
                                f"Must be 1..{MAX_NUM_IMAGES_PER_CALL}."
                            ),
                        },
                    },
                    "required": ["prompt"],
                    "additionalProperties": False,
                },
            },
        }
    )
    out.append(
        {
            "type": "function",
            "function": {
                "name": "modify_image",
                "x-tags": [TOOL_TAG_GENERATION],
                "description": (
                    "Edit or restyle an **existing** image using Fal z-image-turbo **image-to-image** "
                    "(not text-to-image). Use when the user asks to change, fix, recolor, restyle, or otherwise "
                    "modify a specific picture—including one previously saved under workspace/generated_images/. "
                    "Provide exactly one source: either source_image_relative_path (file under workspace, e.g. "
                    "generated_images/z_image_....jpeg) or source_image_url (public http(s) URL). "
                    "If both are omitted, it will auto-use the most recent image file under generated_images/. "
                    "**Identity lock:** For themed restyles (e.g. zodiac 生肖), align `prompt` with **IDENTITY.md** "
                    "appearance traits; preserve locked facial/hair features—use prompt for additive theme/costume/scene, "
                    "not to replace the agreed face. "
                    "Optional strength (0–1) controls how strongly the output follows the prompt vs. the source. "
                    "Same config/GCS requirements as generate_image."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": (
                                "What to change or the desired look (style, edits, constraints); "
                                "the model conditions on the source image. "
                                "Themed edits (e.g. 生肖): add costume/scene/mood; keep IDENTITY.md appearance-locked traits."
                            ),
                        },
                        "source_image_relative_path": {
                            "type": "string",
                            "description": (
                                "Workspace-relative path to an image file (jpg/png/webp/gif). "
                                "Use e.g. generated_images/... from a prior generate_image result. "
                                "Omit if using source_image_url; if both source fields are omitted, "
                                "the latest image under generated_images/ is used."
                            ),
                        },
                        "source_image_url": {
                            "type": "string",
                            "description": (
                                "Public http(s) URL of the image to edit. Omit if using source_image_relative_path."
                            ),
                        },
                        "image_size": {
                            "type": "string",
                            "description": (
                                "Optional fal preset (e.g. portrait_4_3, square_hd). "
                                "Omit for prototype default (portrait_4_3)."
                            ),
                        },
                        "num_inference_steps": {
                            "type": "integer",
                            "description": "Optional inference steps (default 8). Must be >= 1.",
                        },
                        "strength": {
                            "type": "number",
                            "description": (
                                "Optional 0..1; higher = follow prompt more, lower = stay closer to source (default 0.6)."
                            ),
                        },
                    },
                    "required": ["prompt"],
                    "additionalProperties": False,
                },
            },
        }
    )
    if interactive_bootstrap_active:
        out.extend(_openai_interactive_bootstrap_tools())
    return prepare_openai_tools_for_chat_completions(out)


_INNER_TICK_REPL_TOOL_NAMES: tuple[str, ...] = (
    "user_profile_record",
    "tool_update_agent_status_line",
    "memory_store_list_paths",
    "memory_store_read_document",
    "memory_store_write_document",
)


def build_openai_repl_tools_inner_tick() -> list[dict[str, Any]]:
    """
    内在节拍：仅 USER 档案与工作区读写，不含定时、联网、生图/改图。
    """
    full = build_openai_repl_tools()
    want = set(_INNER_TICK_REPL_TOOL_NAMES)
    picked = [
        t
        for t in full
        if t.get("type") == "function" and t.get("function", {}).get("name") in want
    ]
    by_name = {t["function"]["name"]: t for t in picked}
    missing = want - set(by_name)
    if missing:
        raise RuntimeError(
            f"build_openai_repl_tools_inner_tick: missing tool defs {sorted(missing)}"
        )
    return [by_name[n] for n in _INNER_TICK_REPL_TOOL_NAMES]


def _repl_write_allowed(
    store: MemoryStore, relative_path: str, write_allowlist: frozenset[str]
) -> str | None:
    """若不允许写入则返回错误信息字符串，否则 None。"""
    try:
        rel_posix = _tool_rel_posix_from_arg(relative_path)
    except ValueError as exc:
        return f"ERROR: {exc}"
    if rel_posix not in write_allowlist:
        return (
            "ERROR: REPL memory_store_write_document only allows: "
            + ", ".join(sorted(write_allowlist))
            + f"; got {rel_posix!r}"
        )
    return None


async def _dispatch(
    store: MemoryStore,
    name: str,
    arguments: dict[str, Any],
    *,
    write_allowlist: frozenset[str] | None = None,
    repository_only_store_text: bool = False,
) -> str:
    _ = repository_only_store_text
    if not _BASE_TOOL_REGISTRY.is_allowed(name):
        return f"ERROR: unknown tool {name!r}"

    memory_store_dispatch_result = dispatch_memory_store_tool(
        store=store,
        name=name,
        arguments=arguments,
        write_allowlist=write_allowlist,
        tool_memory_store_list_paths=tool_memory_store_list_paths,
        tool_memory_store_read_document=tool_memory_store_read_document,
        tool_memory_store_write_document=tool_memory_store_write_document,
        tool_memory_store_mkdir=tool_memory_store_mkdir,
        tool_user_profile_record=tool_user_profile_record,
        parse_optional_max_chars=_parse_optional_max_chars,
        repl_write_allowed=_repl_write_allowed,
    )
    if memory_store_dispatch_result is not None:
        return memory_store_dispatch_result
    if name == "tool_update_agent_status_line":
        raw_sl = arguments.get("status_line")
        if not isinstance(raw_sl, str):
            return "ERROR: status_line must be a string"
        return await tool_update_agent_status_line(store, raw_sl)
    if name == "schedule_task":
        raw_exec_time = arguments.get("exec_time_utc")
        raw_task_text = arguments.get("task_text")
        if not isinstance(raw_exec_time, str):
            return "ERROR: exec_time_utc must be a string"
        if not isinstance(raw_task_text, str):
            return "ERROR: task_text must be a string"
        try:
            return tool_schedule_task(
                store,
                exec_time_utc=raw_exec_time,
                task_text=raw_task_text,
            )
        except ValueError as exc:
            return f"ERROR: {exc}"
    if name == "phone_call_user":
        raw_phone = arguments.get("phone_number")
        raw_reason = arguments.get("reason")
        if not isinstance(raw_phone, str):
            return "ERROR: phone_number must be a string"
        if not isinstance(raw_reason, str):
            return "ERROR: reason must be a string"
        return await tool_phone_call_user(root, raw_phone, raw_reason)
    if name == "companion_runtime_inspect":
        return tool_companion_runtime_inspect(store, dict(arguments or {}))
    if name == "companion_set_experience_profile":
        raw_ctx = arguments.get("context_mode")
        if not isinstance(raw_ctx, str):
            return "ERROR: context_mode must be a string"
        raw_uc = arguments.get("user_confirmed")
        if not isinstance(raw_uc, bool):
            return "ERROR: user_confirmed must be a boolean"
        raw_note = arguments.get("note")
        if raw_note is not None and not isinstance(raw_note, str):
            return "ERROR: note must be a string or omitted"
        return tool_companion_set_experience_profile(
            store,
            raw_ctx,
            user_confirmed=raw_uc,
            note=raw_note,
        )
    if name == "google_web_search":
        raw_q = arguments.get("query")
        if not isinstance(raw_q, str):
            return "ERROR: query must be a string"
        n_raw = arguments.get("num_results")
        n_opt: int | None
        if n_raw is None:
            n_opt = None
        elif isinstance(n_raw, bool):
            return "ERROR: num_results must be a positive integer or omitted"
        elif isinstance(n_raw, int):
            n_opt = n_raw
        elif isinstance(n_raw, float) and n_raw.is_integer():
            n_opt = int(n_raw)
        else:
            return "ERROR: num_results must be a positive integer or omitted"
        return await run_google_web_search(query=raw_q, num_results=n_opt)
    if name == "read_web_page":
        raw_u = arguments.get("url")
        if not isinstance(raw_u, str):
            return "ERROR: url must be a string"
        mb_raw = arguments.get("max_bullets")
        mb_opt: int | None
        if mb_raw is None:
            mb_opt = None
        elif isinstance(mb_raw, bool):
            return "ERROR: max_bullets must be a positive integer or omitted"
        elif isinstance(mb_raw, int):
            mb_opt = mb_raw
        elif isinstance(mb_raw, float) and mb_raw.is_integer():
            mb_opt = int(mb_raw)
        else:
            return "ERROR: max_bullets must be a positive integer or omitted"
        return await run_read_web_page(store, url=raw_u, max_bullets=mb_opt)
    if name == "generate_image":
        gate_err = check_image_tool_allowed(store, tool_name="generate_image")
        if gate_err is not None:
            return gate_err
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str):
            return "ERROR: prompt must be a string"
        if not prompt.strip():
            return "ERROR: prompt must be non-empty"
        image_size = arguments.get("image_size")
        if image_size is not None and not isinstance(image_size, str):
            return "ERROR: image_size must be a string or omitted"
        image_size_s = image_size.strip() if isinstance(image_size, str) else None
        if image_size_s == "":
            image_size_s = None
        n_steps, err = parse_optional_positive_int(
            arguments.get("num_inference_steps"), field_name="num_inference_steps"
        )
        if err:
            return f"ERROR: {err}"
        n_img, err2 = parse_optional_positive_int(
            arguments.get("num_images"), field_name="num_images"
        )
        if err2:
            return f"ERROR: {err2}"
        if n_img is not None and n_img > MAX_NUM_IMAGES_PER_CALL:
            return (
                "ERROR: num_images must be at most "
                f"{MAX_NUM_IMAGES_PER_CALL} per generate_image call"
            )
        from loguru import logger

        t_img = time.perf_counter()
        out = await run_generate_image_z_image_turbo(
            store,
            prompt=prompt,
            image_size=image_size_s,
            num_inference_steps=n_steps,
            num_images=n_img,
            persona_revision_id=current_persona_revision_id(store),
        )
        logger.info(
            "tool generate_image wall_ms={:.0f} scope={} ok={}",
            (time.perf_counter() - t_img) * 1000.0,
            store.scope.registry_key(),
            not out.startswith("ERROR:"),
        )
        if not out.startswith("ERROR:"):
            mark_image_tool_completed(store, tool_name="generate_image")
        return out
    if name == "modify_image":
        gate_err = check_image_tool_allowed(store, tool_name="modify_image")
        if gate_err is not None:
            return gate_err
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str):
            return "ERROR: prompt must be a string"
        if not prompt.strip():
            return "ERROR: prompt must be non-empty"
        raw_path = arguments.get("source_image_relative_path")
        raw_url = arguments.get("source_image_url")
        if raw_path is not None and not isinstance(raw_path, str):
            return "ERROR: source_image_relative_path must be a string or omitted"
        if raw_url is not None and not isinstance(raw_url, str):
            return "ERROR: source_image_url must be a string or omitted"
        path_s = raw_path.strip() if isinstance(raw_path, str) else ""
        url_s = raw_url.strip() if isinstance(raw_url, str) else ""
        if path_s and url_s:
            return "ERROR: use only one of source_image_relative_path or source_image_url, not both"
        src_path: Path | None = None
        if path_s:
            try:
                path_s = normalize_memory_store_relative_path(path_s)
            except ValueError as exc:
                return f"ERROR: {exc}"
            asset = find_latest_asset_by_local_relative_path(store, path_s)
            if asset is not None:
                u = str(asset.get("gcs_http_url") or "").strip()
                if u.startswith("http://") or u.startswith("https://"):
                    url_s = u
                else:
                    return f"ERROR: source image in index has no http(s) URL for {path_s!r}"
            else:
                return f"ERROR: source image not in index: {path_s!r}"
        src_url_out: str | None = url_s if url_s else None
        if src_path is None and src_url_out is None:
            src_url_out = _latest_generated_image_http_url_from_index(store)
            if src_url_out is None:
                return (
                    "ERROR: modify_image requires source_image_relative_path or source_image_url; "
                    "no prior image URL in index"
                )
        image_size = arguments.get("image_size")
        if image_size is not None and not isinstance(image_size, str):
            return "ERROR: image_size must be a string or omitted"
        image_size_s = image_size.strip() if isinstance(image_size, str) else None
        if image_size_s == "":
            image_size_s = None
        n_steps, err = parse_optional_positive_int(
            arguments.get("num_inference_steps"), field_name="num_inference_steps"
        )
        if err:
            return f"ERROR: {err}"
        strength, err_s = parse_optional_strength(arguments.get("strength"))
        if err_s:
            return f"ERROR: {err_s}"
        from loguru import logger

        t_img = time.perf_counter()
        out = await run_modify_image_z_image_turbo(
            store,
            prompt=prompt,
            source_path=src_path,
            source_image_url=src_url_out,
            image_size=image_size_s,
            num_inference_steps=n_steps,
            strength=strength,
            persona_revision_id=current_persona_revision_id(store),
        )
        logger.info(
            "tool modify_image wall_ms={:.0f} scope={} ok={}",
            (time.perf_counter() - t_img) * 1000.0,
            store.scope.registry_key(),
            not out.startswith("ERROR:"),
        )
        if not out.startswith("ERROR:"):
            mark_image_tool_completed(store, tool_name="modify_image")
        return out
    if name == "companion_update_prompt_slice":
        raw_slice = arguments.get("slice")
        raw_content = arguments.get("content")
        if not isinstance(raw_slice, str):
            return "ERROR: slice must be a string"
        if not isinstance(raw_content, str):
            return "ERROR: content must be a string"
        return tool_companion_update_prompt_slice(store, raw_slice, raw_content)
    if name == "companion_bootstrap_user_interactive_complete":
        raw_note = arguments.get("note")
        if raw_note is not None and not isinstance(raw_note, str):
            return "ERROR: note must be a string or omitted"
        return tool_companion_bootstrap_user_interactive_complete(store, raw_note)
    return f"ERROR: unknown tool {name!r}"


async def execute_tool_call(
    store: MemoryStore,
    name: str,
    arguments_json: str,
    *,
    write_allowlist: frozenset[str] | None = None,
    repository_only_store_text: bool = False,
) -> str:
    from loguru import logger

    raw = (arguments_json or "").strip()
    try:
        parsed: dict[str, Any] = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        err = f"ERROR: invalid JSON arguments: {exc}"
        logger.warning("tool {} json_error: {}", name, err)
        return err
    if not isinstance(parsed, dict):
        err = "ERROR: tool arguments must be a JSON object"
        logger.warning("tool {} {}", name, err)
        return err
    try:
        out = await _dispatch(
            store,
            name,
            parsed,
            write_allowlist=write_allowlist,
            repository_only_store_text=repository_only_store_text,
        )
    except (OSError, ValueError) as exc:
        err = f"ERROR: {exc}"
        logger.warning("tool {} dispatch: {}", name, err)
        return err
    if out.startswith("ERROR:"):
        logger.warning("tool {} result: {}", name, out)
    else:
        logger.debug("tool {} ok ({} chars)", name, len(out))
    return out


async def _execute_tool_call_blocking_impl(
    store: MemoryStore,
    name: str,
    arguments_json: str,
    *,
    write_allowlist: frozenset[str] | None = None,
    repository_only_store_text: bool = False,
) -> str:
    """`asyncio.run` 结束前释放 fal 全局 client，避免连续多次 blocking 调用踩 closed loop。"""
    try:
        return await execute_tool_call(
            store,
            name,
            arguments_json,
            write_allowlist=write_allowlist,
            repository_only_store_text=repository_only_store_text,
        )
    finally:
        await reset_fal_async_client_after_short_lived_loop()


def execute_tool_call_blocking(
    store: MemoryStore,
    name: str,
    arguments_json: str,
    *,
    write_allowlist: frozenset[str] | None = None,
    repository_only_store_text: bool = False,
) -> str:
    """Sync entry: safe from async contexts via a fresh event loop in a worker thread."""

    def _run_new_loop() -> str:
        return asyncio.run(
            _execute_tool_call_blocking_impl(
                store,
                name,
                arguments_json,
                write_allowlist=write_allowlist,
                repository_only_store_text=repository_only_store_text,
            )
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_new_loop()

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_run_new_loop).result(timeout=1200)


def tool_executor_for_store(store: MemoryStore) -> Callable[[str, str], str]:
    """返回 (name, arguments_json) -> result_str，供循环内调用。"""

    def run(name: str, arguments_json: str) -> str:
        return execute_tool_call_blocking(
            store, name, arguments_json, write_allowlist=None
        )

    return run
