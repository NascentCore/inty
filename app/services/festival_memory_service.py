# CREATED_BY_AGENT
"""
节日记忆抽取服务：筛选 (user, agent) 轮数≥阈值、按会话拉取对话、LLM 抽取节日回忆并写入 memory。
"""

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo

from loguru import logger

from app.api.types.llm_config import LLMConfig
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

import psycopg

from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import Agent
from app.models.memory import Memory
from app.models.user import User
from app.services.chat_history_service import get_chat_history_connection
from app.services.chat_service import generate_session_id
from app.services.memory_service import MEMORY_TYPE_FESTIVAL
from app.utils.openai_client import chat_completion_for_extraction
from app.utils.openrouter_memory import (
    DEFAULT_MEMORY_EXTRACTION_MODEL as DEFAULT_FESTIVAL_EXTRACTION_MODEL,
)

_MAX_IN_PARAMS = 5000
DEFAULT_MIN_ROUNDS_IN_WINDOW = 15


def _window_for_festival_date(
    festival_date: date, timezone_str: str = "UTC"
) -> Tuple[datetime, datetime]:
    """该时区下节日自然日 00:00 至次日 04:00（共 28 小时）换算为 UTC。返回 (window_start, window_end) 左闭右开。"""
    tz = ZoneInfo(timezone_str)
    local_start = datetime(
        festival_date.year,
        festival_date.month,
        festival_date.day,
        0,
        0,
        0,
        tzinfo=tz,
    )
    local_end = local_start + timedelta(hours=28)
    window_start = local_start.astimezone(timezone.utc)
    window_end = local_end.astimezone(timezone.utc)
    return (window_start, window_end)


def get_pairs_with_min_rounds_in_window_sync(
    festival_date: date,
    db_url: str,
    min_rounds: int = DEFAULT_MIN_ROUNDS_IN_WINDOW,
    timezone_str: str = "UTC",
) -> List[Tuple[str, str]]:
    """
    同步筛选 (user_id, agent_id)：仅包含在「该时区下节日自然日 00:00 至次日 04:00」28 小时
    （换算为 UTC）内，该会话用户消息数（排除开场白）>= min_rounds 的组合。
    db_url：用于 psycopg 连接的数据库 URL（主库或只读副本）。
    """
    window_start, window_end = _window_for_festival_date(festival_date, timezone_str)
    logger.debug(f"connecting to database: {db_url}")
    conn = psycopg.connect(db_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, agent_id, id
                FROM chats
                WHERE is_active = true
                """)
            rows = cur.fetchall()
        if not rows:
            return []
        chat_to_ua = {(r[2]): (r[0], r[1]) for r in rows}
        session_ids = [generate_session_id(r[2]) for r in rows]
        session_to_count = {}
        for i in range(0, len(session_ids), _MAX_IN_PARAMS):
            chunk = session_ids[i : i + _MAX_IN_PARAMS]
            ph = ",".join("%s" for _ in chunk)
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT session_id::text,
                        COUNT(*) FILTER (
                            WHERE message->>'type' IN ('human', 'HumanMessage')
                            AND (meta_data IS NULL OR meta_data->>'isOpening' IS NULL OR meta_data->>'isOpening' != 'true')
                        ) AS user_message_count
                    FROM chat_history
                    WHERE session_id::text IN ({ph}) AND deleted_at IS NULL
                        AND created_at >= %s AND created_at < %s
                    GROUP BY session_id
                    """,
                    chunk + [window_start, window_end],
                )
                for row in cur.fetchall():
                    session_to_count[row[0]] = row[1] or 0
        out = []
        for chat_id, (uid, aid) in chat_to_ua.items():
            sid = generate_session_id(chat_id)
            if session_to_count.get(sid, 0) >= min_rounds:
                out.append((uid, aid))
        return out
    finally:
        conn.close()


def get_messages_for_user_agent_sync(
    user_id: str, agent_id: str, connection: Optional[Any] = None
) -> List[Tuple[str, str]]:
    """
    拉取该用户与该角色的单会话消息 (role, content)，按 created_at 升序。
    connection 可选；不传则使用 get_chat_history_connection()（主库）。
    """
    conn = connection if connection is not None else get_chat_history_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM chats WHERE user_id = %s AND agent_id = %s AND is_active = true LIMIT 1",
            (user_id, agent_id),
        )
        row = cur.fetchone()
    if not row:
        return []
    chat_id = row[0]
    session_id = generate_session_id(chat_id)
    ph = "%s"
    query = f"""
        SELECT message
        FROM chat_history
        WHERE session_id::text = {ph} AND deleted_at IS NULL
        ORDER BY created_at ASC
    """
    out: List[Tuple[str, str]] = []
    with conn.cursor() as cur:
        cur.execute(query, (session_id,))
        for r in cur.fetchall():
            raw = r[0]
            try:
                data = (
                    json.loads(raw)
                    if isinstance(raw, str)
                    else (raw if isinstance(raw, dict) else json.loads(str(raw)))
                )
            except Exception:
                continue
            msg_type = data.get("type", "human")
            content = ""
            if (
                "data" in data
                and isinstance(data.get("data"), dict)
                and "content" in data["data"]
            ):
                content = data["data"].get("content") or ""
            elif "content" in data:
                content = data["content"] or ""
            role = "user" if msg_type in ("human", "HumanMessage") else "assistant"
            out.append((role, str(content)))
    return out


def _format_chat_for_prompt(messages: List[Tuple[str, str]]) -> str:
    lines = []
    for role, content in messages:
        label = "User" if role == "user" else "AI"
        lines.append(f"**{label}**: {content}")
    return "\n".join(lines)


def _normalize_llm_config(
    llm_config: Optional[Union[LLMConfig, dict]],
) -> Optional[LLMConfig]:
    """将 dict 转为 LLMConfig，None 或已是 LLMConfig 则原样返回。"""
    if llm_config is None:
        return None
    if isinstance(llm_config, dict):
        return LLMConfig.model_validate(llm_config)
    return llm_config


def assemble_args(
    messages: List[Tuple[str, str]],
    festival_name: str,
    festival_date: date,
    prompt_template: str,
    llm_config: Optional[Union[LLMConfig, dict]] = None,
) -> Tuple[str, LLMConfig]:
    """
    组装 chat_completion_for_extraction 的调用参数（full_prompt, LLMConfig）。
    若 llm_config 存在且含 model，则使用该 LLMConfig；否则使用全局默认（节日抽取：max_tokens=2000, temperature=0.0）。
    供 extract_festival_and_save 与 extract_festival_to_dict 复用。
    """
    llm_config = _normalize_llm_config(llm_config)
    chat_text = _format_chat_for_prompt(messages)
    date_str = (
        festival_date.isoformat()
        if isinstance(festival_date, date)
        else str(festival_date)
    )
    full_prompt = f"""{prompt_template}

---
Festival name: {festival_name}
Festival date: {date_str}

---
# Conversation between the user and the character

{chat_text}

---
Based on the conversation above, extract memories or preferences related to "{festival_name}" for this user and character. Output a concise summary in one short paragraph. Output the summary in English only. Do not include any other format or text."""
    if llm_config and (llm_config.model or "").strip():
        return (full_prompt, llm_config)
    cfg = getattr(global_config_loaded_from_config_yaml, "memory_extraction", None)
    model_name = (
        cfg.model.strip() if cfg and cfg.model else None
    ) or DEFAULT_FESTIVAL_EXTRACTION_MODEL
    default_llm_config = LLMConfig(
        model=model_name,
        max_tokens=2000,
        temperature=0.0,
    )
    return (full_prompt, default_llm_config)


async def summarize_memory_from_messages_between_user_and_agent(
    user_id: str,
    agent_id: str,
    festival_name: str,
    festival_date: date,
    prompt_template: str,
    messages_override: Optional[List[Tuple[str, str]]] = None,
    llm_config: Optional[Union[LLMConfig, dict]] = None,
) -> Optional[Memory]:
    """
    根据 (user_id, agent_id) 拉取会话消息、调用 LLM 抽取节日回忆摘要，并构造（未持久化的）Memory 行。
    失败（无消息、无摘要或过短、LLM 异常）时返回 None。
    若传入 messages_override，则使用该消息列表，不再从 DB 拉取；用于脚本 --messages-input 与直接抽取结果一致。
    """
    if messages_override is not None:
        messages = messages_override
    else:
        messages = await asyncio.to_thread(
            get_messages_for_user_agent_sync, user_id, agent_id
        )
    if not messages:
        logger.debug(f"节日记忆跳过：user_id={user_id} agent_id={agent_id} 无消息")
        return None
    logger.debug(f"节日记忆抽取：user_id={user_id} agent_id={agent_id} 消息数={len(messages)}")
    for msg in messages:
        logger.debug(f"message: {msg}")
    full_prompt, ext_llm_config = assemble_args(
        messages, festival_name, festival_date, prompt_template, llm_config
    )
    try:
        summary, _, _ = await chat_completion_for_extraction(
            full_prompt, llm_config=ext_llm_config
        )
        if not summary or len(summary.strip()) < 10:
            return None
        summary = summary.strip()
    except Exception as e:
        logger.warning(
            f"节日记忆 LLM 调用失败 user_id={user_id} agent_id={agent_id}: {e}"
        )
        return None
    extracted_at = datetime.now(timezone.utc)
    return Memory(
        user_id=user_id,
        memory_type=MEMORY_TYPE_FESTIVAL,
        agent_id=agent_id,
        content=summary,
        extracted_at=extracted_at,
        festival_name=festival_name,
        festival_date=festival_date,
    )


async def extract_festival_and_save(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    festival_name: str,
    festival_date: date,
    prompt_template: str,
    llm_config: Optional[Union[LLMConfig, dict]] = None,
) -> bool:
    """
    对 (user_id, agent_id) 拉取该会话消息、按节日提示词调用 LLM 抽取回忆摘要，
    删除旧节日记忆后写入一条 memory（memory_type=festival）。
    返回是否成功。
    """
    memory_row = await summarize_memory_from_messages_between_user_and_agent(
        user_id,
        agent_id,
        festival_name,
        festival_date,
        prompt_template,
        llm_config=llm_config,
    )
    if memory_row is None:
        return False
    await db.execute(
        delete(Memory).where(
            Memory.user_id == user_id,
            Memory.agent_id == agent_id,
            Memory.memory_type == MEMORY_TYPE_FESTIVAL,
            Memory.festival_name == festival_name,
            Memory.festival_date == festival_date,
        )
    )
    db.add(memory_row)
    await db.commit()
    logger.debug(
        f"节日记忆写入完成 user_id={user_id} agent_id={agent_id} festival={festival_name}"
    )
    # 提示消息改为按需投递：在用户发起聊天或拉取消息列表时写入 chat_history 并更新 memory.delivery_at
    return True


async def _get_user_agent_names(
    db: AsyncSession, user_id: str, agent_id: str
) -> Tuple[Optional[str], Optional[str]]:
    """从主库查 user nickname 与 agent name，用于 JSON 导出等。"""
    user_name, agent_name = None, None
    try:
        r = await db.execute(
            select(User.nickname).where(User.id == user_id, User.deleted_at.is_(None))
        )
        row = r.scalar_one_or_none()
        if row is not None:
            user_name = (row or "").strip() or None
    except Exception as e:
        logger.debug(f"resolve user name for {user_id}: {e}")
    try:
        r = await db.execute(
            select(Agent.name).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
        )
        row = r.scalar_one_or_none()
        if row is not None:
            agent_name = (row or "").strip() or None
    except Exception as e:
        logger.debug(f"resolve agent name for {agent_id}: {e}")
    return user_name, agent_name


async def extract_festival_to_dict(
    user_id: str,
    agent_id: str,
    festival_name: str,
    festival_date: date,
    prompt_template: str,
    db: Optional[AsyncSession] = None,
    messages_override: Optional[List[Tuple[str, str]]] = None,
) -> Optional[dict]:
    """
    与 extract_festival_and_save 相同的拉消息、拼 prompt、调 LLM 流程，
    但返回可 JSON 序列化的 dict，不写库。失败返回 None。
    若传入 db，会在返回的 dict 中附带 user_name、agent_name（从主库查 nickname/name）。
    若传入 messages_override，则使用该消息列表，不再从 DB 拉取；用于脚本 --messages-input。
    这个只用于离线脚本，在线服务不使用本函数。
    """
    memory_row = await summarize_memory_from_messages_between_user_and_agent(
        user_id,
        agent_id,
        festival_name,
        festival_date,
        prompt_template,
        messages_override=messages_override,
        llm_config=None,
    )
    if memory_row is None:
        return None
    fd = memory_row.festival_date
    out = {
        "user_id": memory_row.user_id,
        "agent_id": memory_row.agent_id,
        "memory_type": memory_row.memory_type,
        "content": memory_row.content,
        "extracted_at": memory_row.extracted_at.isoformat(),
        "festival_name": memory_row.festival_name,
        "festival_date": fd.isoformat() if isinstance(fd, date) else str(fd),
    }
    if db is not None:
        user_name, agent_name = await _get_user_agent_names(db, user_id, agent_id)
        out["user_name"] = user_name or user_id
        out["agent_name"] = agent_name or agent_id
    return out


async def query_festival_memories_from_db(
    db: AsyncSession, festival_name: str, festival_date: date
) -> List[dict]:
    """
    从主库 memory 表按节日名称与日期查询已有节日记忆，返回与 extract_festival_to_dict
    相同结构的 dict 列表（含 user_name、agent_name）。不写库、不调 LLM。
    """
    r = await db.execute(
        select(Memory).where(
            Memory.memory_type == MEMORY_TYPE_FESTIVAL,
            Memory.festival_name == festival_name,
            Memory.festival_date == festival_date,
        )
    )
    rows = r.scalars().all()
    out: List[dict] = []
    for row in rows:
        fd = row.festival_date
        d = {
            "user_id": row.user_id,
            "agent_id": row.agent_id,
            "memory_type": row.memory_type,
            "content": row.content,
            "extracted_at": row.extracted_at.isoformat(),
            "festival_name": row.festival_name,
            "festival_date": fd.isoformat() if isinstance(fd, date) else str(fd),
        }
        user_name, agent_name = await _get_user_agent_names(db, row.user_id, row.agent_id)
        d["user_name"] = user_name or row.user_id
        d["agent_name"] = agent_name or row.agent_id
        out.append(d)
    return out
