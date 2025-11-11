"""用户数据分析服务 - 将脚本查询逻辑重构为异步服务"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml


def generate_session_id(chat_id: str) -> str:
    """生成 session_id，与 app/services/chat_service.py 中的逻辑一致"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


class UserAnalyticsService:
    """用户行为分析服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_new_users(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """查询新用户统计"""
        query = text(
            """
            SELECT 
                DATE(created_at AT TIME ZONE 'UTC') as date,
                auth_type,
                COUNT(*) as count
            FROM users
            WHERE created_at >= :start_date AND created_at < :end_date
              AND deleted_at IS NULL
            GROUP BY DATE(created_at AT TIME ZONE 'UTC'), auth_type
            ORDER BY date, auth_type
        """
        )
        result = await self.db.execute(
            query, {"start_date": start_date, "end_date": end_date}
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
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """查询用户聊天活动（原始数据，需要前端聚合）"""
        query = text(
            """
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
            WHERE u.created_at >= :start_date AND u.created_at < :end_date
              AND u.deleted_at IS NULL
            ORDER BY u.id, c.created_at
        """
        )
        result = await self.db.execute(
            query, {"start_date": start_date, "end_date": end_date}
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

    async def get_conversation_rounds(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """查询对话轮数统计（按Session）- 只统计新用户发起的会话

        与原始脚本逻辑一致：查询新用户的所有会话（不限制 chat 创建时间）
        因为新用户可能在注册后的任意时间创建会话
        """
        # 只统计新用户（在 start_date 到 end_date 之间注册的用户）的所有会话
        # 注意：不限制 chat 的创建时间，因为新用户可能在注册后任意时间创建会话
        chats_query = text(
            """
            SELECT c.id
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.created_at >= :start_date 
              AND u.created_at < :end_date
              AND u.deleted_at IS NULL
              AND c.is_active = true
        """
        )
        result = await self.db.execute(
            chats_query, {"start_date": start_date, "end_date": end_date}
        )
        chat_ids = [row[0] for row in result.fetchall()]

        logger.info(f"get_conversation_rounds: 找到 {len(chat_ids)} 个新用户的会话")

        if not chat_ids:
            logger.info("get_conversation_rounds: 没有找到新用户的会话")
            return []

        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if not session_ids:
            logger.info("get_conversation_rounds: 没有生成有效的 session_ids")
            return []

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        history_query = text(
            f"""
            SELECT 
                session_id::text as session_id,
                COUNT(*) as message_count,
                COUNT(*) FILTER (
                    WHERE meta_data->>'isOpening' != 'true' OR meta_data IS NULL
                ) as non_opening_count
            FROM chat_history
            WHERE session_id::text IN ({placeholders})
            GROUP BY session_id
        """
        )
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        result = await self.db.execute(history_query, params)

        session_to_count = {}
        session_to_non_opening_count = {}
        for row in result.fetchall():
            session_id_str = row[0]
            session_to_count[session_id_str] = row[1]
            session_to_non_opening_count[session_id_str] = row[2]

        data = []
        for chat_id, session_id in chat_to_session.items():
            if session_id in session_to_count:
                message_count_excluding_opening = session_to_non_opening_count.get(
                    session_id, session_to_count[session_id]
                )
                # 只返回有用户消息的会话（排除仅浏览开场白的会话）
                if message_count_excluding_opening > 0:
                    data.append(
                        {
                            "chat_id": chat_id,
                            "message_count": session_to_count[session_id],
                            "message_count_excluding_opening": message_count_excluding_opening,
                        }
                    )

        # 统计消息数分布
        message_counts = [d["message_count_excluding_opening"] for d in data]
        if message_counts:
            from collections import Counter

            count_distribution = Counter(message_counts)
            logger.info(
                f"get_conversation_rounds: 返回 {len(data)} 个有用户消息的会话（已排除仅开场白的会话），"
                f"消息数分布（前10个最常见的值）: {dict(count_distribution.most_common(10))}"
            )
        else:
            logger.info("get_conversation_rounds: 没有找到有用户消息的会话")

        return data

    async def get_user_rounds_distribution(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """查询对话轮数分布（按用户）"""
        chats_query = text(
            """
            SELECT
                c.user_id,
                c.id as chat_id
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.created_at >= :start_date AND u.created_at < :end_date
              AND u.deleted_at IS NULL
              AND c.is_active = true
        """
        )
        result = await self.db.execute(
            chats_query, {"start_date": start_date, "end_date": end_date}
        )
        chat_records = result.fetchall()

        if not chat_records:
            return []

        chat_ids = [row[1] for row in chat_records]
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if not session_ids:
            return []

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        messages_query = text(
            f"""
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
        """
        )
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        result = await self.db.execute(messages_query, params)

        session_to_user_msg_count = {row[0]: row[1] for row in result.fetchall()}

        user_to_total_rounds = {}
        for i, (user_id, chat_id) in enumerate(chat_records):
            session_id = chat_to_session[chat_id]
            user_msg_count = session_to_user_msg_count.get(session_id, 0)
            if user_id not in user_to_total_rounds:
                user_to_total_rounds[user_id] = 0
            user_to_total_rounds[user_id] += user_msg_count

        return [
            {"user_id": user_id, "total_rounds": total_rounds}
            for user_id, total_rounds in user_to_total_rounds.items()
        ]

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

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        query = text(
            f"""
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
        """
        )
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        result = await self.db.execute(query, params)

        session_to_voice_count = {row[0]: row[1] for row in result.fetchall()}

        data = []
        for chat_id, session_id in chat_to_session.items():
            voice_count = session_to_voice_count.get(session_id, 0)
            if voice_count > 0:
                data.append({"chat_id": chat_id, "voice_message_count": voice_count})

        return data

    async def get_analytics_stats(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """计算统计数据（与原始脚本逻辑一致）"""
        # 1. 获取新用户数
        new_users_data = await self.get_new_users(start_date, end_date)
        total_new_users = sum(item["count"] for item in new_users_data)

        # 2. 获取用户会话详情
        sessions_detail = await self.get_user_sessions_detail(start_date, end_date)
        if not sessions_detail:
            new_user_open_rate = (
                (0 / total_new_users * 100) if total_new_users > 0 else 0.0
            )
            # 查询生图统计（即使没有会话详情也要统计）
            image_gen_query = text("""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                    COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures
                FROM subscription_usage
                WHERE usage_type = 'image_generation'
                  AND usage_date >= :start_date 
                  AND usage_date < :end_date
            """)
            image_gen_result = await self.db.execute(
                image_gen_query, {"start_date": start_date, "end_date": end_date}
            )
            image_gen_row = image_gen_result.fetchone()
            
            total_image_generation_requests = image_gen_row[0] if image_gen_row else 0
            total_image_generation_success = image_gen_row[1] if image_gen_row else 0
            total_image_generation_failures = image_gen_row[2] if image_gen_row else 0
            
            image_generation_success_rate = (
                (total_image_generation_success / total_image_generation_requests * 100)
                if total_image_generation_requests > 0
                else 0.0
            )
            
            return {
                "total_new_users": total_new_users,
                "total_chat_initiators": 0,
                "total_user_messages": 0,
                "total_active_sessions": 0,
                "total_voice_requests": 0,
                "avg_messages_per_user": 0.0,
                "avg_sessions_per_user": 0.0,
                "avg_voice_requests_per_user": 0.0,
                "avg_rounds_per_session": 0.0,
                "new_user_open_rate": round(new_user_open_rate, 2),
                "total_image_generation_requests": total_image_generation_requests,
                "total_image_generation_success": total_image_generation_success,
                "total_image_generation_failures": total_image_generation_failures,
                "image_generation_success_rate": round(image_generation_success_rate, 2),
            }

        # 3. 获取有用户消息的会话（排除仅浏览开场白的）
        # message_count 已经在 get_user_sessions_detail 中统计了用户消息数（排除开场白）
        active_chat_ids = [
            item["chat_id"] for item in sessions_detail if item["message_count"] > 0
        ]
        active_sessions = [
            item for item in sessions_detail if item["chat_id"] in active_chat_ids
        ]

        if not active_sessions:
            new_user_open_rate = (
                (0 / total_new_users * 100) if total_new_users > 0 else 0.0
            )
            # 查询生图统计（即使没有活跃会话也要统计）
            image_gen_query = text("""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                    COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures
                FROM subscription_usage
                WHERE usage_type = 'image_generation'
                  AND usage_date >= :start_date 
                  AND usage_date < :end_date
            """)
            image_gen_result = await self.db.execute(
                image_gen_query, {"start_date": start_date, "end_date": end_date}
            )
            image_gen_row = image_gen_result.fetchone()
            
            total_image_generation_requests = image_gen_row[0] if image_gen_row else 0
            total_image_generation_success = image_gen_row[1] if image_gen_row else 0
            total_image_generation_failures = image_gen_row[2] if image_gen_row else 0
            
            image_generation_success_rate = (
                (total_image_generation_success / total_image_generation_requests * 100)
                if total_image_generation_requests > 0
                else 0.0
            )
            
            return {
                "total_new_users": total_new_users,
                "total_chat_initiators": 0,
                "total_user_messages": 0,
                "total_active_sessions": 0,
                "total_voice_requests": 0,
                "avg_messages_per_user": 0.0,
                "avg_sessions_per_user": 0.0,
                "avg_voice_requests_per_user": 0.0,
                "avg_rounds_per_session": 0.0,
                "new_user_open_rate": round(new_user_open_rate, 2),
                "total_image_generation_requests": total_image_generation_requests,
                "total_image_generation_success": total_image_generation_success,
                "total_image_generation_failures": total_image_generation_failures,
                "image_generation_success_rate": round(image_generation_success_rate, 2),
            }

        # 4. 计算统计指标
        total_active_sessions = len(active_sessions)
        total_active_users = len(set(item["user_id"] for item in active_sessions))
        total_user_messages = sum(item["message_count"] for item in active_sessions)
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

        # 计算新增用户开口率
        new_user_open_rate = (
            (total_active_users / total_new_users * 100) if total_new_users > 0 else 0.0
        )

        # 6. 查询生图统计
        image_gen_query = text("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= :start_date 
              AND usage_date < :end_date
        """)
        image_gen_result = await self.db.execute(
            image_gen_query, {"start_date": start_date, "end_date": end_date}
        )
        image_gen_row = image_gen_result.fetchone()
        
        total_image_generation_requests = image_gen_row[0] if image_gen_row else 0
        total_image_generation_success = image_gen_row[1] if image_gen_row else 0
        total_image_generation_failures = image_gen_row[2] if image_gen_row else 0
        
        # 计算成功率
        image_generation_success_rate = (
            (total_image_generation_success / total_image_generation_requests * 100)
            if total_image_generation_requests > 0
            else 0.0
        )

        return {
            "total_new_users": total_new_users,
            "total_chat_initiators": total_active_users,
            "total_user_messages": total_user_messages,
            "total_active_sessions": total_active_sessions,
            "total_voice_requests": total_voice_requests,
            "avg_messages_per_user": round(avg_messages_per_user, 2),
            "avg_sessions_per_user": round(avg_sessions_per_user, 2),
            "avg_voice_requests_per_user": round(avg_voice_requests_per_user, 2),
            "avg_rounds_per_session": round(avg_rounds_per_session, 2),
            "new_user_open_rate": round(new_user_open_rate, 2),
            "total_image_generation_requests": total_image_generation_requests,
            "total_image_generation_success": total_image_generation_success,
            "total_image_generation_failures": total_image_generation_failures,
            "image_generation_success_rate": round(image_generation_success_rate, 2),
        }

    async def get_chat_messages(self, chat_ids: List[str]) -> List[Dict[str, Any]]:
        """查询聊天会话的具体消息"""
        if not chat_ids:
            return []

        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if not session_ids:
            return []

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        query = text(
            f"""
            SELECT
                ch.session_id::text as session_id,
                ch.message->>'type' as message_type,
                ch.message->>'content' as content,
                ch.created_at,
                ch.audio_url
            FROM chat_history ch
            WHERE ch.session_id::text IN ({placeholders})
            ORDER BY ch.created_at
        """
        )
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        result = await self.db.execute(query, params)
        rows = result.fetchall()

        session_to_chat = {v: k for k, v in chat_to_session.items()}
        data = []
        for row in rows:
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

    async def get_users_hitting_chat_limit(
        self,
        start_date: datetime,
        end_date: datetime,
        guest_limit: Optional[int] = None,
        google_limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询按日统计达到聊天限制的用户"""
        from datetime import timedelta

        if guest_limit is None:
            guest_limit = (
                global_config_loaded_from_config_yaml.app.limits.guest_user_chat_24h_limit
            )
        if google_limit is None:
            google_limit = (
                global_config_loaded_from_config_yaml.app.limits.free_user_chat_24h_limit
            )

        # 计算查询范围：需要提前24小时来获取活跃用户
        query_start_date = start_date - timedelta(hours=24)
        end_date_minus_one_day = end_date - timedelta(days=1)

        # 将 datetime 转换为 date 字符串用于 SQL
        start_date_str = start_date.date().isoformat()
        end_date_minus_one_day_str = end_date_minus_one_day.date().isoformat()

        # 先检查 subscription_usage 表中是否有数据
        check_query = text(
            """
            SELECT COUNT(*) as count
            FROM subscription_usage
            WHERE usage_type = 'chat'
              AND usage_date >= :query_start_date
              AND usage_date < :end_date
        """
        )
        check_result = await self.db.execute(
            check_query,
            {
                "query_start_date": query_start_date,
                "end_date": end_date,
            },
        )
        usage_count = check_result.scalar() or 0
        logger.debug(f"subscription_usage 表中符合条件的记录数: {usage_count}")

        if usage_count == 0:
            logger.info(
                f"subscription_usage 表中没有符合条件的聊天使用记录，返回空结果"
            )
            return []

        # 构建 SQL 查询，将日期字符串和整数限制直接嵌入（已验证是安全的）
        query = text(
            f"""
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
                  AND su.usage_date < :end_date
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
        """
        )
        try:
            result = await self.db.execute(
                query,
                {
                    "end_date": end_date,
                    "query_start_date": query_start_date,
                },
            )
            rows = result.fetchall()
            logger.debug(f"查询到 {len(rows)} 个达到限制的用户记录")
            return [
                {
                    "date": (
                        row[0].isoformat()
                        if isinstance(row[0], datetime)
                        else str(row[0])
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
        except Exception as e:
            logger.error(f"查询达到限制的用户失败: {str(e)}")
            logger.error(
                f"查询参数: start_date={start_date}, end_date={end_date}, guest_limit={guest_limit}, google_limit={google_limit}"
            )
            logger.exception(e)
            # 如果查询失败，返回空列表而不是抛出异常，避免影响其他功能
            return []

    async def get_agent_analytics(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """查询角色数据分析统计"""
        chats_query = text(
            """
            SELECT
                c.id as chat_id,
                c.agent_id,
                a.name as agent_name,
                c.user_id
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id
            INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE u.created_at >= :start_date AND u.created_at < :end_date
              AND u.deleted_at IS NULL
              AND c.is_active = true
        """
        )
        result = await self.db.execute(
            chats_query, {"start_date": start_date, "end_date": end_date}
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

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        messages_query = text(
            f"""
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
        """
        )
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        result = await self.db.execute(messages_query, params)

        session_to_user_msg_count = {row[0]: row[1] for row in result.fetchall()}

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
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """查询用户会话详情（聚合数据）"""
        chats_query = text(
            """
            SELECT
                u.id as user_id,
                u.auth_type,
                u.created_at as user_created_at,
                u.nickname,
                u.email,
                c.id as chat_id,
                a.name as agent_name
            FROM users u
            INNER JOIN chats c ON u.id = c.user_id AND c.is_active = true
            INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE u.created_at >= :start_date AND u.created_at < :end_date
              AND u.deleted_at IS NULL
            ORDER BY u.id, c.created_at
        """
        )
        result = await self.db.execute(
            chats_query, {"start_date": start_date, "end_date": end_date}
        )
        chat_records = result.fetchall()

        if not chat_records:
            return []

        chat_ids = [row[5] for row in chat_records]
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        if not session_ids:
            return []

        placeholders = ",".join([f":session_id_{i}" for i in range(len(session_ids))])
        messages_query = text(
            f"""
            SELECT
                ch.session_id::text as session_id,
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
                ) as voice_message_count
            FROM chat_history ch
            WHERE ch.session_id::text IN ({placeholders})
            GROUP BY ch.session_id
        """
        )
        params = {f"session_id_{i}": sid for i, sid in enumerate(session_ids)}
        result = await self.db.execute(messages_query, params)

        session_to_msg_count = {}
        session_to_voice_count = {}
        for row in result.fetchall():
            session_id_str = row[0]
            session_to_msg_count[session_id_str] = row[1]
            session_to_voice_count[session_id_str] = row[2]

        data = []
        for row in chat_records:
            chat_id = row[5]
            session_id = chat_to_session[chat_id]
            message_count = session_to_msg_count.get(session_id, 0)
            voice_count = session_to_voice_count.get(session_id, 0)

            data.append(
                {
                    "user_id": row[0],
                    "auth_type": row[1],
                    "user_created_at": row[2].isoformat() if row[2] else None,
                    "nickname": row[3],
                    "email": row[4],
                    "chat_id": chat_id,
                    "agent_name": row[6],
                    "message_count": message_count,
                    "voice_message_count": voice_count,
                }
            )

        return data
