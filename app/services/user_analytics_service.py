"""用户数据分析服务 - 将脚本查询逻辑重构为异步服务"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml

BATCH_SIZE = 500  # 默认每批数量，可通过 user_analytics_report.batch_size 覆盖


def generate_session_id(chat_id: str) -> str:
    """生成 session_id，与 app/services/chat_service.py 中的逻辑一致"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


def _batch_list(items: List[Any], batch_size: int = BATCH_SIZE) -> List[List[Any]]:
    """将列表分批"""
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


class UserAnalyticsService:
    """用户行为分析服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        uar = getattr(
            global_config_loaded_from_config_yaml, "user_analytics_report", None
        )
        self._batch_size = getattr(uar, "batch_size", BATCH_SIZE)

    async def get_new_users(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """查询用户注册统计（按注册日期范围）"""
        query = text("""
            SELECT 
                DATE(created_at AT TIME ZONE 'UTC') as date,
                auth_type,
                COUNT(*) as count
            FROM users
            WHERE created_at >= :register_start_date 
              AND created_at < :register_end_date
              AND deleted_at IS NULL
            GROUP BY DATE(created_at AT TIME ZONE 'UTC'), auth_type
            ORDER BY date, auth_type
        """)
        result = await self.db.execute(
            query,
            {
                "register_start_date": register_start_date,
                "register_end_date": register_end_date,
            },
        )
        rows = result.fetchall()
        return [
            {
                "date": (
                    row[0].isoformat() if isinstance(row[0], datetime) else str(row[0])
                ),
                "auth_type": row[1],
                "count": row[2],
            }
            for row in rows
        ]

    async def get_user_chat_activity(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """查询用户聊天活动（原始数据，按注册日期范围筛选用户）"""
        query = text("""
            SELECT 
                u.id as user_id,
                u.auth_type,
                u.created_at,
                u.nickname,
                u.email,
                c.id as chat_id,
                a.id as agent_id,
                a.name as agent_name
            FROM users u
            LEFT JOIN chats c ON u.id = c.user_id AND c.is_active = true
            LEFT JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE u.created_at >= :register_start_date 
              AND u.created_at < :register_end_date
              AND u.deleted_at IS NULL
            ORDER BY u.id, c.created_at
        """)
        result = await self.db.execute(
            query,
            {
                "register_start_date": register_start_date,
                "register_end_date": register_end_date,
            },
        )
        rows = result.fetchall()
        return [
            {
                "user_id": row[0],
                "auth_type": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "nickname": row[3],
                "email": row[4],
                "chat_id": row[5],
                "agent_id": row[6],
                "agent_name": row[7],
            }
            for row in rows
        ]

    async def get_chat_agent_info(self, chat_ids: List[str]) -> List[Dict[str, Any]]:
        """按 chat_id 批量查询 chat 对应的 user_id、agent_name，用于热门角色等仅需有活动 chat 的场景。"""
        if not chat_ids:
            return []
        out: List[Dict[str, Any]] = []
        for batch in _batch_list(chat_ids, self._batch_size):
            placeholders = ",".join([f":chat_id_{i}" for i in range(len(batch))])
            query = text(f"""
                SELECT c.id as chat_id, c.user_id, a.name as agent_name
                FROM chats c
                INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
                WHERE c.id::text IN ({placeholders}) AND c.is_active = true
            """)
            params = {f"chat_id_{i}": cid for i, cid in enumerate(batch)}
            result = await self.db.execute(query, params)
            for row in result.fetchall():
                out.append(
                    {
                        "chat_id": row[0],
                        "user_id": row[1],
                        "agent_name": row[2],
                    }
                )
        return out

    async def get_active_session_ids_on_date(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
    ) -> Set[str]:
        """查询在指定日期范围内有消息的 session_id 集合（排除记忆提醒消息）。

        用于日报等单日统计时先缩小范围，只对当日有活动的 session 做后续批量聚合。
        """
        query = text("""
            SELECT DISTINCT session_id::text
            FROM chat_history
            WHERE created_at >= :activity_start_date
              AND created_at < :activity_end_date
              AND (meta_data->>'messageType' IS NULL
                   OR (meta_data->>'messageType' != 'festival_memory_prompt'
                       AND meta_data->>'messageType' != 'daily_memory_prompt'))
        """)
        result = await self.db.execute(
            query,
            {
                "activity_start_date": activity_start_date,
                "activity_end_date": activity_end_date,
            },
        )
        return {row[0] for row in result.fetchall()}

    async def get_generated_images_on_date(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围内的生图列表（用于日报展示）"""
        # 关键步骤：按日报传入的 UTC 日期边界查询，避免“最近 1 天”导致跨日报口径不一致。
        query = text("""
            SELECT
                id,
                session_id::text as session_id,
                REPLACE(
                    meta_data->'generated_image'->>'image_url',
                    'gs://',
                    'https://storage.googleapis.com/'
                ) as image_url,
                meta_data,
                created_at
            FROM chat_history
            WHERE meta_data->'generated_image' IS NOT NULL
              AND meta_data->'generated_image'->>'image_url' IS NOT NULL
              AND deleted_at IS NULL
              AND created_at >= :activity_start_date
              AND created_at < :activity_end_date
            ORDER BY created_at DESC
        """)
        result = await self.db.execute(
            query,
            {
                "activity_start_date": activity_start_date,
                "activity_end_date": activity_end_date,
            },
        )
        rows = result.fetchall()
        return [
            {
                "id": row[0],
                "session_id": row[1],
                "image_url": row[2],
                "meta_data": row[3] or {},
                "created_at": row[4].isoformat() if row[4] else None,
            }
            for row in rows
        ]

    async def get_voice_audios_on_date(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
        register_start_date: Optional[datetime] = None,
        register_end_date: Optional[datetime] = None,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """查询指定日期范围内的语音播报与语音通话录音，按 (user_id, agent_id) 分组。

        返回: (voice_message_groups, voice_call_groups)。每组为 { user_id, agent_id, agent_name, audios: [{ audio_url, message_id, created_at, duration_seconds }] }。
        语音通话同一 URL 在 user/AI 两条消息上共享，按 (user_id, agent_id) 内按 audio_url 去重。
        """
        from collections import defaultdict

        reg_start = register_start_date or datetime(2020, 1, 1, tzinfo=timezone.utc)
        reg_end = register_end_date or activity_end_date

        active_session_ids = await self.get_active_session_ids_on_date(
            activity_start_date, activity_end_date
        )
        if not active_session_ids:
            return [], []

        chats_query = text("""
            SELECT c.id, c.user_id, c.agent_id, a.name
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id AND u.deleted_at IS NULL
            INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE u.created_at >= :reg_start AND u.created_at < :reg_end
              AND c.is_active = true
        """)
        result = await self.db.execute(
            chats_query,
            {"reg_start": reg_start, "reg_end": reg_end},
        )
        session_to_user_agent: Dict[str, tuple] = {}
        for row in result.fetchall():
            chat_id, user_id, agent_id, agent_name = row
            sid = generate_session_id(str(chat_id))
            if sid in active_session_ids:
                session_to_user_agent[sid] = (
                    str(user_id),
                    str(agent_id),
                    agent_name or "",
                )

        session_ids = [s for s in active_session_ids if s in session_to_user_agent]
        if not session_ids:
            return [], []

        rows_audio: List[tuple] = []
        for batch in _batch_list(session_ids, self._batch_size):
            placeholders = ",".join([f":sid_{i}" for i in range(len(batch))])
            query = text(f"""
                SELECT session_id::text, id, audio_url, created_at, meta_data
                FROM chat_history
                WHERE session_id::text IN ({placeholders})
                  AND created_at >= :act_start AND created_at < :act_end
                  AND audio_url IS NOT NULL AND deleted_at IS NULL
            """)
            params = {f"sid_{i}": s for i, s in enumerate(batch)}
            params["act_start"] = activity_start_date
            params["act_end"] = activity_end_date
            res = await self.db.execute(query, params)
            rows_audio.extend(res.fetchall())

        def _duration_from_meta(meta: Optional[Dict]) -> Optional[float]:
            if not meta:
                return None
            d = meta.get("audioDuration")
            if d is not None and isinstance(d, (int, float)):
                return float(d)
            return None

        voice_message_key_to_audios: Dict[tuple, List[Dict[str, Any]]] = defaultdict(
            list
        )
        voice_call_key_to_seen_url: Dict[tuple, Dict[str, Dict[str, Any]]] = (
            defaultdict(dict)
        )
        key_to_agent_name: Dict[tuple, str] = {}

        for row in rows_audio:
            session_id, msg_id, audio_url, created_at, meta_data = row
            meta = meta_data or {}
            is_voice_call = meta.get("is_voice") in (True, "true")
            t = session_to_user_agent.get(session_id)
            if not t:
                continue
            user_id, agent_id, agent_name = t
            key = (user_id, agent_id)
            key_to_agent_name[key] = agent_name or ""
            created_at_str = created_at.isoformat() if created_at else None
            duration = _duration_from_meta(meta)
            entry = {
                "audio_url": audio_url,
                "message_id": msg_id,
                "created_at": created_at_str,
                "duration_seconds": duration,
            }
            if is_voice_call:
                if audio_url not in voice_call_key_to_seen_url[key]:
                    voice_call_key_to_seen_url[key][audio_url] = entry
                else:
                    existing = voice_call_key_to_seen_url[key][audio_url]
                    if created_at and (
                        existing.get("created_at") is None
                        or (existing["created_at"] or "") > (created_at_str or "")
                    ):
                        voice_call_key_to_seen_url[key][audio_url] = entry
            else:
                voice_message_key_to_audios[key].append(entry)

        def _build_groups(
            key_to_audios: Dict[tuple, Any],
            values_are_list: bool,
        ) -> List[Dict[str, Any]]:
            out = []
            for (user_id, agent_id), audios in key_to_audios.items():
                audios_list = audios if values_are_list else list(audios.values())
                out.append(
                    {
                        "user_id": user_id,
                        "agent_id": agent_id,
                        "agent_name": key_to_agent_name.get((user_id, agent_id), ""),
                        "audios": audios_list,
                    }
                )
            return out

        voice_message_groups = _build_groups(
            voice_message_key_to_audios, values_are_list=True
        )
        voice_call_groups = _build_groups(
            voice_call_key_to_seen_url, values_are_list=False
        )
        return voice_message_groups, voice_call_groups

    async def _query_session_message_counts(
        self,
        session_ids: List[str],
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
    ) -> Dict[str, tuple]:
        """分批查询 session 的消息统计

        返回: {session_id: (message_count, non_opening_count)}
        """
        if not session_ids:
            return {}

        session_to_counts: Dict[str, tuple] = {}

        for batch in _batch_list(session_ids, self._batch_size):
            placeholders = ",".join([f":session_id_{i}" for i in range(len(batch))])

            if activity_start_date and activity_end_date:
                history_query = text(f"""
                    SELECT 
                        session_id::text as session_id,
                        COUNT(*) as message_count,
                        COUNT(*) FILTER (
                            WHERE meta_data->>'isOpening' != 'true' OR meta_data IS NULL
                        ) as non_opening_count
                    FROM chat_history
                    WHERE session_id::text IN ({placeholders})
                      AND created_at >= :activity_start_date
                      AND created_at < :activity_end_date
                      AND (meta_data->>'messageType' IS NULL OR (meta_data->>'messageType' != 'festival_memory_prompt' AND meta_data->>'messageType' != 'daily_memory_prompt'))
                    GROUP BY session_id
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(batch)}
                params["activity_start_date"] = activity_start_date
                params["activity_end_date"] = activity_end_date
            else:
                history_query = text(f"""
                    SELECT 
                        session_id::text as session_id,
                        COUNT(*) as message_count,
                        COUNT(*) FILTER (
                            WHERE meta_data->>'isOpening' != 'true' OR meta_data IS NULL
                        ) as non_opening_count
                    FROM chat_history
                    WHERE session_id::text IN ({placeholders})
                      AND (meta_data->>'messageType' IS NULL OR (meta_data->>'messageType' != 'festival_memory_prompt' AND meta_data->>'messageType' != 'daily_memory_prompt'))
                    GROUP BY session_id
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(batch)}

            result = await self.db.execute(history_query, params)
            for row in result.fetchall():
                session_to_counts[row[0]] = (row[1], row[2])

        return session_to_counts

    async def get_conversation_rounds(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
        active_session_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """查询对话轮数统计（按Session）

        参数:
            register_start_date/register_end_date: 用户注册日期范围，筛选用户
            activity_start_date/activity_end_date: 活跃日期范围，筛选消息时间
            active_session_ids: 若提供，仅统计这些 session（与注册范围取交集），用于日报缩小范围
        """
        chats_query = text("""
            SELECT c.id
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.created_at >= :register_start_date 
              AND u.created_at < :register_end_date
              AND u.deleted_at IS NULL
              AND c.is_active = true
        """)
        result = await self.db.execute(
            chats_query,
            {
                "register_start_date": register_start_date,
                "register_end_date": register_end_date,
            },
        )
        chat_ids = [row[0] for row in result.fetchall()]

        logger.info(f"get_conversation_rounds: 找到 {len(chat_ids)} 个用户的会话")

        if not chat_ids:
            logger.info("get_conversation_rounds: 没有找到用户的会话")
            return []

        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if active_session_ids is not None:
            session_ids = [s for s in session_ids if s in active_session_ids]
            chat_to_session = {
                cid: sid
                for cid, sid in chat_to_session.items()
                if sid in active_session_ids
            }
            logger.info(
                f"get_conversation_rounds: 限定当日有活动的 session 后共 {len(session_ids)} 个"
            )

        if not session_ids:
            logger.info("get_conversation_rounds: 没有生成有效的 session_ids")
            return []

        session_to_counts = await self._query_session_message_counts(
            session_ids, activity_start_date, activity_end_date
        )

        data = []
        for chat_id, session_id in chat_to_session.items():
            if session_id in session_to_counts:
                message_count, non_opening_count = session_to_counts[session_id]
                if non_opening_count > 0:
                    data.append(
                        {
                            "chat_id": chat_id,
                            "message_count": message_count,
                            "message_count_excluding_opening": non_opening_count,
                        }
                    )

        message_counts = [d["message_count_excluding_opening"] for d in data]
        if message_counts:
            from collections import Counter

            count_distribution = Counter(message_counts)
            logger.info(
                f"get_conversation_rounds: 返回 {len(data)} 个有用户消息的会话，"
                f"消息数分布（前10个最常见的值）: {dict(count_distribution.most_common(10))}"
            )
        else:
            logger.info("get_conversation_rounds: 没有找到有用户消息的会话")

        return data

    async def _query_session_user_message_counts(
        self,
        session_ids: List[str],
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """分批查询 session 的用户消息数（排除开场白）

        返回: {session_id: user_message_count}
        """
        if not session_ids:
            return {}

        session_to_count: Dict[str, int] = {}

        for batch in _batch_list(session_ids, self._batch_size):
            placeholders = ",".join([f":session_id_{i}" for i in range(len(batch))])

            if activity_start_date and activity_end_date:
                messages_query = text(f"""
                    SELECT
                        ch.session_id::text as session_id,
                        COUNT(*) FILTER (
                            WHERE ch.message->>'type' = 'human'
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as user_message_count
                    FROM chat_history ch
                    WHERE ch.session_id::text IN ({placeholders})
                      AND ch.created_at >= :activity_start_date
                      AND ch.created_at < :activity_end_date
                    GROUP BY ch.session_id
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(batch)}
                params["activity_start_date"] = activity_start_date
                params["activity_end_date"] = activity_end_date
            else:
                messages_query = text(f"""
                    SELECT
                        ch.session_id::text as session_id,
                        COUNT(*) FILTER (
                            WHERE ch.message->>'type' = 'human'
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as user_message_count
                    FROM chat_history ch
                    WHERE ch.session_id::text IN ({placeholders})
                    GROUP BY ch.session_id
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(batch)}

            result = await self.db.execute(messages_query, params)
            for row in result.fetchall():
                session_to_count[row[0]] = row[1]

        return session_to_count

    async def get_user_rounds_distribution(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
        active_session_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """查询对话轮数分布（按用户）

        参数:
            register_start_date/register_end_date: 用户注册日期范围，筛选用户
            activity_start_date/activity_end_date: 活跃日期范围，筛选消息时间
            active_session_ids: 若提供，仅统计这些 session，用于日报缩小范围
        """
        chats_query = text("""
            SELECT
                c.user_id,
                c.id as chat_id
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.created_at >= :register_start_date 
              AND u.created_at < :register_end_date
              AND u.deleted_at IS NULL
              AND c.is_active = true
        """)
        result = await self.db.execute(
            chats_query,
            {
                "register_start_date": register_start_date,
                "register_end_date": register_end_date,
            },
        )
        chat_records = result.fetchall()

        if not chat_records:
            return []

        chat_ids = [row[1] for row in chat_records]
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if active_session_ids is not None:
            chat_records = [
                (user_id, chat_id)
                for user_id, chat_id in chat_records
                if chat_to_session[chat_id] in active_session_ids
            ]
            session_ids = [s for s in session_ids if s in active_session_ids]
            chat_to_session = {
                cid: sid
                for cid, sid in chat_to_session.items()
                if sid in active_session_ids
            }

        if not session_ids:
            return []

        session_to_user_msg_count = await self._query_session_user_message_counts(
            session_ids, activity_start_date, activity_end_date
        )

        user_to_total_rounds: Dict[str, int] = {}
        for user_id, chat_id in chat_records:
            session_id = chat_to_session[chat_id]
            user_msg_count = session_to_user_msg_count.get(session_id, 0)
            if user_id not in user_to_total_rounds:
                user_to_total_rounds[user_id] = 0
            user_to_total_rounds[user_id] += user_msg_count

        return [
            {"user_id": user_id, "total_rounds": total_rounds}
            for user_id, total_rounds in user_to_total_rounds.items()
        ]

    async def get_popular_agents(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
        limit: int = 20,
        active_session_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """获取热门角色排行（Top N）

        当传入 active_session_ids 时，仅基于有活动的 chat 查询 (user_id, agent_name)，
        避免全量 get_user_chat_activity 在副本上超时。
        """
        from collections import defaultdict

        rounds_data = await self.get_conversation_rounds(
            register_start_date,
            register_end_date,
            activity_start_date,
            activity_end_date,
            active_session_ids=active_session_ids,
        )
        chat_to_rounds = {
            item["chat_id"]: item["message_count_excluding_opening"]
            for item in rounds_data
        }

        if active_session_ids is not None:
            chat_ids = list(dict.fromkeys([r["chat_id"] for r in rounds_data]))
            activity_data = await self.get_chat_agent_info(chat_ids)
        else:
            activity_data = await self.get_user_chat_activity(
                register_start_date, register_end_date
            )

        agent_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "users": set(),
                "rounds": 0,
                "sessions": [],
                "total_chats": set(),
            }
        )

        for item in activity_data:
            if item["chat_id"] and item["agent_name"]:
                agent_name = item["agent_name"]
                agent_stats[agent_name]["total_chats"].add(item["chat_id"])

        for item in activity_data:
            if item["chat_id"] and item["agent_name"]:
                agent_name = item["agent_name"]
                rounds = chat_to_rounds.get(item["chat_id"], 0)
                if rounds > 0:
                    agent_stats[agent_name]["users"].add(item["user_id"])
                    agent_stats[agent_name]["rounds"] += rounds
                    agent_stats[agent_name]["sessions"].append(rounds)

        result = []
        for agent_name, stats in agent_stats.items():
            user_count = len(stats["users"])
            total_rounds = stats["rounds"]
            sessions = stats["sessions"]
            active_sessions = len(sessions)
            total_sessions = len(stats["total_chats"])

            avg_rounds_per_user = total_rounds / user_count if user_count > 0 else 0.0
            sessions_ge_5 = sum(1 for r in sessions if r >= 5)
            sessions_ge_10 = sum(1 for r in sessions if r >= 10)
            pct_sessions_ge_5 = (
                (sessions_ge_5 / active_sessions * 100) if active_sessions > 0 else 0.0
            )
            pct_sessions_ge_10 = (
                (sessions_ge_10 / active_sessions * 100) if active_sessions > 0 else 0.0
            )
            open_rate = (
                (active_sessions / total_sessions * 100) if total_sessions > 0 else 0.0
            )

            result.append(
                {
                    "agent_name": agent_name,
                    "user_count": user_count,
                    "total_rounds": total_rounds,
                    "avg_rounds_per_user": round(avg_rounds_per_user, 2),
                    "pct_sessions_ge_5": round(pct_sessions_ge_5, 2),
                    "pct_sessions_ge_10": round(pct_sessions_ge_10, 2),
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "open_rate": round(open_rate, 2),
                }
            )

        result.sort(key=lambda x: x["user_count"], reverse=True)
        return result[:limit]

    async def get_voice_usage(self, chat_ids: List[str]) -> List[Dict[str, Any]]:
        """查询语音使用统计"""
        if not chat_ids:
            return []

        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if not session_ids:
            return []

        session_to_voice_count = await self._query_session_voice_counts(session_ids)

        data = []
        for chat_id, session_id in chat_to_session.items():
            voice_count = session_to_voice_count.get(session_id, 0)
            if voice_count > 0:
                data.append({"chat_id": chat_id, "voice_message_count": voice_count})

        return data

    async def _query_session_voice_counts(
        self, session_ids: List[str]
    ) -> Dict[str, int]:
        """分批查询 session 的语音消息数

        返回: {session_id: voice_message_count}
        """
        if not session_ids:
            return {}

        session_to_voice_count: Dict[str, int] = {}

        for batch in _batch_list(session_ids, self._batch_size):
            placeholders = ",".join([f":session_id_{i}" for i in range(len(batch))])
            query = text(f"""
                SELECT 
                    ch.session_id::text as session_id,
                    COUNT(*) FILTER (
                        WHERE ch.audio_url IS NOT NULL 
                        AND (
                            ch.meta_data IS NULL 
                            OR ch.meta_data->>'isOpening' IS NULL 
                            OR ch.meta_data->>'isOpening' != 'true'
                        )
                    ) as voice_message_count
                FROM chat_history ch
                WHERE ch.session_id::text IN ({placeholders})
                GROUP BY ch.session_id
            """)
            params = {f"session_id_{i}": sid for i, sid in enumerate(batch)}
            result = await self.db.execute(query, params)

            for row in result.fetchall():
                session_to_voice_count[row[0]] = row[1]

        return session_to_voice_count

    async def get_analytics_stats(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
        active_session_ids: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """计算统计数据

        参数:
            register_start_date/register_end_date: 用户注册日期范围
            activity_start_date/activity_end_date: 活跃日期范围（用于生图统计等）
            active_session_ids: 若提供，仅统计这些 session，用于日报缩小范围
        """
        # 生图统计使用活跃日期范围，如果未提供则使用注册日期范围
        img_start = activity_start_date or register_start_date
        img_end = activity_end_date or register_end_date

        # 1. 获取用户数
        new_users_data = await self.get_new_users(
            register_start_date, register_end_date
        )
        total_new_users = sum(item["count"] for item in new_users_data)

        # 2. 获取用户会话详情
        sessions_detail = await self.get_user_sessions_detail(
            register_start_date,
            register_end_date,
            activity_start_date,
            activity_end_date,
            active_session_ids=active_session_ids,
        )

        # 辅助函数：查询语音通话（Live Chat）统计
        # 只统计指定注册日期范围内新用户在指定活跃日期范围内的通话数据
        async def get_live_chat_stats() -> Dict[str, Any]:
            live_chat_query = text("""
                SELECT 
                    COUNT(DISTINCT su.user_id) as user_count,
                    COUNT(*) as session_count,
                    COALESCE(
                        SUM((su.extra_data->>'duration_seconds')::int), 0
                    ) as total_duration
                FROM subscription_usage su
                INNER JOIN users u ON su.user_id = u.id
                WHERE su.usage_type = 'live_chat'
                  AND su.usage_date >= :activity_start_date 
                  AND su.usage_date < :activity_end_date
                  AND u.created_at >= :register_start_date
                  AND u.created_at < :register_end_date
                  AND u.deleted_at IS NULL
            """)
            live_chat_result = await self.db.execute(
                live_chat_query,
                {
                    "activity_start_date": img_start,
                    "activity_end_date": img_end,
                    "register_start_date": register_start_date,
                    "register_end_date": register_end_date,
                },
            )
            live_chat_row = live_chat_result.fetchone()
            user_count = live_chat_row[0] if live_chat_row else 0
            session_count = live_chat_row[1] if live_chat_row else 0
            total_duration = live_chat_row[2] if live_chat_row else 0
            avg_sessions_per_user = (
                session_count / user_count if user_count > 0 else 0.0
            )
            avg_duration_per_user = (
                total_duration / user_count if user_count > 0 else 0.0
            )
            avg_duration_per_session = (
                total_duration / session_count if session_count > 0 else 0.0
            )
            return {
                "total_live_chat_users": user_count,
                "total_live_chat_sessions": session_count,
                "total_live_chat_duration": total_duration,
                "avg_live_chat_sessions_per_user": round(avg_sessions_per_user, 2),
                "avg_live_chat_duration_per_user": round(avg_duration_per_user, 2),
                "avg_live_chat_duration_per_session": round(
                    avg_duration_per_session, 2
                ),
            }

        # 辅助函数：查询生图统计
        async def get_image_gen_stats() -> Dict[str, Any]:
            image_gen_query = text("""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                    COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures,
                    COUNT(*) FILTER (
                        WHERE extra_data->>'success' = 'true' 
                        AND (extra_data->>'is_matched' IS NULL 
                             OR extra_data->>'is_matched' = 'false')
                    ) as new_generation,
                    COUNT(*) FILTER (
                        WHERE extra_data->>'success' = 'true' 
                        AND extra_data->>'is_matched' = 'true'
                    ) as fallback_used
                FROM subscription_usage
                WHERE usage_type = 'image_generation'
                  AND usage_date >= :start_date 
                  AND usage_date < :end_date
            """)
            image_gen_result = await self.db.execute(
                image_gen_query, {"start_date": img_start, "end_date": img_end}
            )
            image_gen_row = image_gen_result.fetchone()
            total_requests = image_gen_row[0] if image_gen_row else 0
            total_success = image_gen_row[1] if image_gen_row else 0
            total_failures = image_gen_row[2] if image_gen_row else 0
            new_generation = image_gen_row[3] if image_gen_row else 0
            fallback_used = image_gen_row[4] if image_gen_row else 0
            success_rate = (
                (total_success / total_requests * 100) if total_requests > 0 else 0.0
            )
            return {
                "total_image_generation_requests": total_requests,
                "total_image_generation_success": total_success,
                "total_image_generation_failures": total_failures,
                "image_generation_success_rate": round(success_rate, 2),
                "total_image_new_generation": new_generation,
                "total_image_fallback_used": fallback_used,
            }

        if not sessions_detail:
            new_user_open_rate = 0.0
            img_stats = await get_image_gen_stats()
            live_chat_stats = await get_live_chat_stats()
            return {
                "total_new_users": total_new_users,
                "total_chat_initiators": 0,
                "total_user_messages": 0,
                "total_ai_messages": 0,
                "total_active_sessions": 0,
                "total_voice_requests": 0,
                "avg_messages_per_user": 0.0,
                "avg_sessions_per_user": 0.0,
                "avg_voice_requests_per_user": 0.0,
                "avg_rounds_per_session": 0.0,
                "new_user_open_rate": round(new_user_open_rate, 2),
                **img_stats,
                **live_chat_stats,
            }

        # 3. 获取有用户消息的会话（排除仅浏览开场白的）
        active_chat_ids = [
            item["chat_id"] for item in sessions_detail if item["message_count"] > 0
        ]
        active_sessions = [
            item for item in sessions_detail if item["chat_id"] in active_chat_ids
        ]

        if not active_sessions:
            new_user_open_rate = 0.0
            img_stats = await get_image_gen_stats()
            live_chat_stats = await get_live_chat_stats()
            return {
                "total_new_users": total_new_users,
                "total_chat_initiators": 0,
                "total_user_messages": 0,
                "total_ai_messages": 0,
                "total_active_sessions": 0,
                "total_voice_requests": 0,
                "avg_messages_per_user": 0.0,
                "avg_sessions_per_user": 0.0,
                "avg_voice_requests_per_user": 0.0,
                "avg_rounds_per_session": 0.0,
                "new_user_open_rate": round(new_user_open_rate, 2),
                **img_stats,
                **live_chat_stats,
            }

        # 4. 计算统计指标
        total_active_sessions = len(active_sessions)
        total_active_users = len(set(item["user_id"] for item in active_sessions))
        total_user_messages = sum(item["message_count"] for item in active_sessions)
        total_ai_messages = sum(item["ai_message_count"] for item in active_sessions)
        total_voice_requests = sum(
            item["voice_message_count"] for item in active_sessions
        )

        # 5. 计算平均值
        avg_messages_per_user = (
            total_user_messages / total_active_users if total_active_users > 0 else 0.0
        )
        avg_sessions_per_user = (
            total_active_sessions / total_active_users
            if total_active_users > 0
            else 0.0
        )
        avg_voice_requests_per_user = (
            total_voice_requests / total_active_users if total_active_users > 0 else 0.0
        )
        avg_rounds_per_session = (
            total_user_messages / total_active_sessions
            if total_active_sessions > 0
            else 0.0
        )

        # 计算开口率
        new_user_open_rate = (
            (total_active_users / total_new_users * 100) if total_new_users > 0 else 0.0
        )

        # 6. 查询生图统计
        img_stats = await get_image_gen_stats()

        # 7. 查询语音通话统计
        live_chat_stats = await get_live_chat_stats()

        return {
            "total_new_users": total_new_users,
            "total_chat_initiators": total_active_users,
            "total_user_messages": total_user_messages,
            "total_ai_messages": total_ai_messages,
            "total_active_sessions": total_active_sessions,
            "total_voice_requests": total_voice_requests,
            "avg_messages_per_user": round(avg_messages_per_user, 2),
            "avg_sessions_per_user": round(avg_sessions_per_user, 2),
            "avg_voice_requests_per_user": round(avg_voice_requests_per_user, 2),
            "avg_rounds_per_session": round(avg_rounds_per_session, 2),
            "new_user_open_rate": round(new_user_open_rate, 2),
            **img_stats,
            **live_chat_stats,
        }

    async def get_chat_messages(
        self,
        chat_ids: List[str],
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """查询聊天会话的具体消息"""
        if not chat_ids:
            return []

        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if not session_ids:
            return []

        session_to_chat = {v: k for k, v in chat_to_session.items()}
        data = []

        for batch in _batch_list(session_ids, self._batch_size):
            placeholders = ",".join([f":session_id_{i}" for i in range(len(batch))])
            if activity_start_date and activity_end_date:
                query = text(f"""
                    SELECT
                        ch.session_id::text as session_id,
                        ch.message->>'type' as message_type,
                        COALESCE(
                            ch.message->'data'->>'content',
                            ch.message->>'content'
                        ) as content,
                        ch.created_at,
                        ch.audio_url
                    FROM chat_history ch
                    WHERE ch.session_id::text IN ({placeholders})
                      AND ch.created_at >= :activity_start_date
                      AND ch.created_at < :activity_end_date
                    ORDER BY ch.created_at
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(batch)}
                params["activity_start_date"] = activity_start_date
                params["activity_end_date"] = activity_end_date
            else:
                query = text(f"""
                    SELECT
                        ch.session_id::text as session_id,
                        ch.message->>'type' as message_type,
                        COALESCE(
                            ch.message->'data'->>'content',
                            ch.message->>'content'
                        ) as content,
                        ch.created_at,
                        ch.audio_url
                    FROM chat_history ch
                    WHERE ch.session_id::text IN ({placeholders})
                    ORDER BY ch.created_at
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(batch)}
            result = await self.db.execute(query, params)

            for row in result.fetchall():
                session_id = row[0]
                chat_id = session_to_chat.get(session_id)
                if chat_id:
                    data.append(
                        {
                            "chat_id": chat_id,
                            "message_type": row[1],
                            "content": row[2],
                            "created_at": row[3].isoformat() if row[3] else None,
                            "audio_url": row[4],
                        }
                    )

        return data

    async def get_paginated_user_agent_conversations_detail(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
        page: int = 1,
        size: int = 10,
    ) -> Dict[str, Any]:
        """按 user_id + agent_id 分组返回会话与消息详情（分页）"""
        active_session_ids: Optional[Set[str]] = None
        if activity_start_date and activity_end_date:
            # When querying by activity date range, pre-filter to active sessions first.
            # This avoids loading all historical chats for all users.
            active_session_ids = await self.get_active_session_ids_on_date(
                activity_start_date, activity_end_date
            )
            if not active_session_ids:
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "size": size,
                    "has_more": False,
                }

        sessions_detail = await self.get_user_sessions_detail(
            register_start_date,
            register_end_date,
            activity_start_date,
            activity_end_date,
            active_session_ids=active_session_ids,
        )
        if not sessions_detail:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "size": size,
                "has_more": False,
            }

        grouped: Dict[tuple[str, str], Dict[str, Any]] = {}
        for item in sessions_detail:
            user_id = item["user_id"]
            agent_id = item["agent_id"]
            grouping_key = (user_id, agent_id)
            if grouping_key not in grouped:
                grouped[grouping_key] = {
                    "user_id": user_id,
                    "auth_type": item["auth_type"],
                    "user_created_at": item["user_created_at"],
                    "nickname": item["nickname"],
                    "email": item["email"],
                    "agent_id": agent_id,
                    "agent_name": item["agent_name"],
                    "session_count": 0,
                    "message_count": 0,
                    "voice_message_count": 0,
                    "sessions": [],
                }

            grouped_item = grouped[grouping_key]
            grouped_item["session_count"] += 1
            grouped_item["voice_message_count"] += item["voice_message_count"]
            grouped_item["sessions"].append(
                {
                    "chat_id": item["chat_id"],
                    "message_count": item["message_count"],
                    "voice_message_count": item["voice_message_count"],
                    "messages": [],
                }
            )

        sorted_group_keys = sorted(grouped.keys(), key=lambda key: (key[0], key[1]))
        grouped_items = [grouped[key] for key in sorted_group_keys]

        total = len(grouped_items)
        offset = (page - 1) * size
        paged_items = grouped_items[offset : offset + size]
        if not paged_items:
            return {
                "items": [],
                "total": total,
                "page": page,
                "size": size,
                "has_more": False,
            }

        chat_ids: List[str] = []
        for item in paged_items:
            chat_ids.extend([session["chat_id"] for session in item["sessions"]])

        messages = await self.get_chat_messages(
            chat_ids, activity_start_date, activity_end_date
        )
        chat_to_messages: Dict[str, List[Dict[str, Any]]] = {}
        for message in messages:
            chat_id = message["chat_id"]
            if chat_id not in chat_to_messages:
                chat_to_messages[chat_id] = []
            chat_to_messages[chat_id].append(message)

        for grouped_item in paged_items:
            all_messages_count = 0
            for session in grouped_item["sessions"]:
                session_messages = chat_to_messages.get(session["chat_id"], [])
                session["messages"] = session_messages
                all_messages_count += len(session_messages)
            grouped_item["message_count"] = all_messages_count

        return {
            "items": paged_items,
            "total": total,
            "page": page,
            "size": size,
            "has_more": offset + size < total,
        }

    async def _get_users_hitting_chat_limit_single_day(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
        guest_limit: int,
        google_limit: int,
    ) -> List[Dict[str, Any]]:
        """单日「达到聊天限制用户」查询，供 get_users_hitting_chat_limit 按天调用以减轻周报单次查询压力。"""
        from datetime import timedelta

        query_start_date = activity_start_date - timedelta(hours=24)
        end_date_minus_one_day = activity_end_date - timedelta(days=1)
        start_date_str = activity_start_date.date().isoformat()
        end_date_minus_one_day_str = end_date_minus_one_day.date().isoformat()

        check_query = text("""
            SELECT COUNT(*) as count
            FROM subscription_usage
            WHERE usage_type = 'chat'
              AND usage_date >= :query_start_date
              AND usage_date < :activity_end_date
        """)
        check_result = await self.db.execute(
            check_query,
            {
                "query_start_date": query_start_date,
                "activity_end_date": activity_end_date,
            },
        )
        usage_count = check_result.scalar() or 0
        if usage_count == 0:
            return []

        query = text(f"""
            WITH date_series AS (
                SELECT generate_series(
                    '{start_date_str}'::date,
                    '{end_date_minus_one_day_str}'::date,
                    interval '1 day'
                )::date as check_date
            ),
            active_users AS (
                SELECT DISTINCT su.user_id
                FROM subscription_usage su
                WHERE su.usage_type = 'chat'
                  AND su.usage_date >= :query_start_date
                  AND su.usage_date < :activity_end_date
            ),
            user_usage AS (
                SELECT 
                    ds.check_date,
                    u.id as user_id,
                    u.auth_type,
                    u.nickname,
                    u.email,
                    COALESCE(SUM(su.usage_count), 0) as chat_count_24h,
                    CASE 
                        WHEN u.auth_type = 'GUEST' THEN {guest_limit}
                        ELSE {google_limit}
                    END as limit_value
                FROM date_series ds
                CROSS JOIN active_users au
                INNER JOIN users u ON u.id = au.user_id AND u.deleted_at IS NULL
                LEFT JOIN subscription_usage su ON (
                    su.user_id = u.id
                    AND su.usage_type = 'chat'
                    AND su.usage_date >= (ds.check_date::timestamp AT TIME ZONE 'UTC' - interval '24 hours')
                    AND su.usage_date < (ds.check_date::timestamp AT TIME ZONE 'UTC' + interval '1 day')
                )
                GROUP BY ds.check_date, u.id, u.auth_type, u.nickname, u.email
            )
            SELECT 
                check_date as date,
                user_id,
                auth_type,
                nickname,
                email,
                chat_count_24h,
                limit_value
            FROM user_usage
            WHERE chat_count_24h >= limit_value
            ORDER BY check_date, user_id
        """)
        result = await self.db.execute(
            query,
            {
                "activity_end_date": activity_end_date,
                "query_start_date": query_start_date,
            },
        )
        rows = result.fetchall()
        return [
            {
                "date": (
                    row[0].isoformat() if isinstance(row[0], datetime) else str(row[0])
                ),
                "user_id": row[1],
                "auth_type": row[2],
                "nickname": row[3],
                "email": row[4],
                "chat_count_24h": row[5],
                "limit_value": row[6],
            }
            for row in rows
        ]

    async def get_users_hitting_chat_limit(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
        guest_limit: Optional[int] = None,
        google_limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询按日统计达到聊天限制的用户（使用活跃日期范围）。

        多日范围（如周报）时按天分别查询再合并，避免单条大 SQL 超时。
        """
        from datetime import timedelta

        if guest_limit is None:
            guest_limit = (
                global_config_loaded_from_config_yaml.app.limits.guest_user_chat_24h_limit
            )
        if google_limit is None:
            google_limit = (
                global_config_loaded_from_config_yaml.app.limits.free_user_chat_24h_limit
            )

        range_days = (activity_end_date - activity_start_date).days
        if range_days <= 1:
            try:
                return await self._get_users_hitting_chat_limit_single_day(
                    activity_start_date,
                    activity_end_date,
                    guest_limit,
                    google_limit,
                )
            except Exception:
                logger.exception(
                    "查询达到限制的用户失败: activity_start_date=%s, activity_end_date=%s",
                    activity_start_date,
                    activity_end_date,
                )
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                return []

        all_results: List[Dict[str, Any]] = []
        for i in range(range_days):
            day_start = activity_start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            try:
                day_results = await self._get_users_hitting_chat_limit_single_day(
                    day_start, day_end, guest_limit, google_limit
                )
                all_results.extend(day_results)
            except Exception:
                logger.exception(
                    "查询达到限制的用户失败（单日）: day_start=%s, day_end=%s",
                    day_start,
                    day_end,
                )
                try:
                    await self.db.rollback()
                except Exception:
                    pass
        return all_results

    async def get_agent_analytics(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """查询角色数据分析统计

        参数:
            register_start_date/register_end_date: 用户注册日期范围，筛选用户
            activity_start_date/activity_end_date: 活跃日期范围，筛选消息时间
        """
        chats_query = text("""
            SELECT
                c.id as chat_id,
                c.agent_id,
                a.name as agent_name,
                c.user_id
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id
            INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE u.created_at >= :register_start_date 
              AND u.created_at < :register_end_date
              AND u.deleted_at IS NULL
              AND c.is_active = true
        """)
        result = await self.db.execute(
            chats_query,
            {
                "register_start_date": register_start_date,
                "register_end_date": register_end_date,
            },
        )
        chat_records = result.fetchall()

        if not chat_records:
            return []

        chat_to_info = {}
        for row in chat_records:
            chat_id = row[0]
            agent_id = row[1]
            agent_name = row[2]
            user_id = row[3]
            chat_to_info[chat_id] = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "user_id": user_id,
            }

        chat_ids = list(chat_to_info.keys())
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if not session_ids:
            return []

        session_to_user_msg_count = await self._query_session_user_message_counts(
            session_ids, activity_start_date, activity_end_date
        )

        agent_stats = {}
        for chat_id, session_id in chat_to_session.items():
            info = chat_to_info[chat_id]
            agent_id = info["agent_id"]
            agent_name = info["agent_name"]
            user_id = info["user_id"]

            user_msg_count = session_to_user_msg_count.get(session_id, 0)

            if agent_id not in agent_stats:
                agent_stats[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "chat_user_ids": set(),
                    "total_sessions": 0,
                    "total_rounds": 0,
                    "sessions_ge_5_rounds": 0,
                    "sessions_ge_10_rounds": 0,
                }

            if user_msg_count > 0:
                agent_stats[agent_id]["chat_user_ids"].add(user_id)
                agent_stats[agent_id]["total_sessions"] += 1
                agent_stats[agent_id]["total_rounds"] += user_msg_count
                if user_msg_count >= 5:
                    agent_stats[agent_id]["sessions_ge_5_rounds"] += 1
                if user_msg_count >= 10:
                    agent_stats[agent_id]["sessions_ge_10_rounds"] += 1

        result_data = []
        for agent_id, stats in agent_stats.items():
            chat_user_count = len(stats["chat_user_ids"])
            total_sessions = stats["total_sessions"]
            avg_rounds_per_user = (
                round(stats["total_rounds"] / chat_user_count, 4)
                if chat_user_count > 0
                else 0
            )
            ge_5_rounds_ratio = (
                stats["sessions_ge_5_rounds"] / total_sessions
                if total_sessions > 0
                else 0
            )
            ge_10_rounds_ratio = (
                stats["sessions_ge_10_rounds"] / total_sessions
                if total_sessions > 0
                else 0
            )

            result_data.append(
                {
                    "agent_id": agent_id,
                    "agent_name": stats["agent_name"],
                    "chat_user_count": chat_user_count,
                    "total_sessions": total_sessions,
                    "total_rounds": stats["total_rounds"],
                    "avg_rounds_per_user": avg_rounds_per_user,
                    "sessions_ge_5_rounds": stats["sessions_ge_5_rounds"],
                    "sessions_ge_10_rounds": stats["sessions_ge_10_rounds"],
                    "ge_5_rounds_ratio": round(ge_5_rounds_ratio * 100, 2),
                    "ge_10_rounds_ratio": round(ge_10_rounds_ratio * 100, 2),
                }
            )

        return result_data

    async def get_user_sessions_detail(
        self,
        register_start_date: datetime,
        register_end_date: datetime,
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
        active_session_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """查询用户会话详情（聚合数据）

        参数:
            register_start_date/register_end_date: 用户注册日期范围，筛选用户
            activity_start_date/activity_end_date: 活跃日期范围，筛选消息时间
            active_session_ids: 若提供，仅统计这些 session，用于日报缩小范围
        """
        chats_query = text("""
            SELECT
                u.id as user_id,
                u.auth_type,
                u.created_at as user_created_at,
                u.nickname,
                u.email,
                c.id as chat_id,
                a.id as agent_id,
                a.name as agent_name
            FROM users u
            INNER JOIN chats c ON u.id = c.user_id AND c.is_active = true
            INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE u.created_at >= :register_start_date 
              AND u.created_at < :register_end_date
              AND u.deleted_at IS NULL
            ORDER BY u.id, c.created_at
        """)
        result = await self.db.execute(
            chats_query,
            {
                "register_start_date": register_start_date,
                "register_end_date": register_end_date,
            },
        )
        chat_records = result.fetchall()

        if not chat_records:
            return []

        chat_ids = [row[5] for row in chat_records]
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if active_session_ids is not None:
            chat_records = [
                row
                for row in chat_records
                if chat_to_session[row[5]] in active_session_ids
            ]
            session_ids = [s for s in session_ids if s in active_session_ids]
            chat_to_session = {
                cid: sid
                for cid, sid in chat_to_session.items()
                if sid in active_session_ids
            }

        if not session_ids:
            return []

        session_to_msg_count, session_to_voice_count, session_to_ai_msg_count = (
            await self._query_session_detail_counts(
                session_ids, activity_start_date, activity_end_date
            )
        )

        data = []
        for row in chat_records:
            chat_id = row[5]
            session_id = chat_to_session[chat_id]
            message_count = session_to_msg_count.get(session_id, 0)
            voice_count = session_to_voice_count.get(session_id, 0)
            ai_message_count = session_to_ai_msg_count.get(session_id, 0)

            data.append(
                {
                    "user_id": row[0],
                    "auth_type": row[1],
                    "user_created_at": row[2].isoformat() if row[2] else None,
                    "nickname": row[3],
                    "email": row[4],
                    "chat_id": chat_id,
                    "agent_id": row[6],
                    "agent_name": row[7],
                    "message_count": message_count,
                    "voice_message_count": voice_count,
                    "ai_message_count": ai_message_count,
                }
            )

        return data

    async def _query_session_detail_counts(
        self,
        session_ids: List[str],
        activity_start_date: Optional[datetime] = None,
        activity_end_date: Optional[datetime] = None,
    ) -> tuple[Dict[str, int], Dict[str, int], Dict[str, int]]:
        """分批查询 session 的用户消息数、语音消息数、AI 回复消息数

        返回: (session_to_msg_count, session_to_voice_count, session_to_ai_msg_count)
        """
        if not session_ids:
            return {}, {}, {}

        session_to_msg_count: Dict[str, int] = {}
        session_to_voice_count: Dict[str, int] = {}
        session_to_ai_msg_count: Dict[str, int] = {}

        for batch in _batch_list(session_ids, self._batch_size):
            uuid_batch = [uuid.UUID(sid) for sid in batch]
            placeholders = ",".join([f":session_id_{i}" for i in range(len(batch))])

            if activity_start_date and activity_end_date:
                messages_query = text(f"""
                    SELECT
                        ch.session_id as session_id,
                        COUNT(*) FILTER (
                            WHERE ch.message->>'type' = 'human'
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as user_message_count,
                        COUNT(*) FILTER (
                            WHERE ch.audio_url IS NOT NULL
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as voice_message_count,
                        COUNT(*) FILTER (
                            WHERE ch.message->>'type' = 'ai'
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as ai_message_count
                    FROM chat_history ch
                    WHERE ch.session_id IN ({placeholders})
                      AND ch.created_at >= :activity_start_date
                      AND ch.created_at < :activity_end_date
                    GROUP BY ch.session_id
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(uuid_batch)}
                params["activity_start_date"] = activity_start_date
                params["activity_end_date"] = activity_end_date
            else:
                messages_query = text(f"""
                    SELECT
                        ch.session_id as session_id,
                        COUNT(*) FILTER (
                            WHERE ch.message->>'type' = 'human'
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as user_message_count,
                        COUNT(*) FILTER (
                            WHERE ch.audio_url IS NOT NULL
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as voice_message_count,
                        COUNT(*) FILTER (
                            WHERE ch.message->>'type' = 'ai'
                            AND (
                                ch.meta_data IS NULL
                                OR ch.meta_data->>'isOpening' IS NULL
                                OR ch.meta_data->>'isOpening' != 'true'
                            )
                        ) as ai_message_count
                    FROM chat_history ch
                    WHERE ch.session_id IN ({placeholders})
                    GROUP BY ch.session_id
                """)
                params = {f"session_id_{i}": sid for i, sid in enumerate(uuid_batch)}

            result = await self.db.execute(messages_query, params)
            for row in result.fetchall():
                session_key = str(row[0])
                session_to_msg_count[session_key] = row[1]
                session_to_voice_count[session_key] = row[2]
                session_to_ai_msg_count[session_key] = row[3]

        return session_to_msg_count, session_to_voice_count, session_to_ai_msg_count

    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱查找用户"""
        query = text("""
            SELECT id, email, nickname, auth_type, created_at, gender, age_group
            FROM users
            WHERE email = :email AND deleted_at IS NULL
            LIMIT 1
        """)
        result = await self.db.execute(query, {"email": email})
        row = result.fetchone()
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "nickname": row[2],
                "auth_type": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "gender": row[5],
                "age_group": row[6],
            }
        return None

    async def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过用户 ID 查找用户"""
        query = text("""
            SELECT id, email, nickname, auth_type, created_at, gender, age_group
            FROM users
            WHERE id = :user_id AND deleted_at IS NULL
            LIMIT 1
        """)
        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "nickname": row[2],
                "auth_type": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "gender": row[5],
                "age_group": row[6],
            }
        return None

    async def get_user_chat_ids(self, user_id: str) -> List[str]:
        """获取用户的所有 chat_id"""
        query = text("""
            SELECT id
            FROM chats
            WHERE user_id = :user_id AND is_active = true
        """)
        result = await self.db.execute(query, {"user_id": user_id})
        return [row[0] for row in result.fetchall()]

    async def get_user_daily_messages(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """统计用户每日消息数"""
        chat_ids = await self.get_user_chat_ids(user_id)
        if not chat_ids:
            return []

        session_ids = [generate_session_id(chat_id) for chat_id in chat_ids]

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        query = f"""
            SELECT 
                DATE(ch.created_at AT TIME ZONE 'UTC') as date,
                COUNT(*) as message_count,
                COUNT(DISTINCT ch.session_id) as session_count
            FROM chat_history ch
            WHERE ch.session_id::text IN ({placeholders})
              AND ch.message->>'type' = 'human'
              AND (ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
        """

        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}

        if start_date:
            query += " AND ch.created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND ch.created_at < :end_date"
            params["end_date"] = end_date

        query += """
            GROUP BY DATE(ch.created_at AT TIME ZONE 'UTC')
            ORDER BY date
        """

        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        return [
            {
                "date": (
                    row[0].isoformat() if isinstance(row[0], datetime) else str(row[0])
                ),
                "message_count": row[1],
                "session_count": row[2],
            }
            for row in rows
        ]

    async def get_daily_messages_for_all_users(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """统计全量用户在日期范围内的每日消息数。"""
        query = text("""
            SELECT
                DATE(ch.created_at AT TIME ZONE 'UTC') as date,
                COUNT(*) as message_count,
                COUNT(DISTINCT ch.session_id) as session_count
            FROM chat_history ch
            WHERE ch.message->>'type' = 'human'
              AND (ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
              AND ch.created_at >= :start_date
              AND ch.created_at < :end_date
            GROUP BY DATE(ch.created_at AT TIME ZONE 'UTC')
            ORDER BY date
        """)
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }
        result = await self.db.execute(query, params)
        rows = result.fetchall()
        return [
            {
                "date": (
                    row[0].isoformat() if isinstance(row[0], datetime) else str(row[0])
                ),
                "message_count": row[1],
                "session_count": row[2],
            }
            for row in rows
        ]

    async def get_user_generated_images_count(self, user_id: str) -> int:
        """获取用户总的生图数"""
        try:
            from sqlalchemy import select

            from app.models.resource import Resource, ResourceType

            # 查询所有符合条件的资源
            query = select(Resource).where(
                Resource.user_id == user_id,
                Resource.type == ResourceType.IMAGE,
                Resource.resource_metadata.isnot(None),
            )
            result = await self.db.execute(query)
            resources = result.scalars().all()

            # 统计有 generation_prompt 的图片
            count = 0
            for resource in resources:
                metadata = resource.resource_metadata or {}
                if metadata.get("generation_prompt"):
                    count += 1

            return count
        except Exception as e:
            logger.warning(f"获取用户生图数失败: {str(e)}")
            return 0

    async def get_user_today_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户当日统计"""
        from datetime import timedelta

        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        today_end = today_start + timedelta(days=1)

        chat_ids = await self.get_user_chat_ids(user_id)
        if not chat_ids:
            total_generated_images = await self.get_user_generated_images_count(user_id)
            return {
                "today_message_count": 0,
                "today_session_count": 0,
                "total_generated_images": total_generated_images,
            }

        session_ids = [generate_session_id(chat_id) for chat_id in chat_ids]

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        query = text(f"""
            SELECT 
                COUNT(DISTINCT ch.session_id) as session_count,
                COUNT(*) FILTER (
                    WHERE ch.message->>'type' = 'human'
                    AND (ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
                ) as message_count
            FROM chat_history ch
            WHERE ch.session_id::text IN ({placeholders})
              AND ch.created_at >= :today_start
              AND ch.created_at < :today_end
        """)
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        params["today_start"] = today_start
        params["today_end"] = today_end

        result = await self.db.execute(query, params)
        row = result.fetchone()

        total_generated_images = await self.get_user_generated_images_count(user_id)

        return {
            "today_message_count": row[1] if row else 0,
            "today_session_count": row[0] if row else 0,
            "total_generated_images": total_generated_images,
        }

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有会话列表"""
        from app.services.image_transform_service import image_transform_service

        query = text("""
            SELECT 
                c.id as chat_id,
                a.name as agent_name,
                a.avatar as agent_avatar_url,
                c.created_at,
                c.updated_at
            FROM chats c
            INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE c.user_id = :user_id AND c.is_active = true
            ORDER BY c.created_at DESC
        """)
        result = await self.db.execute(query, {"user_id": user_id})
        chat_records = result.fetchall()

        if not chat_records:
            return []

        chat_ids = [row[0] for row in chat_records]
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        messages_query = text(f"""
            SELECT
                ch.session_id::text as session_id,
                COUNT(*) FILTER (
                    WHERE ch.message->>'type' = 'human'
                    AND (
                        ch.meta_data IS NULL
                        OR ch.meta_data->>'isOpening' IS NULL
                        OR ch.meta_data->>'isOpening' != 'true'
                    )
                ) as message_count,
                MAX(ch.created_at) FILTER (
                    WHERE ch.message->>'type' = 'human'
                    AND (
                        ch.meta_data IS NULL
                        OR ch.meta_data->>'isOpening' IS NULL
                        OR ch.meta_data->>'isOpening' != 'true'
                    )
                ) as last_user_message_time,
                MAX(ch.created_at) as last_message_time
            FROM chat_history ch
            WHERE ch.session_id::text IN ({placeholders})
            GROUP BY ch.session_id
        """)
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        result = await self.db.execute(messages_query, params)

        session_to_msg_count = {}
        session_to_last_user_message_time = {}
        session_to_last_message_time = {}
        for row in result.fetchall():
            session_id_str = row[0]
            session_to_msg_count[session_id_str] = row[1]
            if row[2]:  # last_user_message_time
                session_to_last_user_message_time[session_id_str] = row[2]
            if row[3]:  # last_message_time (any message, including AI)
                session_to_last_message_time[session_id_str] = row[3]

        data = []
        for row in chat_records:
            chat_id = row[0]
            session_id = chat_to_session[chat_id]
            message_count = session_to_msg_count.get(session_id, 0)
            # 优先使用最后一条用户消息时间，如果没有则使用最后一条消息时间（包括AI消息）
            last_user_message_time = session_to_last_user_message_time.get(session_id)
            last_message_time = session_to_last_message_time.get(session_id)
            updated_at = last_user_message_time or last_message_time
            agent_avatar_url = (
                image_transform_service.transform_desktop(row[2]) if row[2] else None
            )

            data.append(
                {
                    "chat_id": chat_id,
                    "agent_name": row[1],
                    "agent_avatar_url": agent_avatar_url,
                    "created_at": row[3].isoformat() if row[3] else None,
                    "updated_at": (updated_at.isoformat() if updated_at else None),
                    "message_count": message_count,
                }
            )

        return data

    async def get_session_messages(
        self, chat_id: str, page: int = 1, size: int = 50
    ) -> Dict[str, Any]:
        """获取指定会话的对话历史"""
        session_id = generate_session_id(chat_id)

        # 先获取总数（排除记忆提取型消息）
        count_query = text("""
            SELECT COUNT(*)
            FROM chat_history
            WHERE session_id::text = :session_id
              AND (meta_data->>'messageType' IS NULL OR (meta_data->>'messageType' != 'festival_memory_prompt' AND meta_data->>'messageType' != 'daily_memory_prompt'))
        """)
        count_result = await self.db.execute(count_query, {"session_id": session_id})
        total = count_result.scalar() or 0

        # 获取分页数据
        offset = (page - 1) * size
        query = text("""
            SELECT
                id,
                message->>'type' as message_type,
                COALESCE(
                    message->'data'->>'content',
                    message->>'content'
                ) as content,
                message->'data'->>'image_url' as image_url_from_message,
                created_at,
                audio_url,
                meta_data
            FROM chat_history
            WHERE session_id::text = :session_id
              AND (meta_data->>'messageType' IS NULL OR (meta_data->>'messageType' != 'festival_memory_prompt' AND meta_data->>'messageType' != 'daily_memory_prompt'))
            ORDER BY created_at ASC
            LIMIT :limit OFFSET :offset
        """)
        result = await self.db.execute(
            query,
            {"session_id": session_id, "limit": size, "offset": offset},
        )
        rows = result.fetchall()

        messages = []
        for row in rows:
            message_type = row[1] or "human"
            content = row[2] or ""
            image_url_from_message = row[3]  # 独立图片消息的 URL
            meta_data = row[6]  # 索引从 0 开始，所以 meta_data 是第 7 个字段（索引 6）

            # 处理图片 URL 转换
            try:
                from app.services.image_transform_service import image_transform_service

                # 处理独立图片消息（type="image"）
                if message_type == "image" and image_url_from_message:
                    image_url_from_message = image_transform_service.transform_desktop(
                        image_url_from_message
                    )

                # 处理 meta_data 中的 generated_image（文本消息中包含的生成图片）
                if (
                    meta_data
                    and isinstance(meta_data, dict)
                    and "generated_image" in meta_data
                ):
                    generated_image = meta_data["generated_image"]
                    image_url = generated_image.get("image_url")

                    if image_url:
                        # 转换 GCS URI 为 CDN URL
                        cdn_url = image_transform_service.transform_desktop(image_url)

                        # 更新 meta_data 中的图片 URL
                        meta_data = dict(meta_data)  # 创建副本避免修改原始数据
                        meta_data["generated_image"] = {
                            "image_url": cdn_url,
                            "width": generated_image.get("width"),
                            "height": generated_image.get("height"),
                            "format": generated_image.get("format"),
                        }
            except Exception as e:
                logger.warning(f"转换图片 URL 失败: {str(e)}")
                # 如果转换失败，保留原始数据

            messages.append(
                {
                    "id": row[0],
                    "message_type": message_type,
                    "content": content,
                    "image_url": image_url_from_message,  # 独立图片消息的 URL
                    "created_at": row[4].isoformat() if row[4] else None,
                    "audio_url": row[5],
                    "meta_data": meta_data,
                }
            )

        return {
            "messages": messages,
            "total": total,
            "page": page,
            "size": size,
            "has_more": offset + len(messages) < total,
        }

    async def get_llm_latency_trend(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """按小时聚合 LLM 调用延迟"""
        query = text("""
            SELECT 
                DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC') as hour,
                AVG((meta_data->>'llm_invoke_time')::float) as avg_latency,
                COUNT(*) as count
            FROM chat_history
            WHERE created_at >= :start_date 
              AND created_at < :end_date
              AND meta_data->>'llm_invoke_time' IS NOT NULL
              AND deleted_at IS NULL
              AND (meta_data->>'messageType' IS NULL OR (meta_data->>'messageType' != 'festival_memory_prompt' AND meta_data->>'messageType' != 'daily_memory_prompt'))
            GROUP BY DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC')
            ORDER BY hour
        """)
        result = await self.db.execute(
            query,
            {
                "start_date": activity_start_date,
                "end_date": activity_end_date,
            },
        )
        rows = result.fetchall()
        return [
            {
                "hour": row[0].strftime("%Y-%m-%d %H:00") if row[0] else None,
                "avg_latency": round(row[1], 3) if row[1] else 0.0,
                "count": row[2] or 0,
            }
            for row in rows
        ]

    async def get_image_generation_latency_trend(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """按小时和模型聚合生图耗时"""
        query = text("""
            SELECT 
                DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC') as hour,
                extra_data->>'model' as model,
                AVG((extra_data->>'generation_time_ms')::float) as avg_latency_ms,
                COUNT(*) as count
            FROM subscription_usage
            WHERE created_at >= :start_date 
              AND created_at < :end_date
              AND usage_type = 'image_generation'
              AND extra_data->>'success' = 'true'
              AND extra_data->>'generation_time_ms' IS NOT NULL
              AND extra_data->>'model' IS NOT NULL
            GROUP BY DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC'), extra_data->>'model'
            ORDER BY hour, model
        """)
        result = await self.db.execute(
            query,
            {
                "start_date": activity_start_date,
                "end_date": activity_end_date,
            },
        )
        rows = result.fetchall()
        return [
            {
                "hour": row[0].strftime("%Y-%m-%d %H:00") if row[0] else None,
                "model": row[1] or "unknown",
                "avg_latency_ms": round(row[2], 1) if row[2] else 0.0,
                "count": row[3] or 0,
            }
            for row in rows
        ]

    async def get_live_chat_latency_trend(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """按小时聚合 Live Chat 延迟数据"""
        query = text("""
            SELECT 
                DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC') as hour,
                AVG((extra_data->'latency_metrics'->>'connect_latency_ms')::float) as avg_connect_latency,
                AVG((extra_data->'latency_metrics'->>'first_response_after_silence_ms')::float) as avg_first_response_after_silence,
                AVG((extra_data->'latency_metrics'->>'avg_turn_latency_ms')::float) as avg_turn_latency,
                COUNT(*) as count
            FROM subscription_usage
            WHERE created_at >= :start_date 
              AND created_at < :end_date
              AND usage_type = 'live_chat'
              AND extra_data->'latency_metrics' IS NOT NULL
            GROUP BY DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC')
            ORDER BY hour
        """)
        result = await self.db.execute(
            query,
            {
                "start_date": activity_start_date,
                "end_date": activity_end_date,
            },
        )
        rows = result.fetchall()
        return [
            {
                "hour": row[0].strftime("%Y-%m-%d %H:00") if row[0] else None,
                "avg_connect_latency": round(row[1], 1) if row[1] else None,
                "avg_first_response_after_silence": (
                    round(row[2], 1) if row[2] else None
                ),
                "avg_turn_latency": round(row[3], 1) if row[3] else None,
                "count": row[4] or 0,
            }
            for row in rows
        ]

    async def get_live_chat_basic_stats(
        self,
        activity_start_date: datetime,
        activity_end_date: datetime,
    ) -> Dict[str, Any]:
        """获取 Live Chat 基础统计"""
        query = text("""
            SELECT 
                COUNT(DISTINCT user_id) as user_count,
                COUNT(*) as session_count,
                COALESCE(SUM((extra_data->>'duration_seconds')::int), 0) as total_duration
            FROM subscription_usage
            WHERE created_at >= :start_date 
              AND created_at < :end_date
              AND usage_type = 'live_chat'
        """)
        result = await self.db.execute(
            query,
            {
                "start_date": activity_start_date,
                "end_date": activity_end_date,
            },
        )
        row = result.fetchone()

        user_count = row[0] if row else 0
        session_count = row[1] if row else 0
        total_duration = row[2] if row else 0

        avg_sessions_per_user = (
            round(session_count / user_count, 2) if user_count > 0 else 0.0
        )
        avg_duration_per_user = (
            round(total_duration / user_count, 2) if user_count > 0 else 0.0
        )
        avg_duration_per_session = (
            round(total_duration / session_count, 2) if session_count > 0 else 0.0
        )

        return {
            "total_users": user_count,
            "total_sessions": session_count,
            "total_duration": total_duration,
            "avg_sessions_per_user": avg_sessions_per_user,
            "avg_duration_per_user": avg_duration_per_user,
            "avg_duration_per_session": avg_duration_per_session,
        }

    async def get_image_generation_failure_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        top_n_reasons: int = 20,
    ) -> Dict[str, Any]:
        """
        生图失败与兜底分析（只读，适合在 replica 上执行）。
        返回：summary、fallback_stats、failures_by_type、failures_by_reason、
        daily_trend、failures_by_agent。
        """
        # 1) 总体 + 兜底
        summary_query = text("""
            SELECT
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures,
                COUNT(*) FILTER (WHERE extra_data->>'success' IS NULL OR extra_data->>'success' = '') as unknown_status,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true' AND (extra_data->>'is_matched' IS NULL OR extra_data->>'is_matched' = 'false')) as new_generation,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true' AND extra_data->>'is_matched' = 'true') as fallback_used
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= :start_date
              AND usage_date < :end_date
        """)
        r = await self.db.execute(
            summary_query, {"start_date": start_date, "end_date": end_date}
        )
        row = r.fetchone()
        if not row:
            return _empty_image_failure_analytics()

        total_requests = row[0] or 0
        total_success = row[1] or 0
        total_failures = row[2] or 0
        unknown_status = row[3] or 0
        new_generation = row[4] or 0
        fallback_used = row[5] or 0
        success_rate = (
            (total_success / total_requests * 100) if total_requests > 0 else 0.0
        )
        fallback_ratio_success = (
            (fallback_used / total_success * 100) if total_success > 0 else 0.0
        )
        fallback_ratio_requests = (
            (fallback_used / total_requests * 100) if total_requests > 0 else 0.0
        )

        summary = {
            "total_requests": total_requests,
            "total_success": total_success,
            "total_failures": total_failures,
            "unknown_status": unknown_status,
            "success_rate": round(success_rate, 2),
            "failure_rate": (
                round((total_failures / total_requests * 100), 2)
                if total_requests > 0
                else 0.0
            ),
        }
        fallback_stats = {
            "new_generation": new_generation,
            "fallback_used": fallback_used,
            "fallback_ratio_of_success_pct": round(fallback_ratio_success, 2),
            "fallback_ratio_of_requests_pct": round(fallback_ratio_requests, 2),
        }

        # 2) 失败类型
        type_query = text("""
            SELECT extra_data->>'failure_type' as failure_type, COUNT(*) as count
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= :start_date AND usage_date < :end_date
              AND (extra_data->>'success' = 'false' OR extra_data->>'success' IS NULL)
            GROUP BY extra_data->>'failure_type'
            ORDER BY count DESC
        """)
        r = await self.db.execute(
            type_query, {"start_date": start_date, "end_date": end_date}
        )
        failures_by_type = [
            {"failure_type": (row[0] or "unknown"), "count": row[1]}
            for row in r.fetchall()
        ]

        # 3) 失败原因 Top N
        reason_query = text("""
            SELECT extra_data->>'failure_reason' as failure_reason,
                   extra_data->>'failure_type' as failure_type,
                   COUNT(*) as count
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= :start_date AND usage_date < :end_date
              AND (extra_data->>'success' = 'false' OR extra_data->>'success' IS NULL)
              AND extra_data->>'failure_reason' IS NOT NULL
            GROUP BY extra_data->>'failure_reason', extra_data->>'failure_type'
            ORDER BY count DESC
            LIMIT :top_n
        """)
        r = await self.db.execute(
            reason_query,
            {
                "start_date": start_date,
                "end_date": end_date,
                "top_n": top_n_reasons,
            },
        )
        failures_by_reason = [
            {
                "failure_reason": (row[0] or "")[:500],
                "failure_type": row[1] or "unknown",
                "count": row[2],
            }
            for row in r.fetchall()
        ]

        # 4) 按日趋势
        daily_query = text("""
            SELECT DATE(usage_date AT TIME ZONE 'UTC') as date,
                   COUNT(*) as total_requests,
                   COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                   COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures,
                   COUNT(*) FILTER (WHERE extra_data->>'success' = 'true' AND (extra_data->>'is_matched' IS NULL OR extra_data->>'is_matched' = 'false')) as new_generation,
                   COUNT(*) FILTER (WHERE extra_data->>'success' = 'true' AND extra_data->>'is_matched' = 'true') as fallback_used
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= :start_date AND usage_date < :end_date
            GROUP BY DATE(usage_date AT TIME ZONE 'UTC')
            ORDER BY date
        """)
        r = await self.db.execute(
            daily_query, {"start_date": start_date, "end_date": end_date}
        )
        daily_trend = []
        for row in r.fetchall():
            total = row[1] or 0
            daily_trend.append(
                {
                    "date": row[0].isoformat() if row[0] else None,
                    "total_requests": total,
                    "total_success": row[2] or 0,
                    "total_failures": row[3] or 0,
                    "new_generation": row[4] or 0,
                    "fallback_used": row[5] or 0,
                    "success_rate": (
                        round((row[2] or 0) / total * 100, 2) if total > 0 else 0.0
                    ),
                }
            )

        # 5) 按 Agent 失败率（请求数>=5）
        agent_query = text("""
            SELECT su.extra_data->>'agent_id' as agent_id,
                   a.name as agent_name,
                   COUNT(*) as total_requests,
                   COUNT(*) FILTER (WHERE su.extra_data->>'success' = 'true') as total_success,
                   COUNT(*) FILTER (WHERE su.extra_data->>'success' = 'false') as total_failures
            FROM subscription_usage su
            LEFT JOIN agents a ON su.extra_data->>'agent_id' = a.id::text
            WHERE su.usage_type = 'image_generation'
              AND su.usage_date >= :start_date AND su.usage_date < :end_date
              AND su.extra_data->>'agent_id' IS NOT NULL
            GROUP BY su.extra_data->>'agent_id', a.name
            HAVING COUNT(*) >= 5
            ORDER BY total_requests DESC
        """)
        r = await self.db.execute(
            agent_query, {"start_date": start_date, "end_date": end_date}
        )
        failures_by_agent = []
        for row in r.fetchall():
            total = row[2] or 0
            failures_by_agent.append(
                {
                    "agent_id": row[0],
                    "agent_name": row[1] or "Unknown",
                    "total_requests": total,
                    "total_success": row[3] or 0,
                    "total_failures": row[4] or 0,
                    "failure_rate": (
                        round((row[4] or 0) / total * 100, 2) if total > 0 else 0.0
                    ),
                }
            )

        return {
            "summary": summary,
            "fallback_stats": fallback_stats,
            "failures_by_type": failures_by_type,
            "failures_by_reason": failures_by_reason,
            "daily_trend": daily_trend,
            "failures_by_agent": failures_by_agent,
        }


def _empty_image_failure_analytics() -> Dict[str, Any]:
    """无数据时的生图失败分析空结构"""
    return {
        "summary": {
            "total_requests": 0,
            "total_success": 0,
            "total_failures": 0,
            "unknown_status": 0,
            "success_rate": 0.0,
            "failure_rate": 0.0,
        },
        "fallback_stats": {
            "new_generation": 0,
            "fallback_used": 0,
            "fallback_ratio_of_success_pct": 0.0,
            "fallback_ratio_of_requests_pct": 0.0,
        },
        "failures_by_type": [],
        "failures_by_reason": [],
        "daily_trend": [],
        "failures_by_agent": [],
    }
