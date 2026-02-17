# CREATED_BY_AGENT
"""
记忆服务：从 memory 表读取用户记忆，供提示词注入使用。
"""

import asyncio
from datetime import date, datetime, timezone
from typing import Optional, Union

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.agent import get_sync_engine
from app.models.memory import FestivalMemoryMetadata, Memory
from app.services.chat_history_service import (
    add_festival_memory_prompt_message_sync,
    get_chat_history_connection,
    get_festival_memory_prompt_content_for_agent_sync,
)
from app.api.types.llm_config import LLMConfig
from app.services.chat_service import generate_session_id

MEMORY_TYPE_USER_COMMON = "user_common"
MEMORY_TYPE_FESTIVAL = "festival"
FESTIVAL_METADATA_NAME_KEY = "festival_name"
FESTIVAL_METADATA_DATE_KEY = "festival_data"
FESTIVAL_METADATA_LLM_CONFIG_KEY = "llm_config"

# 节日抽取输出 llm_config 时，仅含 model 时的默认参数（与 assemble_args 默认一致）
_FESTIVAL_EXTRACTION_DEFAULT_TEMPERATURE = 0.0
_FESTIVAL_EXTRACTION_DEFAULT_MAX_TOKENS = 2000


def _normalize_memory_metadata(raw_metadata: object) -> dict:
    if isinstance(raw_metadata, dict):
        return raw_metadata
    return {}


def _llm_config_to_metadata_dict(
    llm_config: Union[LLMConfig, dict],
) -> dict:
    """将 LLMConfig 或 dict 转为仅含 model/temperature/max_tokens 的 dict，用于 metadata 存储。"""
    if isinstance(llm_config, LLMConfig):
        raw = llm_config.model_dump()
    else:
        raw = dict(llm_config)
    return {
        "model": (raw.get("model") or "").strip() or None,
        "temperature": raw.get("temperature")
        if raw.get("temperature") is not None
        else _FESTIVAL_EXTRACTION_DEFAULT_TEMPERATURE,
        "max_tokens": raw.get("max_tokens")
        if raw.get("max_tokens") is not None
        else _FESTIVAL_EXTRACTION_DEFAULT_MAX_TOKENS,
    }


def build_festival_memory_metadata(
    festival_name: str,
    festival_date: date,
    llm_config: Optional[Union[LLMConfig, dict]] = None,
) -> dict:
    """构造节日记忆 metadata；使用 FestivalMemoryMetadata 序列化为 DB 格式。"""
    festival_date_str = (
        festival_date.isoformat()
        if isinstance(festival_date, date)
        else str(festival_date)
    )
    llm_config_model = None
    if llm_config is not None:
        cfg_dict = _llm_config_to_metadata_dict(llm_config)
        if cfg_dict.get("model"):
            llm_config_model = LLMConfig.model_validate(cfg_dict)
    meta = FestivalMemoryMetadata(
        festival_name=festival_name,
        festival_date=festival_date_str,
        llm_config=llm_config_model,
    )
    return meta.model_dump_for_db()


def metadata_to_llm_config_output(meta_data: dict) -> Optional[dict]:
    """
    从节日记忆 metadata 得到输出用 llm_config 对象。
    委托 FestivalMemoryMetadata.model_validate_from_db，返回 llm_config 的 dict 或 None。
    """
    meta = FestivalMemoryMetadata.model_validate_from_db(
        meta_data if isinstance(meta_data, dict) else {}
    )
    if meta.llm_config is None:
        return None
    raw = meta.llm_config.model_dump()
    model = (raw.get("model") or "").strip()
    if not model:
        return None
    return {
        "model": model,
        "temperature": raw.get("temperature")
        if raw.get("temperature") is not None
        else _FESTIVAL_EXTRACTION_DEFAULT_TEMPERATURE,
        "max_tokens": raw.get("max_tokens")
        if raw.get("max_tokens") is not None
        else _FESTIVAL_EXTRACTION_DEFAULT_MAX_TOKENS,
    }


def _parse_festival_date(raw_festival_date: object) -> Optional[date]:
    if isinstance(raw_festival_date, date):
        return raw_festival_date
    if raw_festival_date is None:
        return None
    value = str(raw_festival_date).strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def resolve_festival_name_and_date(
    raw_metadata: object,
    legacy_festival_name: object,
    legacy_festival_date: object,
) -> tuple[Optional[str], Optional[date]]:
    """metadata 优先读取节日名称/日期，缺失时回退旧列。使用 FestivalMemoryMetadata.model_validate_from_db。"""
    metadata = _normalize_memory_metadata(raw_metadata)
    meta = FestivalMemoryMetadata.model_validate_from_db(metadata)

    festival_name = meta.festival_name
    if festival_name is None and isinstance(legacy_festival_name, str):
        festival_name = legacy_festival_name.strip() or None

    festival_date = _parse_festival_date(meta.festival_date)
    if festival_date is None:
        festival_date = _parse_festival_date(legacy_festival_date)

    return festival_name, festival_date


def _festival_date_sort_key(festival_date: Optional[date]) -> tuple[int, date]:
    if festival_date is None:
        return (1, date.max)
    return (0, festival_date)


def get_user_memory_for_prompt_sync(
    user_id: str, memory_type: str = MEMORY_TYPE_USER_COMMON
) -> str:
    """
    同步获取用户记忆文本，用于拼接到 ##User information 之后。
    查 memory：user_id、memory_type、agent_id IS NULL，按 created_at DESC 取最新，多条用 \\n\\n 拼接。
    """
    engine = get_sync_engine()
    with engine.connect() as conn:
        stmt = (
            select(Memory.content)
            .where(
                Memory.user_id == user_id,
                Memory.memory_type == memory_type,
                Memory.agent_id.is_(None),
            )
            .order_by(Memory.created_at.desc())
        )
        rows = conn.execute(stmt).fetchall()
    if not rows:
        return ""
    return "\n\n".join(r[0] for r in rows if r[0])


async def get_user_memory_for_prompt_async(
    db: AsyncSession, user_id: str, memory_type: str = MEMORY_TYPE_USER_COMMON
) -> str:
    """
    异步获取用户记忆文本，用于 build_user_info_prompt_block 等。
    """
    stmt = (
        select(Memory.content)
        .where(
            Memory.user_id == user_id,
            Memory.memory_type == memory_type,
            Memory.agent_id.is_(None),
        )
        .order_by(Memory.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.fetchall()
    if not rows:
        return ""
    return "\n\n".join(r[0] for r in rows if r[0])


async def get_festival_memories_for_user_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> list[dict]:
    """
    获取指定用户与指定角色的节日记忆列表，供角色详情 features.festival_memories 使用。
    返回列表元素：{"memory_id": int, "festival_date": "YYYY-MM-DD", "festival_name": str, "memory": str}
    """
    stmt = select(
        Memory.id,
        Memory.meta_data,
        Memory.festival_name,
        Memory.festival_date,
        Memory.content,
    ).where(
        Memory.user_id == user_id,
        Memory.agent_id == agent_id,
        Memory.memory_type == MEMORY_TYPE_FESTIVAL,
    )
    result = await db.execute(stmt)
    rows = result.fetchall()
    items: list[dict] = []
    for row in rows:
        memory_id, metadata, legacy_festival_name, legacy_festival_date, content = row
        festival_name, festival_date = resolve_festival_name_and_date(
            metadata, legacy_festival_name, legacy_festival_date
        )
        if festival_date is None or festival_name is None or content is None:
            continue
        items.append(
            {
                "memory_id": memory_id,
                "_festival_date_obj": festival_date,
                "festival_date": (
                    festival_date.isoformat()
                    if hasattr(festival_date, "isoformat")
                    else str(festival_date)
                ),
                "festival_name": festival_name,
                "memory": content,
            }
        )
    items.sort(
        key=lambda item: (
            _festival_date_sort_key(item["_festival_date_obj"]),
            item["memory_id"],
        )
    )
    return [
        {
            "memory_id": item["memory_id"],
            "festival_date": item["festival_date"],
            "festival_name": item["festival_name"],
            "memory": item["memory"],
        }
        for item in items
    ]


def _get_session_id_for_user_agent_sync(user_id: str, agent_id: str) -> str | None:
    """根据 (user_id, agent_id) 获取该会话的 session_id，无会话则返回 None。"""
    conn = get_chat_history_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM chats WHERE user_id = %s AND agent_id = %s AND is_active = true LIMIT 1",
            (user_id, agent_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return generate_session_id(row[0])


async def get_pairs_with_undelivered_festival_memories(
    db: AsyncSession, limit: int = 100
) -> list[dict]:
    """
    查询存在未投递且未发过 system notification 的节日记忆的 (user_id, agent_id) 对。
    条件：memory_type == festival、delivery_at IS NULL、system_notification_sent_at IS NULL。
    按 (user_id, agent_id) 去重，取前 limit 对；每对带一条代表 festival_memory_id（按 festival_date 升序取第一条）。
    返回列表元素：{"user_id": str, "agent_id": str, "festival_memory_id": int}。
    """
    stmt = select(
        Memory.user_id,
        Memory.agent_id,
        Memory.id,
        Memory.meta_data,
        Memory.festival_name,
        Memory.festival_date,
    ).where(
        Memory.memory_type == MEMORY_TYPE_FESTIVAL,
        Memory.delivery_at.is_(None),
        Memory.system_notification_sent_at.is_(None),
    )
    result = await db.execute(stmt)
    rows = result.fetchall()
    first_by_pair: dict[tuple[str, str], dict] = {}
    for row in rows:
        user_id, agent_id, memory_id, metadata, legacy_name, legacy_date = row
        if not user_id or not agent_id or memory_id is None:
            continue
        _, resolved_festival_date = resolve_festival_name_and_date(
            metadata, legacy_name, legacy_date
        )
        key = (user_id, agent_id)
        sort_key = (_festival_date_sort_key(resolved_festival_date), memory_id)
        selected = first_by_pair.get(key)
        if selected is None or sort_key < selected["sort_key"]:
            first_by_pair[key] = {
                "user_id": user_id,
                "agent_id": agent_id,
                "festival_memory_id": memory_id,
                "sort_key": sort_key,
            }

    selected_pairs = sorted(
        first_by_pair.values(),
        key=lambda item: (item["user_id"], item["agent_id"]),
    )[:limit]
    return [
        {
            "user_id": item["user_id"],
            "agent_id": item["agent_id"],
            "festival_memory_id": item["festival_memory_id"],
        }
        for item in selected_pairs
    ]


async def mark_system_notification_sent_for_user_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> None:
    """
    对该 (user_id, agent_id) 下所有 memory_type == festival 且 delivery_at IS NULL 的
    memory 行更新 system_notification_sent_at = now()。
    """
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Memory)
        .where(
            Memory.user_id == user_id,
            Memory.agent_id == agent_id,
            Memory.memory_type == MEMORY_TYPE_FESTIVAL,
            Memory.delivery_at.is_(None),
        )
        .values(system_notification_sent_at=now)
    )
    await db.commit()


async def get_undelivered_festival_memories(
    db: AsyncSession, user_id: str, agent_id: str
) -> list[dict]:
    """
    查询 (user_id, agent_id) 下尚未投递的节日记忆（delivery_at IS NULL）。
    返回列表元素：{"id": int, "festival_name": str, "festival_date": date}
    """
    stmt = select(
        Memory.id,
        Memory.meta_data,
        Memory.festival_name,
        Memory.festival_date,
    ).where(
        Memory.user_id == user_id,
        Memory.agent_id == agent_id,
        Memory.memory_type == MEMORY_TYPE_FESTIVAL,
        Memory.delivery_at.is_(None),
    )
    result = await db.execute(stmt)
    rows = result.fetchall()
    items: list[dict] = []
    for row in rows:
        memory_id, metadata, legacy_festival_name, legacy_festival_date = row
        festival_name, festival_date = resolve_festival_name_and_date(
            metadata, legacy_festival_name, legacy_festival_date
        )
        if festival_name is None or festival_date is None:
            continue
        items.append(
            {
                "id": memory_id,
                "festival_name": festival_name,
                "festival_date": festival_date,
            }
        )
    items.sort(
        key=lambda item: (_festival_date_sort_key(item["festival_date"]), item["id"])
    )
    return items


async def deliver_festival_memories_for_user_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> list[dict]:
    """
    为 (user_id, agent_id) 执行所有未投递节日记忆的投递：写入 chat_history 并更新 memory.delivery_at。
    返回本次投递的提醒列表，每项含 memory_id, content, festival_name, festival_date，
    供发起聊天接口追加到 choices 使用。

    TODO: 若 Completions 与 GET messages 对同一 (user_id, agent_id) 并发调用本函数，
    理论上可能发生同一 memory 被投递两次（重复 chat_history 行）的 race；
    因操作仅限定于同一用户与角色对，发生概率较低。若需严格避免，可对 memory 行加
    SELECT FOR UPDATE 或对投递结果加唯一约束并做幂等处理。
    """
    undelivered = await get_undelivered_festival_memories(db, user_id, agent_id)
    if not undelivered:
        return []

    session_id = await asyncio.to_thread(
        _get_session_id_for_user_agent_sync, user_id, agent_id
    )
    if not session_id:
        return []

    now = datetime.now(timezone.utc)
    prompt_content = await asyncio.to_thread(
        get_festival_memory_prompt_content_for_agent_sync, agent_id
    )
    delivered = []
    for item in undelivered:
        mid = item["id"]
        festival_name = item["festival_name"]
        festival_date = item["festival_date"]
        festival_date_val: date = (
            festival_date
            if isinstance(festival_date, date)
            else date.fromisoformat(str(festival_date))
        )
        msg_id = await asyncio.to_thread(
            add_festival_memory_prompt_message_sync,
            session_id,
            agent_id,
            mid,
            festival_name,
            festival_date_val,
        )
        if msg_id is None:
            continue
        await db.execute(
            update(Memory)
            .where(Memory.id == mid, Memory.delivery_at.is_(None))
            .values(delivery_at=now)
        )
        delivered.append(
            {
                "memory_id": mid,
                "message_id": msg_id,
                "content": prompt_content,
                "festival_name": festival_name,
                "festival_date": (
                    festival_date_val.isoformat()
                    if hasattr(festival_date_val, "isoformat")
                    else str(festival_date_val)
                ),
            }
        )
    await db.commit()
    return delivered
