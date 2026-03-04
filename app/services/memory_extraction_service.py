# CREATED_BY_AGENT
"""
记忆抽取服务：筛选待抽取用户、拉取全量消息、调用 LLM 抽取并写入 memory、memory_extraction_log。
"""

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

import psycopg

from app.api.types.llm_config import LLMConfig
from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory, MemoryExtractionLog
from app.services.chat_history_service import (
    get_chat_history_connection,
    get_chat_history_replica_connection,
)
from app.services.chat_service import generate_session_id
from app.utils.openai_client import chat_completion_for_extraction
from app.utils.openrouter_memory import DEFAULT_MEMORY_EXTRACTION_MODEL

MEMORY_TYPE_USER_COMMON = "user_common"

_MAX_IN_PARAMS = 5000

# Structured output schema for memory extraction (OpenRouter/OpenAI response_format).
# Only part1_summary is persisted to memory.content.
MEMORY_EXTRACTION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "memory_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "part1_summary": {
                    "type": "string",
                    "description": (
                        "User profile summary for prompt embedding. Include only cross-character consistent information. "
                        "Use this structure: **About this user, you should know:** (2-4 sentences) "
                        "**When talking to this user, note:** (bullets) **This user likes:** (bullets) "
                        "**This user dislikes / avoid:** (bullets)."
                    ),
                }
            },
            "required": ["part1_summary"],
            "additionalProperties": False,
        },
    },
}

_PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "prompting"
    / "memory_extraction_prompt.txt"
)


def _load_prompt() -> str:
    if not _PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Memory extraction prompt file not found: {_PROMPT_PATH}"
        )
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


def _part1_from_content(content: str) -> str:
    """
    从 LLM 返回的 content 解析出 Part1 摘要。
    若 content 为 JSON 且含 part1_summary 且长度>=50，则使用该字段；否则回退到 _extract_part1_summary。
    """
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(content)
            part1 = (data.get("part1_summary") or "").strip()
            if part1 and len(part1) >= 50:
                return part1
        except (json.JSONDecodeError, TypeError):
            pass
    return _extract_part1_summary(content)


def get_all_messages_for_user(
    user_id: str, prefer_replica_read: bool = False
) -> List[Tuple[str, str]]:
    """
    拉取该用户在所有会话中的全部消息 (role, content)，按 created_at 升序。
    不按 agent 过滤，不限制条数。
    """
    conn = None
    if prefer_replica_read:
        try:
            conn = get_chat_history_replica_connection()
        except psycopg.Error as e:
            logger.warning(f"[记忆抽取] 获取副本连接失败，回退主库读取消息: {e}")
    if conn is None:
        conn = get_chat_history_connection()
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


_USAGE_TYPE_CHAT = "chat"


def _get_sync_replica_db_url() -> Optional[str]:
    async_replica_url = global_config_loaded_from_config_yaml.database.async_replica_url
    if not async_replica_url:
        return None
    return async_replica_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _resolve_sync_read_db_url(prefer_replica_read: bool) -> str:
    primary_url = global_config_loaded_from_config_yaml.database.url
    if not prefer_replica_read:
        return primary_url
    replica_url = _get_sync_replica_db_url()
    return replica_url or primary_url


def _compute_users_to_extract_sync(
    user_to_chats: dict,
    user_to_last: dict,
    thresh_new: int,
    thresh_incr: int,
    read_db_url: Optional[str] = None,
) -> List[str]:
    """
    在工作线程中执行：用 subscription_usage 的 chat 次数筛出待抽取 user_id。
    新用户按总聊天次数>=thresh_new；已提取用户按自上次 extracted_at 以来增量>=thresh_incr。
    使用线程内新建连接，避免跨线程复用全局连接导致阻塞。
    """
    if not user_to_chats:
        return []

    candidate_user_ids = list(user_to_chats.keys())
    new_user_ids = [uid for uid in candidate_user_ids if uid not in user_to_last]
    old_user_items = [
        (uid, user_to_last[uid]) for uid in candidate_user_ids if uid in user_to_last
    ]
    num_users = len(candidate_user_ids)
    logger.info(
        f"[记忆抽取] 筛选待抽取用户: subscription_usage 统计，有会话用户数={num_users} "
        f"(新={len(new_user_ids)}, 已提取={len(old_user_items)})"
    )

    primary_db_url = global_config_loaded_from_config_yaml.database.url
    db_url = read_db_url or primary_db_url
    try:
        conn = psycopg.connect(db_url, autocommit=True)
    except psycopg.Error as e:
        if read_db_url and db_url != primary_db_url:
            # 迁移关键步骤：离线读优先副本，副本不可达时自动回退主库，保证任务可继续执行。
            logger.warning(f"[记忆抽取] 副本连接失败，回退主库继续筛选用户: {e}")
            conn = psycopg.connect(primary_db_url, autocommit=True)
        else:
            raise
    try:
        result: List[str] = []

        if new_user_ids:
            for i in range(0, len(new_user_ids), _MAX_IN_PARAMS):
                chunk = new_user_ids[i : i + _MAX_IN_PARAMS]
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT user_id, COALESCE(SUM(usage_count), 0)::bigint AS total
                        FROM subscription_usage
                        WHERE usage_type = %s AND user_id = ANY(%s)
                        GROUP BY user_id
                        """,
                        (_USAGE_TYPE_CHAT, chunk),
                    )
                    for row in cur.fetchall():
                        if (row[1] or 0) >= thresh_new:
                            result.append(row[0])

        if old_user_items:
            for i in range(0, len(old_user_items), _MAX_IN_PARAMS):
                chunk = old_user_items[i : i + _MAX_IN_PARAMS]
                values_ph = ",".join("(%s::text, %s::timestamptz)" for _ in chunk)
                flat = []
                for uid, last_at in chunk:
                    flat.append(uid)
                    flat.append(last_at)
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT su.user_id, COALESCE(SUM(su.usage_count), 0)::bigint AS incr
                        FROM subscription_usage su
                        JOIN (VALUES {values_ph}) AS v(user_id, last_at)
                          ON su.user_id = v.user_id AND su.usage_date > v.last_at
                        WHERE su.usage_type = %s
                        GROUP BY su.user_id
                        """,
                        flat + [_USAGE_TYPE_CHAT],
                    )
                    for row in cur.fetchall():
                        if (row[1] or 0) >= thresh_incr:
                            result.append(row[0])

        return result
    finally:
        conn.close()


async def get_users_to_extract(
    db: AsyncSession, prefer_replica_read: bool = False
) -> List[str]:
    """
    筛选本次需抽取记忆的用户：依据 subscription_usage 的 chat 次数，
    新用户总聊天次数>=trigger_new_user_messages，或已提取用户自上次提取后新增聊天次数>=trigger_incremental_messages。
    单用户抽取仍从 chat_history 拉取消息，见 get_all_messages_for_user / extract_and_save。
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

    result = await asyncio.to_thread(
        _compute_users_to_extract_sync,
        user_to_chats,
        user_to_last,
        thresh_new,
        thresh_incr,
        _resolve_sync_read_db_url(prefer_replica_read),
    )
    return result


async def extract_and_save(
    db: AsyncSession, user_id: str, prefer_replica_read: bool = False
) -> None:
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
    prompt = _load_prompt()

    messages = await asyncio.to_thread(
        get_all_messages_for_user, user_id, prefer_replica_read
    )
    msg_count = len(messages)
    if msg_count == 0:
        logger.debug(f"记忆抽取跳过：user_id={user_id} 无消息")
        return

    chat_text = _format_chat_for_prompt(messages)
    full_prompt = f"{prompt}\n\n---\n\n# User chat history\n\n{chat_text}"

    start_time = time.perf_counter()
    try:
        model_name = cfg.model.strip() if cfg.model else DEFAULT_MEMORY_EXTRACTION_MODEL
        llm_config = LLMConfig(
            model=model_name or None,
            max_tokens=4000,
            temperature=0.3,
        )
        try:
            full_analysis, prompt_tokens, completion_tokens = (
                await chat_completion_for_extraction(
                    full_prompt,
                    llm_config=llm_config,
                    response_format=MEMORY_EXTRACTION_RESPONSE_FORMAT,
                )
            )
        except Exception as format_err:
            logger.debug(
                f"记忆抽取 structured output 失败，回退自由文本 user_id={user_id}: {format_err}"
            )
            full_analysis, prompt_tokens, completion_tokens = (
                await chat_completion_for_extraction(
                    full_prompt, llm_config=llm_config
                )
            )
        if not full_analysis or len(full_analysis.strip()) < 10:
            raise ValueError(
                "Unable to extract text from response or content too short"
            )
        part1 = _part1_from_content(full_analysis)
    except Exception as e:
        logger.warning(f"记忆抽取 LLM 调用失败 user_id={user_id}: {e}")
        duration_seconds = time.perf_counter() - start_time
        log = MemoryExtractionLog(
            user_id=user_id,
            memory_type=MEMORY_TYPE_USER_COMMON,
            extracted_at=datetime.now(timezone.utc),
            messages_processed_count=msg_count,
            memory_items_count=0,
            status="failed",
            duration_seconds=duration_seconds,
            prompt_tokens=None,
            completion_tokens=None,
        )
        db.add(log)
        await db.commit()
        return

    duration_seconds = time.perf_counter() - start_time
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
            duration_seconds=duration_seconds,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    )
    await db.commit()
    logger.debug(f"记忆抽取完成 user_id={user_id} messages={msg_count}")
