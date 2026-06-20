# CREATED_BY_AGENT
"""
记忆抽取服务：筛选待抽取用户、拉取全量消息、调用 LLM 抽取并写入 memory、memory_extraction_log。

**Companion importance scores**（可选）：当配置 ``memory_extraction.use_significance_perception_in_extraction``
为真时，从 PostgreSQL ``chat_history.meta_data.significance_perception`` 读取内核写入的重要性三元组
（``importance_round`` / ``importance_user_message`` / ``importance_assistant_message``），按
``importance_round`` 对消息排序并在拼装给抽取模型的文本中附加简短标注（见 ``_prepare_messages_for_memory_extraction``、
``_format_chat_for_prompt``）。数据来源与契约说明见 ``app/core/companion_harness/companion/dual_llm_chat_branch_envelope.py`` 模块 docstring。
"""

import asyncio
import json
import re
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

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
from app.core.llms.openai_client import chat_completion_for_extraction
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

DAILY_PROFILE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "memory_extraction_daily_profile",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "daily_profile_summary": {
                    "type": "string",
                    "description": (
                        "Daily user companionship profile summary derived only from today's messages. "
                        "Include emotional signals, companionship needs, notable preference shifts, and boundaries."
                    ),
                }
            },
            "required": ["daily_profile_summary"],
            "additionalProperties": False,
        },
    },
}

_DAILY_PROFILE_PROMPT_TEMPLATE = """
You are a user companionship analyst.

Task:
Summarize the user's companionship-relevant profile ONLY from the provided one-day chat history.
Do not use assumptions outside the conversation.

Focus on:
1) emotional state and companionship needs shown today,
2) stable or changing preferences shown today,
3) boundaries/dislikes shown today,
4) concrete details useful for future empathetic conversations.

Output requirement:
Return a JSON object with exactly one field:
- daily_profile_summary (string)

Target UTC day: {target_day}
""".strip()

_INCREMENTAL_UPDATE_PROMPT_TEMPLATE = """
You are updating a persistent cross-character user companionship profile.

You are given:
1) the previous persisted profile,
2) a newly summarized one-day profile.

Update rules:
- Keep stable facts/preferences unless the new daily summary clearly updates them.
- Incorporate new companionship needs if evidenced in today's summary.
- Remove or soften outdated items when today's summary conflicts with old profile.
- Keep only user information (never AI output-style rules).
- The final profile must remain cross-character usable.

Output requirement:
Return a JSON object with exactly one field:
- part1_summary (string)

The part1_summary must follow this structure:
**About this user, you should know:**
[2-4 sentences]

**When talking to this user, note:**
- ...

**This user likes:**
- ...

**This user dislikes / avoid:**
- ...

Target UTC day: {target_day}
""".strip()

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


def _summary_field_from_content(
    content: str, field_name: str, min_length: int = 20
) -> str:
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(content)
            value = (data.get(field_name) or "").strip()
            if value and len(value) >= min_length:
                return value
        except (json.JSONDecodeError, TypeError):
            pass
    return content[:2000] if len(content) > 2000 else content


def _utc_day_bounds(target_date_utc: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_date_utc, dt_time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _build_daily_profile_prompt(
    chat_text: str,
    target_date_utc: date,
    *,
    include_significance_hints: bool = False,
) -> str:
    header = _DAILY_PROFILE_PROMPT_TEMPLATE.format(
        target_day=target_date_utc.isoformat()
    )
    sig = (
        f"\n\n{_significance_extraction_prompt_block()}"
        if include_significance_hints
        else ""
    )
    return f"{header}{sig}\n\n---\n\n# User chat history for the target day\n\n{chat_text}"


def _build_incremental_update_prompt(
    existing_profile: str,
    daily_profile: str,
    target_date_utc: date,
    *,
    include_significance_hints: bool = False,
) -> str:
    header = _INCREMENTAL_UPDATE_PROMPT_TEMPLATE.format(
        target_day=target_date_utc.isoformat()
    )
    sig = (
        f"\n\n{_significance_extraction_prompt_block()}"
        if include_significance_hints
        else ""
    )
    existing = existing_profile.strip() if existing_profile else "(empty)"
    return (
        f"{header}{sig}\n\n---\n\n# Previous persisted profile\n\n{existing}\n\n---\n\n"
        f"# New daily profile\n\n{daily_profile}"
    )


def _importance_round_from_meta(meta: dict[str, Any] | None) -> int:
    """Extract ``importance_round`` from ``chat_history.meta_data`` for significance-aware ordering."""
    if not meta:
        return 0
    sp = meta.get("significance_perception")
    if not isinstance(sp, dict):
        return 0
    v = sp.get("importance_round")
    if isinstance(v, bool) or not isinstance(v, int):
        return 0
    return max(0, min(10, v))


def _format_chat_for_prompt(
    messages: List[Tuple[str, str, dict[str, Any] | None]],
) -> str:
    lines = []
    for role, content, meta in messages:
        label = "用户" if role == "user" else "AI"
        extra = ""
        if meta and isinstance(meta.get("significance_perception"), dict):
            sp = meta["significance_perception"]
            if isinstance(sp, dict):
                ir = sp.get("importance_round")
                iu = sp.get("importance_user_message")
                ia = sp.get("importance_assistant_message")
                if all(
                    isinstance(x, int) and not isinstance(x, bool)
                    for x in (ir, iu, ia)
                ):
                    extra = (
                        f" [significance round={ir}/10 user_msg={iu}/10 "
                        f"assistant_msg={ia}/10]"
                    )
        lines.append(f"**{label}**{extra}: {content}")
    return "\n".join(lines)


def _significance_extraction_prompt_block() -> str:
    return (
        "## Significance hints (optional metadata)\n\n"
        "Some lines may include bracket tags like "
        "`[significance round=R/10 user_msg=U/10 assistant_msg=A/10]` on AI messages. "
        "These come from the companion kernel when available: higher scores suggest the turn "
        "was more important for long-term user modeling. "
        "Use them as soft prioritization when deciding what to include in the profile summary; "
        "do not invent scores when the tags are absent."
    )


def _prepare_messages_for_memory_extraction(
    rows: List[Tuple[str, str, dict[str, Any] | None]],
    *,
    use_significance: bool,
) -> List[Tuple[str, str, dict[str, Any] | None]]:
    if not use_significance:
        return rows
    indexed = list(enumerate(rows))
    indexed.sort(
        key=lambda it: (-_importance_round_from_meta(it[1][2]), it[0]),
    )
    return [it[1] for it in indexed]


def _sum_optional_int(values: list[int | None]) -> int | None:
    ints = [v for v in values if isinstance(v, int)]
    if not ints:
        return None
    return sum(ints)


async def _chat_completion_with_structured_fallback(
    prompt: str,
    llm_config: LLMConfig,
    response_format: dict,
    log_prefix: str,
) -> tuple[str, int | None, int | None]:
    try:
        return await chat_completion_for_extraction(
            prompt, llm_config=llm_config, response_format=response_format
        )
    except Exception as format_err:
        logger.debug(
            f"{log_prefix} structured output 失败，回退自由文本: {format_err}"
        )
        return await chat_completion_for_extraction(
            prompt, llm_config=llm_config
        )


def _parse_chat_history_json_object(
    value: Any, chat_history_id: str, column_name: str
) -> dict[str, Any] | None:
    assert column_name in {"message", "meta_data"}
    try:
        if isinstance(value, str):
            parsed = json.loads(value)
        elif isinstance(value, dict):
            parsed = value
        else:
            parsed = json.loads(str(value))
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(
            "[记忆抽取] 跳过 malformed chat_history "
            f"{column_name} row_id={chat_history_id}: {e}"
        )
        return None

    if not isinstance(parsed, dict):
        logger.warning(
            "[记忆抽取] 跳过非对象 chat_history "
            f"{column_name} row_id={chat_history_id}"
        )
        return None

    return parsed


def _materialize_chat_history_row(
    chat_history_id: str, raw: Any, meta_raw: Any
) -> Tuple[str, str, dict[str, Any] | None] | None:
    meta = None
    if meta_raw is not None:
        meta = _parse_chat_history_json_object(
            meta_raw, chat_history_id, "meta_data"
        )

    data = _parse_chat_history_json_object(raw, chat_history_id, "message")
    if data is None:
        return None

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
    return (role, str(content), meta)


def get_all_messages_for_user(
    user_id: str, prefer_replica_read: bool = False
) -> List[Tuple[str, str, dict[str, Any] | None]]:
    """
    拉取该用户在所有会话中的全部消息 (role, content, meta_data)，按 created_at 升序。
    不按 agent 过滤，不限制条数。
    """
    conn = None
    if prefer_replica_read:
        try:
            conn = get_chat_history_replica_connection()
        except psycopg.Error as e:
            logger.warning(
                f"[记忆抽取] 获取副本连接失败，回退主库读取消息: {e}"
            )
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
    out: List[Tuple[str, str, dict[str, Any] | None]] = []
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, message, meta_data
            FROM chat_history
            WHERE session_id::text IN ({placeholders}) AND deleted_at IS NULL
            ORDER BY created_at ASC
            """,
            session_ids,
        )
        for row in cur.fetchall():
            materialized = _materialize_chat_history_row(
                str(row[0]), row[1], row[2]
            )
            if materialized is not None:
                out.append(materialized)
    return out


def get_messages_for_user_in_utc_day(
    user_id: str, target_date_utc: date, prefer_replica_read: bool = False
) -> List[Tuple[str, str, dict[str, Any] | None]]:
    """
    拉取该用户在指定 UTC 日内的全部消息 (role, content, meta_data)，按 created_at 升序。
    """
    start_at, end_at = _utc_day_bounds(target_date_utc)
    conn = None
    if prefer_replica_read:
        try:
            conn = get_chat_history_replica_connection()
        except psycopg.Error as e:
            logger.warning(
                f"[记忆抽取] 获取副本连接失败，回退主库读取消息: {e}"
            )
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
    out: List[Tuple[str, str, dict[str, Any] | None]] = []
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, message, meta_data
            FROM chat_history
            WHERE session_id::text IN ({placeholders})
              AND deleted_at IS NULL
              AND created_at >= %s
              AND created_at < %s
            ORDER BY created_at ASC
            """,
            session_ids + [start_at, end_at],
        )
        for row in cur.fetchall():
            materialized = _materialize_chat_history_row(
                str(row[0]), row[1], row[2]
            )
            if materialized is not None:
                out.append(materialized)
    return out


_USAGE_TYPE_CHAT = "chat"


def _get_sync_replica_db_url() -> Optional[str]:
    async_replica_url = (
        global_config_loaded_from_config_yaml.database.async_replica_url
    )
    if not async_replica_url:
        return None
    return async_replica_url.replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )


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
    new_user_ids = [
        uid for uid in candidate_user_ids if uid not in user_to_last
    ]
    old_user_items = [
        (uid, user_to_last[uid])
        for uid in candidate_user_ids
        if uid in user_to_last
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
            logger.warning(
                f"[记忆抽取] 副本连接失败，回退主库继续筛选用户: {e}"
            )
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
                values_ph = ",".join(
                    "(%s::text, %s::timestamptz)" for _ in chunk
                )
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


def _compute_users_with_messages_in_utc_day_sync(
    target_date_utc: date, read_db_url: Optional[str] = None
) -> List[str]:
    """
    在工作线程中执行：按 UTC 日窗口从 subscription_usage 中筛选有 chat 行为的 user_id。
    """
    start_at, end_at = _utc_day_bounds(target_date_utc)
    primary_db_url = global_config_loaded_from_config_yaml.database.url
    db_url = read_db_url or primary_db_url
    try:
        conn = psycopg.connect(db_url, autocommit=True)
    except psycopg.Error as e:
        if read_db_url and db_url != primary_db_url:
            logger.warning(
                f"[记忆抽取] 副本连接失败，回退主库继续筛选用户: {e}"
            )
            conn = psycopg.connect(primary_db_url, autocommit=True)
        else:
            raise
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT su.user_id
                FROM subscription_usage su
                WHERE su.usage_type = %s
                  AND su.usage_date >= %s
                  AND su.usage_date < %s
                  AND EXISTS (
                      SELECT 1
                      FROM chats c
                      WHERE c.user_id = su.user_id
                        AND c.is_active = true
                  )
                """,
                (_USAGE_TYPE_CHAT, start_at, end_at),
            )
            return [row[0] for row in cur.fetchall()]
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
    r = await db.execute(
        text("SELECT user_id, id FROM chats WHERE is_active = true")
    )
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


async def get_users_with_messages_in_utc_day(
    db: AsyncSession,
    target_date_utc: date,
    prefer_replica_read: bool = False,
) -> List[str]:
    """
    获取指定 UTC 日内有新 chat 消息的用户列表，用于增量记忆抽取。
    """
    _ = db
    return await asyncio.to_thread(
        _compute_users_with_messages_in_utc_day_sync,
        target_date_utc,
        _resolve_sync_read_db_url(prefer_replica_read),
    )


def _memory_llm_config(cfg) -> LLMConfig:
    model_name = (
        cfg.model.strip() if cfg.model else DEFAULT_MEMORY_EXTRACTION_MODEL
    )
    return LLMConfig(
        model=model_name or None,
        max_tokens=4000,
        temperature=0.3,
    )


async def _latest_user_common_memory_content(
    db: AsyncSession, user_id: str
) -> str:
    result = await db.execute(
        text("""
            SELECT content
            FROM memory
            WHERE user_id = :user_id
              AND memory_type = :memory_type
              AND agent_id IS NULL
            ORDER BY extracted_at DESC
            LIMIT 1
            """),
        {"user_id": user_id, "memory_type": MEMORY_TYPE_USER_COMMON},
    )
    row = result.first()
    if row is None:
        return ""
    return row[0] or ""


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

    sig_enabled = bool(
        getattr(cfg, "use_significance_perception_in_extraction", False)
    )
    messages_for_prompt = _prepare_messages_for_memory_extraction(
        messages, use_significance=sig_enabled
    )
    chat_text = _format_chat_for_prompt(messages_for_prompt)
    sig_block = (
        f"\n\n{_significance_extraction_prompt_block()}" if sig_enabled else ""
    )
    full_prompt = (
        f"{prompt}{sig_block}\n\n---\n\n# User chat history\n\n{chat_text}"
    )

    start_time = time.perf_counter()
    try:
        llm_config = _memory_llm_config(cfg)
        full_analysis, prompt_tokens, completion_tokens = (
            await _chat_completion_with_structured_fallback(
                full_prompt,
                llm_config=llm_config,
                response_format=MEMORY_EXTRACTION_RESPONSE_FORMAT,
                log_prefix=f"记忆抽取 user_id={user_id}",
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


async def extract_and_save_incremental_daily(
    db: AsyncSession,
    user_id: str,
    target_date_utc: date,
    prefer_replica_read: bool = False,
) -> None:
    """
    增量记忆抽取：仅使用指定 UTC 日消息生成 daily profile，再更新 user_common 画像。
    """
    cfg = getattr(
        global_config_loaded_from_config_yaml,
        "memory_extraction",
        None,
    )
    if not cfg:
        return

    messages = await asyncio.to_thread(
        get_messages_for_user_in_utc_day,
        user_id,
        target_date_utc,
        prefer_replica_read,
    )
    msg_count = len(messages)
    if msg_count == 0:
        logger.debug(
            f"记忆抽取增量跳过：user_id={user_id} target_date_utc={target_date_utc} 无消息"
        )
        return

    sig_enabled = bool(
        getattr(cfg, "use_significance_perception_in_extraction", False)
    )
    messages_for_prompt = _prepare_messages_for_memory_extraction(
        messages, use_significance=sig_enabled
    )
    chat_text = _format_chat_for_prompt(messages_for_prompt)
    daily_prompt = _build_daily_profile_prompt(
        chat_text,
        target_date_utc,
        include_significance_hints=sig_enabled,
    )
    start_time = time.perf_counter()
    try:
        llm_config = _memory_llm_config(cfg)
        daily_analysis, daily_prompt_tokens, daily_completion_tokens = (
            await _chat_completion_with_structured_fallback(
                daily_prompt,
                llm_config=llm_config,
                response_format=DAILY_PROFILE_RESPONSE_FORMAT,
                log_prefix=(
                    "记忆抽取增量-日总结 "
                    f"user_id={user_id} target_date_utc={target_date_utc}"
                ),
            )
        )
        if not daily_analysis or len(daily_analysis.strip()) < 10:
            raise ValueError("Unable to extract daily profile from response")
        daily_profile = _summary_field_from_content(
            daily_analysis, field_name="daily_profile_summary", min_length=20
        )
        if not daily_profile or len(daily_profile.strip()) < 10:
            raise ValueError("Daily profile summary is empty or too short")

        previous_profile = await _latest_user_common_memory_content(db, user_id)
        update_prompt = _build_incremental_update_prompt(
            previous_profile,
            daily_profile,
            target_date_utc,
            include_significance_hints=sig_enabled,
        )
        full_analysis, update_prompt_tokens, update_completion_tokens = (
            await _chat_completion_with_structured_fallback(
                update_prompt,
                llm_config=llm_config,
                response_format=MEMORY_EXTRACTION_RESPONSE_FORMAT,
                log_prefix=(
                    "记忆抽取增量-画像更新 "
                    f"user_id={user_id} target_date_utc={target_date_utc}"
                ),
            )
        )
        if not full_analysis or len(full_analysis.strip()) < 10:
            raise ValueError("Unable to extract updated profile from response")
        part1 = _part1_from_content(full_analysis)
    except Exception as e:
        logger.warning(
            "记忆抽取增量 LLM 调用失败 "
            f"user_id={user_id} target_date_utc={target_date_utc}: {e}"
        )
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
    await db.execute(
        delete(Memory).where(
            Memory.user_id == user_id,
            Memory.memory_type == MEMORY_TYPE_USER_COMMON,
            Memory.agent_id.is_(None),
        )
    )
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
            prompt_tokens=_sum_optional_int(
                [daily_prompt_tokens, update_prompt_tokens]
            ),
            completion_tokens=_sum_optional_int(
                [daily_completion_tokens, update_completion_tokens]
            ),
        )
    )
    await db.commit()
    logger.debug(
        "记忆抽取增量完成 "
        f"user_id={user_id} target_date_utc={target_date_utc} messages={msg_count}"
    )
