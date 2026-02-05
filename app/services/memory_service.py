# CREATED_BY_AGENT
"""
记忆服务：从 memory 表读取用户记忆，供提示词注入使用。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.agent import get_sync_engine
from app.models.memory import Memory

MEMORY_TYPE_USER_COMMON = "user_common"
MEMORY_TYPE_FESTIVAL = "festival"


def get_user_memory_for_prompt_sync(
    user_id: str, memory_type: str = MEMORY_TYPE_USER_COMMON
) -> str:
    """
    同步获取用户记忆文本，用于拼接到 ##User information 之后。
    查 memory：user_id、memory_type、agent_id IS NULL，按 extracted_at DESC 取最新，多条用 \\n\\n 拼接。
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
            .order_by(Memory.extracted_at.desc())
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
        .order_by(Memory.extracted_at.desc())
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
    返回列表元素：{"festival_date": "YYYY-MM-DD", "festival_name": str, "memory": str}
    """
    stmt = (
        select(
            Memory.festival_date,
            Memory.festival_name,
            Memory.content,
        )
        .where(
            Memory.user_id == user_id,
            Memory.agent_id == agent_id,
            Memory.memory_type == MEMORY_TYPE_FESTIVAL,
        )
        .order_by(Memory.festival_date.asc())
    )
    result = await db.execute(stmt)
    rows = result.fetchall()
    out = []
    for row in rows:
        festival_date, festival_name, content = row
        if festival_date is None or festival_name is None or content is None:
            continue
        out.append(
            {
                "festival_date": (
                    festival_date.isoformat()
                    if hasattr(festival_date, "isoformat")
                    else str(festival_date)
                ),
                "festival_name": festival_name,
                "memory": content,
            }
        )
    return out
