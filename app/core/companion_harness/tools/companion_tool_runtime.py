"""Companion tool runtime: schemas, dispatch, and ``execute_tool_call`` for the REPL/Companion Harness.

Persisted companion documents and transcript go through MemoryStore; tool paths align with
``memory_store_document_mapping``.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from app.core.companion_harness.tools.registry import ToolRegistry
from app.core.companion_harness.tools.dispatchers.media import (
    parse_optional_positive_int,
    parse_optional_strength,
)
from app.core.companion_harness.tools.dispatchers.memory_store import (
    dispatch_memory_store_tool,
)

from app.core.companion_harness.companion.bootstrap import (
    tool_companion_bootstrap_user_interactive_complete,
    tool_companion_set_experience_profile,
    tool_companion_update_prompt_slice,
)
from app.core.companion_harness.companion.message_format import (
    openai_assistant_message_dict,
)
from app.core.companion_harness.companion.models import (
    ChatMessage,
    load_context_meta,
)
from app.core.companion_harness.companion.schedule_queue import (
    add_schedule_task,
)
from app.core.companion_harness.memory.memory_store import (
    MemoryStore,
    normalize_memory_store_relative_path,
)
from app.core.companion_harness.memory.memory_store_document_mapping import (
    parse_memory_store_relative_path,
)
from app.core.companion_harness.companion.llm_runtime_events import (
    companion_llm_runtime_event_bind_ctx,
)
from living_sphere.models import (
    LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME,
    LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH,
    LivingSphereUpdate,
)
from techno_core.models import (
    Sphere,
    TechnoCoreEvent,
    TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
    TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
    Visibility,
)

from .fal_z_image_tool import (
    MAX_NUM_IMAGES_PER_CALL,
    reset_fal_async_client_after_short_lived_loop,
    run_generate_image_z_image_turbo,
    run_modify_image_z_image_turbo,
)
from .google_web_search import run_google_web_search
from .image_gate import (
    current_persona_revision_id,
    find_latest_asset_by_local_relative_path,
    list_image_asset_records,
)
from .companion_tool_definitions import (
    COMPANION_LLM_TOOLS,
    COMPANION_LLM_TOOLS_BY_NAME,
    BOOTSTRAP_TRACK_TOOL_NAMES,
    CompanionToolName,
    INNER_TICK_TOOL_NAMES,
    MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    REPL_DESCRIPTION_OVERRIDES,
    TOOL_NAMES_APPENDED,
    TOOL_NAMES_BOOTSTRAP_APPENDED,
    TOOL_NAMES_NON_BOOTSTRAP_TAIL,
    TOOL_NAMES_SHARED_HEAD,
    TOOL_TAG_GENERATION,
    _EMPTY_DESCRIPTION_OVERRIDES,
    openai_tools_for_names,
)
from .openai_tools_prepare import prepare_openai_tools_for_chat_completions
from .read_web_page import run_read_web_page
from app.core.config import global_config_loaded_from_config_yaml
# TODO(commercialization-cleanup): Remove ``tool_phone_call_user`` and ``subscription_service`` /
# ``phone_call_service`` imports from harness — tool is not registered in ``TOOL_NAMES_*``;
# outbound call billing belongs in app orchestration (``phone_call.py``), not ``companion_harness``.
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.global_services import subscription_service
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
# ``TOOL_TAG_GENERATION`` / memory-store caps / allowlist: ``companion_tool_definitions``.


# TODO(inner-tick-autonomy): ai_private.jsonl append-only tool for autonomy inner-tick; drop
# UPDATE_USER_MD / memory_store_* / techno_core from INNER_TICK_TOOL_NAMES (记忆一致性 → dreaming).


def _latest_generated_image_http_url_from_index(
    store: MemoryStore,
) -> str | None:
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


def _list_dir_extra_names_from_store(
    store: MemoryStore, rel_dir: str
) -> set[str]:
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
    tuple(tool.name.value for tool in COMPANION_LLM_TOOLS)
)


def tool_has_tag(tool_name: str, tag: str) -> bool:
    """Return whether a tool declares a given behavior tag."""
    try:
        name = CompanionToolName(tool_name)
    except ValueError:
        return False
    tool = COMPANION_LLM_TOOLS_BY_NAME.get(name)
    if tool is None:
        return False
    return tag in tool.tags


def tool_requires_client_delivery_on_success(tool_name: str) -> bool:
    """True when the tool produces user-visible artifacts that must reach the client if successful."""
    return tool_has_tag(tool_name, TOOL_TAG_GENERATION)


def round_includes_generation_tool(tool_names: Iterable[str]) -> bool:
    return any(tool_requires_client_delivery_on_success(n) for n in tool_names)


def append_user_profile_facts_to_user_md(
    text: str, new_bullets: list[str]
) -> str:
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


def tool_update_user_md(
    store: MemoryStore, items: list[dict[str, Any]]
) -> str:
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
        body[:max_chars]
        + "\n…[truncated: prefix only; file is longer than max_chars]"
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
    if rel in ("transcript.jsonl", "transcript_inner_tick.jsonl"):
        v_err = _transcript_jsonl_validate_for_tool_write(content)
        if v_err is not None:
            return v_err
    st.write_document(rel, content)
    return f"OK wrote {len(content)} chars to {relative_path}"


def tool_memory_store_mkdir(store: MemoryStore, relative_path: str) -> str:
    _ = store, relative_path
    return "OK mkdir (logical prefix only; companion MemoryStore has no host filesystem dirs)"


def tool_techno_core_record_event(
    store: MemoryStore, arguments: dict[str, Any]
) -> str:
    """Append one ``TechnoCoreEvent`` line to ``techno_core_events.jsonl`` (LivingSphere / TechnoCore autonomy)."""
    raw_sphere = arguments.get("sphere")
    raw_summary = arguments.get("summary")
    if not isinstance(raw_sphere, str):
        return "ERROR: sphere must be a string"
    if not isinstance(raw_summary, str):
        return "ERROR: summary must be a string"
    try:
        sphere = Sphere(raw_sphere.strip())
    except ValueError:
        return f"ERROR: invalid sphere {raw_sphere!r}"

    raw_vis = arguments.get("visibility")
    visibility: Visibility = Visibility.PRIVATE
    if raw_vis is not None:
        if not isinstance(raw_vis, str):
            return "ERROR: visibility must be a string or omitted"
        try:
            visibility = Visibility(raw_vis.strip())
        except ValueError:
            return f"ERROR: invalid visibility {raw_vis!r}"

    uid = store.scope.user_id.strip()
    cid = store.scope.companion_id.strip()
    if not cid:
        return f"ERROR: missing companion scope for {TECHNO_CORE_RECORD_EVENT_TOOL_NAME}"

    ev_kwargs: dict[str, Any] = {
        "sphere": sphere,
        "actor_companion_id": cid,
        "summary": raw_summary,
        "visibility": visibility,
        "source": "inner_tick",
        "related_user_id": uid or None,
    }

    raw_ev = arguments.get("emotional_valence")
    if raw_ev is not None:
        if not isinstance(raw_ev, str):
            return "ERROR: emotional_valence must be a string or omitted"
        ev_kwargs["emotional_valence"] = raw_ev

    raw_sal = arguments.get("salience")
    if raw_sal is not None:
        if type(raw_sal) is not int or isinstance(raw_sal, bool):
            return "ERROR: salience must be an integer 1..10 or omitted"
        ev_kwargs["salience"] = raw_sal

    raw_ls = arguments.get("related_living_sphere")
    if raw_ls is not None:
        if not isinstance(raw_ls, str):
            return "ERROR: related_living_sphere must be a string or omitted"
        ev_kwargs["related_living_sphere"] = raw_ls

    try:
        event = TechnoCoreEvent.model_validate(ev_kwargs)
    except ValidationError as exc:
        return f"ERROR: {exc}"

    store.append_jsonl_record(
        TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
        event.model_dump(mode="json"),
    )
    return f"OK recorded techno_core event_id={event.event_id}"


def tool_living_sphere_record_update(
    store: MemoryStore, arguments: dict[str, Any]
) -> str:
    """Append one LivingSphere change intent to ``living_sphere_updates.jsonl``."""
    raw_change = arguments.get("change_request")
    if not isinstance(raw_change, str):
        return "ERROR: change_request must be a string"
    cid = store.scope.companion_id.strip()
    if not cid:
        return f"ERROR: missing companion scope for {LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME}"
    ev_kwargs: dict[str, Any] = {
        "change_request": raw_change,
        "source": "chat_tool",
    }
    bind = companion_llm_runtime_event_bind_ctx.get()
    if bind is not None:
        trace = bind.trace_id.strip()
        if trace:
            ev_kwargs["trace_id"] = trace
        um = bind.user_msg_uuid.strip()
        if um:
            ev_kwargs["user_msg_uuid"] = um
    try:
        update = LivingSphereUpdate.model_validate(ev_kwargs)
    except ValidationError as exc:
        return f"ERROR: {exc}"
    store.append_jsonl_record(
        LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH,
        update.model_dump(mode="json"),
    )
    return f"OK recorded update_id={update.update_id}"


def tool_schedule_task(
    store: MemoryStore, exec_time_utc: str, task_text: str
) -> str:
    task_id = add_schedule_task(
        store,
        exec_time_utc=exec_time_utc,
        task_text=task_text,
    )
    return (
        "OK scheduled task "
        f"id={task_id} exec_time_utc={exec_time_utc} text={task_text.strip()}"
    )


async def tool_phone_call_user(
    store: MemoryStore, phone_number: str, reason: str
) -> str:
    # TODO(commercialization-cleanup): Delete this handler and ``execute_tool_call`` branch;
    # see module-level TODO — prototype harness must not depend on ``SubscriptionService``.
    context = load_context_meta(store=store)
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


def build_openai_bootstrap_track_tools() -> list[dict[str, Any]]:
    """USER_CHAT_BOOTSTRAP track: prompt-slice writes + bootstrap complete only."""
    return prepare_openai_tools_for_chat_completions(
        openai_tools_for_names(
            BOOTSTRAP_TRACK_TOOL_NAMES,
            description_overrides=_EMPTY_DESCRIPTION_OVERRIDES,
        )
    )


def build_openai_repl_tools(
    *, interactive_bootstrap_active: bool = False
) -> list[dict[str, Any]]:
    """
    伴侣对话轮：用户档案追加、LivingSphere/TechnoCore 事件落库、工作区文档读写（写入仅限 MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST）。
    """
    if interactive_bootstrap_active:
        names = TOOL_NAMES_SHARED_HEAD
    else:
        names = TOOL_NAMES_SHARED_HEAD + TOOL_NAMES_NON_BOOTSTRAP_TAIL
    out = openai_tools_for_names(
        names,
        description_overrides=REPL_DESCRIPTION_OVERRIDES,
    )
    appended_names = (
        TOOL_NAMES_BOOTSTRAP_APPENDED
        if interactive_bootstrap_active
        else TOOL_NAMES_APPENDED
    )
    out.extend(
        openai_tools_for_names(
            appended_names,
            description_overrides=_EMPTY_DESCRIPTION_OVERRIDES,
        )
    )
    if interactive_bootstrap_active:
        out.extend(
            openai_tools_for_names(
                BOOTSTRAP_TRACK_TOOL_NAMES,
                description_overrides=_EMPTY_DESCRIPTION_OVERRIDES,
            )
        )
    return prepare_openai_tools_for_chat_completions(out)


def build_openai_repl_tools_inner_tick() -> list[dict[str, Any]]:
    """
    内在节拍：USER 档案、LivingSphere/TechnoCore 事件日志、工作区读写；不含定时、联网、生图/改图。

    TODO(inner-tick-autonomy): Autonomy inner-tick — ai_private.jsonl append only; see INNER_TICK_TOOL_NAMES.
    """
    return prepare_openai_tools_for_chat_completions(
        openai_tools_for_names(
            INNER_TICK_TOOL_NAMES,
            description_overrides=REPL_DESCRIPTION_OVERRIDES,
        )
    )


def _memory_store_write_document_allowlist_reject(
    store: MemoryStore, relative_path: str, write_allowlist: frozenset[str]
) -> str | None:
    """若不允许写入则返回错误信息字符串，否则 None。"""
    _ = store
    try:
        rel_posix = _tool_rel_posix_from_arg(relative_path)
    except ValueError as exc:
        return f"ERROR: {exc}"
    if rel_posix not in write_allowlist:
        return (
            "ERROR: memory_store_write_document only allows: "
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
        tool_update_user_md=tool_update_user_md,
        parse_optional_max_chars=_parse_optional_max_chars,
        write_document_allowlist_reject=_memory_store_write_document_allowlist_reject,
    )
    if memory_store_dispatch_result is not None:
        return memory_store_dispatch_result
    if name == TECHNO_CORE_RECORD_EVENT_TOOL_NAME:
        return tool_techno_core_record_event(store, arguments)
    if name == LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME:
        return tool_living_sphere_record_update(store, arguments)
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
        return await tool_phone_call_user(store, raw_phone, raw_reason)
    if name == "companion_set_experience_profile":
        raw_ctx = arguments.get("context_mode")
        if not isinstance(raw_ctx, str):
            return "ERROR: context_mode must be a string"
        raw_note = arguments.get("note")
        if not isinstance(raw_note, str):
            return "ERROR: note must be a string"
        return tool_companion_set_experience_profile(
            store,
            raw_ctx,
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
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str):
            return "ERROR: prompt must be a string"
        if not prompt.strip():
            return "ERROR: prompt must be non-empty"
        image_size = arguments.get("image_size")
        if image_size is not None and not isinstance(image_size, str):
            return "ERROR: image_size must be a string or omitted"
        image_size_s = (
            image_size.strip() if isinstance(image_size, str) else None
        )
        if image_size_s == "":
            image_size_s = None
        n_steps, err = parse_optional_positive_int(
            arguments.get("num_inference_steps"),
            field_name="num_inference_steps",
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
        return out
    if name == "modify_image":
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str):
            return "ERROR: prompt must be a string"
        if not prompt.strip():
            return "ERROR: prompt must be non-empty"
        raw_path = arguments.get("source_image_relative_path")
        raw_url = arguments.get("source_image_url")
        if raw_path is not None and not isinstance(raw_path, str):
            return (
                "ERROR: source_image_relative_path must be a string or omitted"
            )
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
        image_size_s = (
            image_size.strip() if isinstance(image_size, str) else None
        )
        if image_size_s == "":
            image_size_s = None
        n_steps, err = parse_optional_positive_int(
            arguments.get("num_inference_steps"),
            field_name="num_inference_steps",
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
        return tool_companion_bootstrap_user_interactive_complete(
            store, raw_note
        )
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
