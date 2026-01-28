# CREATED_BY_AGENT
"""
记忆抽取服务：筛选待抽取用户、拉取全量消息、调用 LLM 抽取并写入 memory、memory_extraction_log。
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from loguru import logger
from openai import OpenAI
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory, MemoryExtractionLog
from app.services.chat_history_service import get_chat_history_connection
from app.services.chat_service import generate_session_id

MEMORY_TYPE_USER_COMMON = "user_common"

_PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "prompting"
    / "memory_extraction_prompt.txt"
)


def _load_prompt() -> str:
    if not _PROMPT_PATH.exists():
        raise FileNotFoundError(f"记忆提取提示词文件不存在: {_PROMPT_PATH}")
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _extract_part1_summary(full_analysis: str) -> str:
    """从 LLM 完整回复中解析 Part 1 用户画像摘要。支持中英文 Part 1 标题。"""
    patterns = [
        r"(?:#{1,3}\s*)?(?:\*\*)?Part\s*1[：:][^\n]*(?:\*\*)?\s*\n(.*?)(?=(?:#{1,3}\s*)?(?:\*\*)?Part\s*2|$)",
        r"(\*\*About this user.*?)(?=(?:#{1,3}\s*)?(?:\*\*)?Part\s*2|$)",
        r"(\*\*关于这位用户.*?)(?=(?:#{1,3}\s*)?(?:\*\*)?Part\s*2|$)",
        r"(Part\s*1.*?)(?=Part\s*2|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_analysis, re.DOTALL | re.IGNORECASE)
        if match:
            summary = match.group(1).strip()
            summary = re.sub(r"^---+\s*", "", summary)
            summary = re.sub(r"\s*---+$", "", summary)
            if summary and len(summary) > 50:
                return summary
    user_about = re.search(
        r"(\*\*关于这位用户.*?)(?=\n\n#{2,}|\n\n\*\*Part|\Z)",
        full_analysis,
        re.DOTALL,
    )
    if user_about:
        return user_about.group(1).strip()
    about_en = re.search(
        r"(\*\*About this user.*?)(?=\n\n#{2,}|\n\n\*\*Part|\Z)",
        full_analysis,
        re.DOTALL | re.IGNORECASE,
    )
    if about_en:
        return about_en.group(1).strip()
    return full_analysis[:2000] if len(full_analysis) > 2000 else full_analysis


def get_all_messages_for_user(user_id: str) -> List[Tuple[str, str]]:
    """
    拉取该用户在所有会话中的全部消息 (role, content)，按 created_at 升序。
    不按 agent 过滤，不限制条数。
    """
    conn = get_chat_history_connection()
    # 先取该用户的 chat_id（需访问主库 chats；chat_history 与 chats 同库，此处用同一 conn 无法查 chats，需另查）
    # get_chat_history_connection 连的是 database.url，与主库相同。chats 在主库。我们需要在 memory_extraction 里查 chats，但 get_chat_history_connection 是 psycopg 连接，可执行任意 SQL，包括对 chats 的查询。所以用 conn 查 chats 也可。
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM chats WHERE user_id = %s AND is_active = true",
            (user_id,),
        )
        chat_ids = [r[0] for r in cur.fetchall()]
    if not chat_ids:
        return []
    session_ids = [generate_session_id(cid) for cid in chat_ids]
    placeholders = ",".join("%s" for _ in session_ids)
    query = f"""
        SELECT message
        FROM chat_history
        WHERE session_id::text IN ({placeholders}) AND deleted_at IS NULL
        ORDER BY created_at ASC
    """
    out: List[Tuple[str, str]] = []
    with conn.cursor() as cur:
        cur.execute(query, session_ids)
        for row in cur.fetchall():
            raw = row[0]
            try:
                if isinstance(raw, str):
                    import json

                    data = json.loads(raw)
                elif isinstance(raw, dict):
                    data = raw
                else:
                    data = json.loads(str(raw))
            except Exception:
                continue
            msg_type = data.get("type", "human")
            content = ""
            if (
                "data" in data
                and isinstance(data["data"], dict)
                and "content" in data["data"]
            ):
                content = data["data"]["content"] or ""
            elif "content" in data:
                content = data["content"] or ""
            role = "user" if msg_type in ("human", "HumanMessage") else "assistant"
            out.append((role, str(content)))
    return out


def _format_chat_for_prompt(messages: List[Tuple[str, str]]) -> str:
    lines = []
    for role, content in messages:
        label = "用户" if role == "user" else "AI"
        lines.append(f"**{label}**: {content}")
    return "\n".join(lines)


async def get_users_to_extract(db: AsyncSession) -> List[str]:
    """
    筛选本次需抽取记忆的用户：新用户总消息>=trigger_new_user_messages，
    或已提取用户自上次提取后新增>=trigger_incremental_messages。
    """
    cfg = getattr(
        global_config_loaded_from_config_yaml,
        "memory_extraction",
        None,
    )
    if not cfg:
        return []
    thresh_new = cfg.trigger_new_user_messages
    thresh_incr = cfg.trigger_incremental_messages

    # 所有有会话的用户及其 chat_id
    r = await db.execute(text("SELECT user_id, id FROM chats WHERE is_active = true"))
    rows = r.fetchall()
    user_to_chats: dict = {}
    for uid, cid in rows:
        user_to_chats.setdefault(uid, []).append(cid)

    # 已提取过的用户及其上次 extracted_at
    r2 = await db.execute(
        text("""
            SELECT user_id, MAX(extracted_at) AS last_at
            FROM memory_extraction_log
            WHERE memory_type = :mt
            GROUP BY user_id
        """),
        {"mt": MEMORY_TYPE_USER_COMMON},
    )
    user_to_last = {r[0]: r[1] for r in r2.fetchall()}

    conn = get_chat_history_connection()
    result: List[str] = []

    for user_id, chat_ids in user_to_chats.items():
        sids = [generate_session_id(c) for c in chat_ids]
        ph = ",".join("%s" for _ in sids)
        total = 0
        incr = 0
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*) FROM chat_history
                WHERE session_id::text IN ({ph}) AND deleted_at IS NULL
                """,
                sids,
            )
            total = cur.fetchone()[0] or 0
            last = user_to_last.get(user_id)
            if last is not None:
                cur.execute(
                    f"""
                    SELECT COUNT(*) FROM chat_history
                    WHERE session_id::text IN ({ph}) AND deleted_at IS NULL
                    AND created_at > %s
                    """,
                    sids + [last],
                )
                incr = cur.fetchone()[0] or 0

        if last is None:
            if total >= thresh_new:
                result.append(user_id)
        else:
            if incr >= thresh_incr:
                result.append(user_id)

    return result


async def extract_and_save(db: AsyncSession, user_id: str) -> None:
    """
    对 user_id 拉取全量消息、LLM 抽取 Part1、DELETE 旧 memory、INSERT 新 memory 与 memory_extraction_log。
    """
    cfg = getattr(
        global_config_loaded_from_config_yaml,
        "memory_extraction",
        None,
    )
    if not cfg:
        return
    agent_cfg = global_config_loaded_from_config_yaml.agent
    model = cfg.model or agent_cfg.model
    prompt = _load_prompt()

    messages = get_all_messages_for_user(user_id)
    msg_count = len(messages)
    if msg_count == 0:
        logger.debug(f"记忆抽取跳过：user_id={user_id} 无消息")
        return

    chat_text = _format_chat_for_prompt(messages)
    full_prompt = f"{prompt}\n\n---\n\n# User chat history\n\n{chat_text}"

    try:
        client = OpenAI(api_key=agent_cfg.api_key, base_url=agent_cfg.base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.3,
            max_tokens=4000,
        )
        full_analysis = resp.choices[0].message.content or ""
        part1 = _extract_part1_summary(full_analysis)
    except Exception as e:
        logger.warning(f"记忆抽取 LLM 调用失败 user_id={user_id}: {e}")
        log = MemoryExtractionLog(
            user_id=user_id,
            memory_type=MEMORY_TYPE_USER_COMMON,
            extracted_at=datetime.now(timezone.utc),
            messages_processed_count=msg_count,
            memory_items_count=0,
            status="failed",
        )
        db.add(log)
        await db.commit()
        return

    extracted_at = datetime.now(timezone.utc)
    # 删除该用户 user_common、agent_id 为 NULL 的旧记忆
    await db.execute(
        delete(Memory).where(
            Memory.user_id == user_id,
            Memory.memory_type == MEMORY_TYPE_USER_COMMON,
            Memory.agent_id.is_(None),
        )
    )
    # 写入新记忆（一条 Part1）
    db.add(
        Memory(
            user_id=user_id,
            memory_type=MEMORY_TYPE_USER_COMMON,
            agent_id=None,
            content=part1,
            extracted_at=extracted_at,
        )
    )
    db.add(
        MemoryExtractionLog(
            user_id=user_id,
            memory_type=MEMORY_TYPE_USER_COMMON,
            extracted_at=extracted_at,
            messages_processed_count=msg_count,
            memory_items_count=1,
            status="success",
        )
    )
    await db.commit()
    logger.debug(f"记忆抽取完成 user_id={user_id} messages={msg_count}")
