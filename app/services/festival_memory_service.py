# CREATED_BY_AGENT
"""
节日记忆抽取服务：筛选 (user, agent) 轮数≥阈值、按会话拉取对话、LLM 抽取节日回忆并写入 memory。
"""

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

import psycopg

from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory
from app.services import chat_history_service
from app.services.chat_history_service import get_chat_history_connection
from app.services.chat_service import generate_session_id
from app.services.memory_service import MEMORY_TYPE_FESTIVAL
from app.utils.openrouter_memory import (
    DEFAULT_MEMORY_EXTRACTION_MODEL as DEFAULT_FESTIVAL_EXTRACTION_MODEL,
    call_openrouter_for_extraction,
)

_MAX_IN_PARAMS = 5000
FESTIVAL_MEMORY_MIN_MESSAGES_IN_WINDOW = 30


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
    min_rounds: int = FESTIVAL_MEMORY_MIN_MESSAGES_IN_WINDOW,
    timezone_str: str = "UTC",
) -> List[Tuple[str, str]]:
    """
    同步筛选 (user_id, agent_id)：仅包含在「该时区下节日自然日 00:00 至次日 04:00」28 小时
    （换算为 UTC）内，该会话用户消息数（排除开场白）>= min_rounds 的组合。
    """
    window_start, window_end = _window_for_festival_date(festival_date, timezone_str)
    db_url = global_config_loaded_from_config_yaml.database.url
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
    user_id: str, agent_id: str
) -> List[Tuple[str, str]]:
    """
    拉取该用户与该角色的单会话消息 (role, content)，按 created_at 升序。
    """
    conn = get_chat_history_connection()
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


def get_session_id_for_user_agent_sync(user_id: str, agent_id: str) -> Optional[str]:
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


def _format_chat_for_prompt(messages: List[Tuple[str, str]]) -> str:
    lines = []
    for role, content in messages:
        label = "用户" if role == "user" else "AI"
        lines.append(f"**{label}**: {content}")
    return "\n".join(lines)


async def extract_festival_and_save(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    festival_name: str,
    festival_date: date,
    prompt_template: str,
) -> bool:
    """
    对 (user_id, agent_id) 拉取该会话消息、按节日提示词调用 LLM 抽取回忆摘要，
    删除旧节日记忆后写入一条 memory（memory_type=festival）。
    返回是否成功。
    """
    messages = await asyncio.to_thread(
        get_messages_for_user_agent_sync, user_id, agent_id
    )
    if not messages:
        logger.debug(f"节日记忆跳过：user_id={user_id} agent_id={agent_id} 无消息")
        return False
    chat_text = _format_chat_for_prompt(messages)
    date_str = (
        festival_date.isoformat()
        if isinstance(festival_date, date)
        else str(festival_date)
    )
    full_prompt = f"""{prompt_template}

---
节日名称：{festival_name}
节日日期：{date_str}

---
# 用户与该角色的对话记录

{chat_text}

---
请根据上述对话，抽取该用户与该角色在「{festival_name}」相关的回忆或偏好，输出一段简洁的摘要（一段话即可）。只输出摘要内容，不要其他格式。"""

    cfg = getattr(global_config_loaded_from_config_yaml, "memory_extraction", None)
    model_name = (
        cfg.model.strip() if cfg and cfg.model else None
    ) or DEFAULT_FESTIVAL_EXTRACTION_MODEL
    try:
        summary, _, _ = await call_openrouter_for_extraction(
            full_prompt,
            model=model_name,
            max_tokens=2000,
            temperature=0.3,
        )
        if not summary or len(summary.strip()) < 10:
            raise ValueError("Extraction result is too short or empty")
        summary = summary.strip()
    except Exception as e:
        logger.warning(
            f"节日记忆 LLM 调用失败 user_id={user_id} agent_id={agent_id}: {e}"
        )
        return False

    extracted_at = datetime.now(timezone.utc)
    await db.execute(
        delete(Memory).where(
            Memory.user_id == user_id,
            Memory.agent_id == agent_id,
            Memory.memory_type == MEMORY_TYPE_FESTIVAL,
            Memory.festival_name == festival_name,
            Memory.festival_date == festival_date,
        )
    )
    memory_row = Memory(
        user_id=user_id,
        memory_type=MEMORY_TYPE_FESTIVAL,
        agent_id=agent_id,
        content=summary,
        extracted_at=extracted_at,
        festival_name=festival_name,
        festival_date=festival_date,
    )
    db.add(memory_row)
    await db.commit()
    logger.debug(
        f"节日记忆写入完成 user_id={user_id} agent_id={agent_id} festival={festival_name}"
    )
    session_id = await asyncio.to_thread(
        get_session_id_for_user_agent_sync, user_id, agent_id
    )
    if session_id:
        await asyncio.to_thread(
            chat_history_service.add_festival_memory_prompt_message_sync,
            session_id,
            agent_id,
            memory_row.id,
        )
    return True
