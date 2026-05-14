#!/usr/bin/env python3
"""
用户行为分析脚本

分析 Inty 数据库中的用户注册和聊天行为，生成数据报告和可视化图表。
"""

import argparse
import html
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import yaml
from loguru import logger
from plotly.subplots import make_subplots


def generate_session_id(chat_id: str) -> str:
    """
    生成 session_id，与 app/services/chat_service.py 中的逻辑一致

    验证：使用相同的 UUID5 生成方式，确保与后端代码完全一致
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


class UserAnalytics:
    """用户行为分析类"""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def get_new_users(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """查询新用户统计"""
        query = """
            SELECT 
                DATE(created_at AT TIME ZONE 'UTC') as date,
                auth_type,
                COUNT(*) as count
            FROM users
            WHERE created_at >= %s AND created_at < %s
              AND deleted_at IS NULL
            GROUP BY DATE(created_at AT TIME ZONE 'UTC'), auth_type
            ORDER BY date, auth_type
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
        finally:
            cursor.close()

    def get_user_chat_activity(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """查询用户聊天活动"""
        query = """
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
            WHERE u.created_at >= %s AND u.created_at < %s
              AND u.deleted_at IS NULL
            ORDER BY u.id, c.created_at
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
        finally:
            cursor.close()

    def get_new_users_email_list(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """查询新用户邮箱列表（只包含有邮箱的用户）"""
        query = """
            SELECT 
                id as user_id,
                email,
                created_at,
                auth_type
            FROM users
            WHERE created_at >= %s AND created_at < %s
              AND deleted_at IS NULL
              AND email IS NOT NULL
            ORDER BY created_at DESC
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
        finally:
            cursor.close()

    def get_conversation_rounds(self, start_date: datetime) -> pd.DataFrame:
        """查询对话轮数统计"""
        # 先检查 chat_history 表中是否有数据
        check_query = """
            SELECT COUNT(*) as total_messages,
                   COUNT(DISTINCT session_id) as unique_sessions
            FROM chat_history
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(check_query)
            check_result = cursor.fetchone()
            logger.info(
                f"chat_history 表统计: 总消息数={check_result[0]}, 唯一session数={check_result[1]}"
            )

            if check_result[0] == 0:
                logger.warning("chat_history 表中没有数据")
                return pd.DataFrame()

            # 详细调试：分别查看两个表的数据
            # 1. 查看 chats 表的 ID
            chats_ids_query = """
                SELECT id
                FROM chats
                WHERE created_at >= %s
                LIMIT 3
            """
            cursor.execute(chats_ids_query, (start_date,))
            chats_ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"chats 表样本 ID (前3个): {chats_ids}")

            # 2. 查看 chat_history 表的 session_id
            history_ids_query = """
                SELECT DISTINCT session_id
                FROM chat_history
                LIMIT 3
            """
            cursor.execute(history_ids_query)
            history_ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"chat_history 表样本 session_id (前3个): {history_ids}")
            logger.info(
                f"chat_history session_id 类型: {type(history_ids[0]) if history_ids else 'N/A'}"
            )

            # 3. 尝试不同的匹配方式
            # 尝试 UUID 直接比较
            test_query = """
                SELECT COUNT(*)
                FROM chats c
                JOIN chat_history ch ON c.id::uuid = ch.session_id
                WHERE c.created_at >= %s
            """
            try:
                cursor.execute(test_query, (start_date,))
                count1 = cursor.fetchone()[0]
                logger.info(
                    f"尝试 UUID 直接比较 (c.id::uuid = ch.session_id): 匹配到 {count1} 条"
                )
            except Exception as e:
                logger.warning(f"UUID 直接比较失败: {e}")

            # 先获取所有符合条件的 chat_id
            chats_query = """
                SELECT id
                FROM chats
                WHERE created_at >= %s
            """
            cursor.execute(chats_query, (start_date,))
            chat_ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"找到 {len(chat_ids)} 个聊天会话")

            if not chat_ids:
                return pd.DataFrame()

            # 在 Python 中生成所有 session_id
            chat_to_session = {
                chat_id: generate_session_id(chat_id) for chat_id in chat_ids
            }
            session_ids = list(chat_to_session.values())

            # 查询 chat_history 中存在的 session_id
            placeholders = ",".join(["%s"] * len(session_ids))
            history_query = f"""
                SELECT 
                    session_id::text,
                    COUNT(*) as message_count,
                    COUNT(*) FILTER (WHERE meta_data->>'isOpening' != 'true' OR meta_data IS NULL) as non_opening_count
                FROM chat_history
                WHERE session_id::text IN ({placeholders})
                GROUP BY session_id
            """
            cursor.execute(history_query, tuple(session_ids))

            # 构建 session_id 到消息数的映射
            session_to_count = {}
            session_to_non_opening_count = {}
            for row in cursor.fetchall():
                session_to_count[row[0]] = row[1]
                session_to_non_opening_count[row[0]] = row[2]

            # 转换回 chat_id 和消息数
            data = []
            for chat_id, session_id in chat_to_session.items():
                if session_id in session_to_count:
                    data.append(
                        (
                            chat_id,
                            session_to_count[session_id],
                            session_to_non_opening_count.get(
                                session_id, session_to_count[session_id]
                            ),
                        )
                    )

            logger.info(f"找到 {len(data)} 个有对话记录的会话")

            return pd.DataFrame(
                data,
                columns=["chat_id", "message_count", "message_count_excluding_opening"],
            )
        finally:
            cursor.close()

    def get_voice_usage(self, chat_ids: List[str]) -> pd.DataFrame:
        """查询语音使用统计

        统计每个chat中有语音的消息数量（排除开场白）

        注意：统计范围是这些会话的所有历史消息，不限制时间范围
        这样能完整反映新用户的整体语音使用行为模式
        """
        if not chat_ids:
            return pd.DataFrame()

        # 在 Python 中生成 session_id
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        # 查询有语音的消息（排除开场白）
        placeholders = ",".join(["%s"] * len(session_ids))
        query = f"""
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
        cursor = self.conn.cursor()
        try:
            # 测试查询：先检查数据库中是否有任何语音消息（用于诊断）
            test_query = """
                SELECT 
                    COUNT(*) as total_with_audio,
                    COUNT(*) FILTER (WHERE meta_data->>'isOpening' = 'true') as opening_with_audio,
                    COUNT(*) FILTER (
                        WHERE audio_url IS NOT NULL 
                        AND (
                            meta_data IS NULL 
                            OR meta_data->>'isOpening' IS NULL 
                            OR meta_data->>'isOpening' != 'true'
                        )
                    ) as non_opening_with_audio
                FROM chat_history
                WHERE audio_url IS NOT NULL
            """
            cursor.execute(test_query)
            test_result = cursor.fetchone()
            logger.info(
                f"数据库诊断: 总语音消息={test_result[0]}, "
                f"开场白语音={test_result[1]}, "
                f"非开场白语音={test_result[2]}"
            )

            logger.info(f"查询语音使用: 准备查询 {len(session_ids)} 个 session_id")

            # 额外诊断：检查这些session_id中是否有匹配的记录
            sample_session_ids = (
                session_ids[:5] if len(session_ids) >= 5 else session_ids
            )
            if sample_session_ids:
                sample_placeholders = ",".join(["%s"] * len(sample_session_ids))
                sample_check_query = f"""
                    SELECT COUNT(*) 
                    FROM chat_history 
                    WHERE session_id::text IN ({sample_placeholders})
                """
                cursor.execute(sample_check_query, tuple(sample_session_ids))
                matched_count = cursor.fetchone()[0]
                logger.info(
                    f"会话匹配检查: 前5个session_id在数据库中匹配到 {matched_count} 条消息记录"
                )

            cursor.execute(query, tuple(session_ids))

            # 构建 session_id 到语音消息数的映射
            query_results = cursor.fetchall()
            session_to_voice_count = {row[0]: row[1] for row in query_results}
            logger.info(f"查询语音使用: 数据库返回 {len(query_results)} 条结果")

            # 统计有语音的session数量
            sessions_with_voice = sum(
                1 for count in session_to_voice_count.values() if count > 0
            )
            total_voice_messages = sum(session_to_voice_count.values())
            logger.info(
                f"语音使用统计: {sessions_with_voice} 个会话有语音，共 {total_voice_messages} 条语音消息"
            )

            # 转换回 chat_id 和语音消息数
            data = []
            for chat_id, session_id in chat_to_session.items():
                voice_count = session_to_voice_count.get(session_id, 0)
                if voice_count > 0:
                    data.append((chat_id, voice_count))
                    logger.debug(f"会话 {chat_id[:20]}... 有 {voice_count} 条语音消息")

            logger.info(f"语音使用统计: 返回 {len(data)} 个有语音的会话")
            return pd.DataFrame(data, columns=["chat_id", "voice_message_count"])
        finally:
            cursor.close()

    def get_chat_messages(self, chat_ids: List[str]) -> pd.DataFrame:
        """查询聊天会话的具体消息

        chats.id 对应 chat_history.session_id
        """
        if not chat_ids:
            return pd.DataFrame()

        # 在 Python 中生成 session_id
        chat_to_session = {
            chat_id: generate_session_id(chat_id) for chat_id in chat_ids
        }
        session_ids = list(chat_to_session.values())

        # 查询 chat_history
        placeholders = ",".join(["%s"] * len(session_ids))
        query = f"""
            SELECT 
                ch.session_id::text as session_id,
                ch.message->>'type' as message_type,
                COALESCE(
                    ch.message->'data'->>'content',
                    ch.message->>'content'
                ) as content,
                ch.created_at,
                ch.meta_data
            FROM chat_history ch
            WHERE ch.session_id::text IN ({placeholders})
            ORDER BY ch.session_id, ch.created_at
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, tuple(session_ids))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()

            # 转换 session_id 回 chat_id
            session_to_chat = {v: k for k, v in chat_to_session.items()}
            result_data = []
            for row in data:
                session_id_str = row[0]
                chat_id = session_to_chat.get(session_id_str)
                if chat_id:
                    result_data.append((chat_id, row[1], row[2], row[3], row[4]))

            return pd.DataFrame(
                result_data,
                columns=[
                    "chat_id",
                    "message_type",
                    "content",
                    "created_at",
                    "meta_data",
                ],
            )
        finally:
            cursor.close()

    def get_users_hitting_chat_limit(
        self,
        start_date: datetime,
        end_date: datetime,
        guest_limit: int,
        google_limit: int,
    ) -> pd.DataFrame:
        """查询按日统计达到聊天限制的用户

        对分析时间范围内的每一天，计算每个用户在过去24小时内的聊天次数，
        筛选达到或超过限制的用户。

        Args:
            start_date: 开始日期
            end_date: 结束日期
            guest_limit: guest用户的聊天限制（24小时）
            google_limit: google登录用户的聊天限制（24小时）

        Returns:
            DataFrame包含：日期、用户ID、认证类型、昵称、邮箱、当日24小时聊天次数、限制值
        """
        query = """
            WITH date_series AS (
                SELECT generate_series(
                    DATE(%s),
                    DATE(%s - interval '1 day'),
                    interval '1 day'
                )::date as check_date
            ),
            active_users AS (
                SELECT DISTINCT su.user_id
                FROM subscription_usage su
                WHERE su.usage_type = 'chat'
                  AND su.usage_date >= %s - interval '24 hours'
                  AND su.usage_date < %s
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
                        WHEN u.auth_type = 'GUEST' THEN %s
                        ELSE %s
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
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                query,
                (
                    start_date,
                    end_date,
                    start_date,
                    end_date,
                    guest_limit,
                    google_limit,
                ),
            )
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
        finally:
            cursor.close()

    def get_agent_analytics(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """查询角色数据分析统计
        统计指定日期范围内新注册用户与各角色的聊天数据
        Args:
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            DataFrame包含：
            - agent_id: 角色ID
            - agent_name: 角色名称
            - chat_user_count: 聊天人数（发送了至少一条消息的用户数）
            - total_sessions: 总会话数（有用户消息的会话）
            - total_rounds: 总轮数（用户消息数）
            - sessions_ge_5_rounds: ≥5轮的会话数
            - sessions_ge_10_rounds: ≥10轮的会话数
            - avg_rounds_per_user: 人均轮数
            - ge_5_rounds_ratio: ≥5轮占比(%)
            - ge_10_rounds_ratio: ≥10轮占比(%)
        """
        chats_query = """
            SELECT
                c.id as chat_id,
                c.agent_id,
                a.name as agent_name,
                c.user_id
            FROM chats c
            INNER JOIN users u ON c.user_id = u.id
            INNER JOIN agents a ON c.agent_id = a.id AND a.deleted_at IS NULL
            WHERE u.created_at >= %s AND u.created_at < %s
              AND u.deleted_at IS NULL
              AND c.is_active = true
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(chats_query, (start_date, end_date))
            chat_records = cursor.fetchall()
            logger.info(f"找到 {len(chat_records)} 个新用户聊天会话")

            if not chat_records:
                return pd.DataFrame()

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

            placeholders = ",".join(["%s"] * len(session_ids))
            messages_query = f"""
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
            cursor.execute(messages_query, tuple(session_ids))

            session_to_user_msg_count = {}
            for row in cursor.fetchall():
                session_id_str = row[0]
                user_msg_count = row[1]
                session_to_user_msg_count[session_id_str] = user_msg_count

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

            logger.info(f"统计了 {len(result_data)} 个角色的数据")
            return pd.DataFrame(result_data)
        finally:
            cursor.close()


class ReportGenerator:
    """报告生成类"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_csv(self, df: pd.DataFrame, filename: str):
        """保存 CSV 文件"""
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"已保存 CSV: {filepath}")

    def save_text_report(self, content: str, filename: str):
        """保存文本报告"""
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"已保存文本报告: {filepath}")

    def generate_html_report(
        self,
        daily_users_df: pd.DataFrame,
        user_activity_df: pd.DataFrame,
        popular_agents_df: pd.DataFrame,
        rounds_dist_df: pd.DataFrame,
        user_rounds_dist_df: pd.DataFrame,
        user_sessions_detail_df: pd.DataFrame,
        users_hitting_limit_df: pd.DataFrame,
        date_range: Tuple[datetime, datetime],
    ):
        """生成 HTML 可视化报告"""
        fig = make_subplots(
            rows=7,
            cols=1,
            subplot_titles=(
                "每日新用户趋势",
                "用户聊天活跃度分布",
                "Top 20 热门聊天角色",
                "对话轮数分布（按Session）",
                "对话轮数分布（按用户）",
                "达到聊天限制的用户趋势",
                "新增用户会话详情表",
            ),
            vertical_spacing=0.05,
            specs=[
                [{"type": "bar"}],
                [{"type": "histogram"}],
                [{"type": "bar"}],
                [{"type": "bar"}],
                [{"type": "bar"}],
                [{"type": "bar"}],
                [{"type": "table"}],
            ],
        )

        # 图表 1: 每日新用户趋势（堆叠柱状图）
        if not daily_users_df.empty:
            for auth_type in ["GUEST", "GOOGLE"]:
                data = daily_users_df[daily_users_df["auth_type"] == auth_type]
                fig.add_trace(
                    go.Bar(
                        x=data["date"],
                        y=data["count"],
                        name=f"{auth_type} 用户",
                        legendgroup="auth",
                    ),
                    row=1,
                    col=1,
                )

        # 图表 2: 用户聊天活跃度分布
        if not user_activity_df.empty:
            # 尝试 session_count 或 chat_count
            count_col = (
                "session_count"
                if "session_count" in user_activity_df.columns
                else "chat_count"
            )
            if count_col in user_activity_df.columns:
                chat_counts = user_activity_df[count_col]
                # 只显示有聊天的用户
                active_chat_counts = chat_counts[chat_counts > 0]
                if len(active_chat_counts) > 0:
                    fig.add_trace(
                        go.Histogram(
                            x=active_chat_counts.values,
                            nbinsx=20,
                            name="用户分布",
                            showlegend=False,
                        ),
                        row=2,
                        col=1,
                    )

        # 图表 3: Top 20 热门聊天角色
        if not popular_agents_df.empty:
            top_agents = popular_agents_df.head(20)
            fig.add_trace(
                go.Bar(
                    x=top_agents["user_count"],
                    y=top_agents["agent_name"],
                    orientation="h",
                    name="用户数",
                    showlegend=False,
                ),
                row=3,
                col=1,
            )

        # 图表 4: 对话轮数分布（按Session）
        if not rounds_dist_df.empty:
            fig.add_trace(
                go.Bar(
                    x=rounds_dist_df["rounds_range"],
                    y=rounds_dist_df["count"],
                    name="Session数",
                    showlegend=False,
                    marker_color="lightblue",
                ),
                row=4,
                col=1,
            )

        # 图表 5: 对话轮数分布（按用户）
        if not user_rounds_dist_df.empty:
            fig.add_trace(
                go.Bar(
                    x=user_rounds_dist_df["rounds_range"],
                    y=user_rounds_dist_df["user_count"],
                    name="用户数",
                    showlegend=False,
                    marker_color="lightcoral",
                ),
                row=5,
                col=1,
            )

        # 图表 6: 达到聊天限制的用户趋势
        if not users_hitting_limit_df.empty:
            # 按日期和认证类型分组统计
            daily_hitting_limit = (
                users_hitting_limit_df.groupby(["date", "auth_type"])
                .size()
                .reset_index(name="count")
            )

            for auth_type in ["GUEST", "GOOGLE"]:
                data = daily_hitting_limit[
                    daily_hitting_limit["auth_type"] == auth_type
                ]
                if not data.empty:
                    fig.add_trace(
                        go.Bar(
                            x=data["date"],
                            y=data["count"],
                            name=f"{auth_type} 达到限制",
                            legendgroup="limit",
                            marker_color="orange" if auth_type == "GUEST" else "red",
                        ),
                        row=6,
                        col=1,
                    )

        # 图表 7: 新增用户会话详情表
        if not user_sessions_detail_df.empty:
            # 准备表格数据，限制显示前100条
            display_df = user_sessions_detail_df.head(100).copy()

            # 格式化时间
            if "user_created_at" in display_df.columns:
                display_df["user_created_at"] = pd.to_datetime(
                    display_df["user_created_at"]
                ).dt.strftime("%Y-%m-%d %H:%M:%S")

            # 截断过长的ID
            if "user_id" in display_df.columns:
                display_df["user_id_short"] = display_df["user_id"].str[:20] + "..."
            if "chat_id" in display_df.columns:
                display_df["chat_id_short"] = display_df["chat_id"].str[:20] + "..."

            # 创建交互式表格
            table_data = [
                display_df.get("user_id_short", display_df.get("user_id", [])),
                display_df.get("auth_type", []),
                display_df.get("user_created_at", []),
                display_df.get("chat_id_short", display_df.get("chat_id", [])),
                display_df.get("agent_name", []),
                display_df.get("message_count", []),
            ]

            fig.add_trace(
                go.Table(
                    header=dict(
                        values=[
                            "用户ID",
                            "认证类型",
                            "注册时间",
                            "会话ID",
                            "角色名称",
                            "消息数",
                        ],
                        fill_color="paleturquoise",
                        align="left",
                        font=dict(size=12),
                    ),
                    cells=dict(
                        values=table_data,
                        fill_color="lavender",
                        align="left",
                        font=dict(size=11),
                        height=25,
                    ),
                ),
                row=7,
                col=1,
            )

        # 更新布局
        fig.update_layout(
            height=3700,  # 增加高度以容纳新图表
            title_text=f"用户行为分析报告 ({date_range[0].date()} 至 {date_range[1].date()})",
            showlegend=True,
        )

        fig.update_xaxes(title_text="日期", row=1, col=1)
        fig.update_yaxes(title_text="用户数", row=1, col=1)

        fig.update_xaxes(title_text="聊天角色数量", row=2, col=1)
        fig.update_yaxes(title_text="用户数", row=2, col=1)

        fig.update_xaxes(title_text="聊天用户数", row=3, col=1)
        fig.update_yaxes(title_text="角色名称", row=3, col=1)

        fig.update_xaxes(title_text="消息数区间", row=4, col=1)
        fig.update_yaxes(title_text="Session数量", row=4, col=1)

        fig.update_xaxes(title_text="消息数区间", row=5, col=1)
        fig.update_yaxes(title_text="用户数量", row=5, col=1)

        fig.update_xaxes(title_text="日期", row=6, col=1)
        fig.update_yaxes(title_text="达到限制的用户数", row=6, col=1)

        # 保存 HTML
        filepath = self.output_dir / "user_analytics_report.html"
        fig.write_html(str(filepath))
        logger.info(f"已保存 HTML 报告: {filepath}")

    def generate_detailed_html_report(
        self,
        user_sessions_detail_df: pd.DataFrame,
        messages_df: pd.DataFrame,
        date_range: Tuple[datetime, datetime],
        stats: Optional[Dict[str, Any]] = None,
        long_conversations: Optional[pd.DataFrame] = None,
    ):
        """生成包含对话详情的详细HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户对话详情报告 - {date_range[0].date()} 至 {date_range[1].date()}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .stats-section {{
            margin: 30px 0;
        }}
        .stats-section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card h3 {{
            margin: 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stat-card .number {{
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-card .description {{
            font-size: 11px;
            opacity: 0.85;
            margin-top: 8px;
            line-height: 1.4;
        }}
        .stat-card .calculation {{
            font-size: 10px;
            opacity: 0.7;
            margin-top: 5px;
            font-style: italic;
        }}
        .user-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin: 20px 0;
            overflow: hidden;
        }}
        .user-header {{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .user-header:hover {{
            opacity: 0.9;
        }}
        .user-info {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .user-info-item {{
            display: flex;
            flex-direction: column;
        }}
        .user-info-item label {{
            font-size: 12px;
            opacity: 0.8;
        }}
        .user-info-item value {{
            font-size: 16px;
            font-weight: bold;
        }}
        .toggle-icon {{
            font-size: 24px;
            transition: transform 0.3s;
        }}
        .toggle-icon.expanded {{
            transform: rotate(180deg);
        }}
        .user-content {{
            display: none;
            padding: 20px;
            background: #fafafa;
        }}
        .user-content.expanded {{
            display: block;
        }}
        .session-card {{
            background: white;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .session-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .session-title {{
            font-weight: bold;
            color: #4CAF50;
            font-size: 16px;
        }}
        .session-meta {{
            color: #666;
            font-size: 14px;
        }}
        .messages {{
            margin-top: 10px;
        }}
        .message {{
            margin: 10px 0;
            padding: 12px;
            border-radius: 8px;
            max-width: 85%;
        }}
        .message.user {{
            background: #e3f2fd;
            margin-left: auto;
            border-bottom-right-radius: 0;
        }}
        .message.assistant {{
            background: #f5f5f5;
            margin-right: auto;
            border-bottom-left-radius: 0;
        }}
        .message-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 12px;
            color: #666;
        }}
        .message-role {{
            font-weight: bold;
        }}
        .message.user .message-role {{
            color: #1976d2;
        }}
        .message.assistant .message-role {{
            color: #4CAF50;
        }}
        .message-content {{
            line-height: 1.6;
            color: #333;
        }}
        .no-messages {{
            color: #999;
            text-align: center;
            padding: 20px;
            font-style: italic;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge.guest {{
            background: #ffeaa7;
            color: #d63031;
        }}
        .badge.google {{
            background: #74b9ff;
            color: #0984e3;
        }}
        .search-box {{
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        .search-box input {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        .filter-box {{
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        .filter-title {{
            font-size: 14px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }}
        .filter-buttons {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 8px 16px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }}
        .filter-btn:hover {{
            background: #f0f0ff;
        }}
        .filter-btn.active {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
        }}
        .user-nickname {{
            font-size: 14px;
            color: #666;
            margin-left: 10px;
        }}
        .user-email {{
            font-size: 12px;
            color: #999;
            font-style: italic;
        }}
        .long-conversations-table {{
            margin: 30px 0;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        .long-conversations-table table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        .long-conversations-table thead {{
            background: #f8f9fa;
            position: sticky;
            top: 0;
        }}
        .long-conversations-table th {{
            padding: 12px;
            text-align: left;
            font-weight: bold;
            color: #333;
            border-bottom: 2px solid #ddd;
        }}
        .long-conversations-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}
        .long-conversations-table tr:hover {{
            background: #f8f9fa;
        }}
        .long-conversations-table tr.top10 {{
            background: #fff3cd;
        }}
        .long-conversations-table tr.top10:hover {{
            background: #ffeaa7;
        }}
        .rounds-badge {{
            display: inline-block;
            padding: 4px 8px;
            background: #74b9ff;
            color: white;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>👥 用户对话详情报告</h1>
        <p style="color: #666;">分析时间范围: {date_range[0].date()} 至 {date_range[1].date()}</p>
"""

        if user_sessions_detail_df.empty or messages_df.empty:
            html_content += """
        <div class="no-messages">
            <h2>暂无对话数据</h2>
            <p>所选时间范围内没有找到用户对话记录</p>
        </div>
"""
        else:
            # 计算排除开场白的消息数（用于后续排序）
            if "meta_data" in messages_df.columns:
                messages_excluding_opening = messages_df[
                    messages_df["meta_data"].apply(
                        lambda x: not (
                            isinstance(x, dict) and x.get("isOpening") == True
                        )
                    )
                ]
            else:
                messages_excluding_opening = messages_df

            # 计算有用户消息的chat_id列表（用于后续判断）
            user_messages_df = messages_df[messages_df["message_type"] == "human"]
            chat_ids_with_user_msgs = user_messages_df["chat_id"].unique()

            # 使用传入的stats数据，如果没有则计算
            if stats is None:
                # 计算基础统计（兼容旧代码）
                total_browse_sessions = len(user_sessions_detail_df)
                total_real_sessions = user_sessions_detail_df[
                    user_sessions_detail_df["chat_id"].isin(chat_ids_with_user_msgs)
                ].shape[0]
                stats = {
                    "total_new_users": user_sessions_detail_df["user_id"].nunique(),
                    "total_chat_initiators": len(
                        user_sessions_detail_df[
                            user_sessions_detail_df["chat_id"].isin(
                                chat_ids_with_user_msgs
                            )
                        ]["user_id"].unique()
                    ),
                    "total_user_messages": len(user_messages_df),
                    "total_active_sessions": total_real_sessions,
                    "avg_messages_per_user": 0,
                    "avg_sessions_per_user": 0,
                    "avg_voice_requests_per_user": 0,
                    "avg_rounds_per_session": 0,
                }

            total_browse_sessions = len(user_sessions_detail_df)  # 总浏览数（用于显示）

            # 计算总语音请求数
            total_voice_requests = 0
            if "voice_message_count" in user_sessions_detail_df.columns:
                total_voice_requests = user_sessions_detail_df[
                    "voice_message_count"
                ].sum()

            html_content += f"""
        <!-- 第一部分：统计类型 -->
        <div class="stats-section">
            <div class="stats-section-title">📊 统计类型</div>
            <div class="stats">
                <div class="stat-card">
                    <h3>新增用户数</h3>
                    <div class="number">{stats.get('total_new_users', 0)}</div>
                    <div class="description">在分析时间范围内注册的新用户总数</div>
                    <div class="calculation">COUNT(DISTINCT users.id WHERE created_at IN date_range)</div>
                </div>
                <div class="stat-card">
                    <h3>发起聊天的人数</h3>
                    <div class="number">{stats.get('total_chat_initiators', 0)}</div>
                    <div class="description">发送了至少一条消息的用户数（排除仅浏览开场白的用户）</div>
                    <div class="calculation">COUNT(DISTINCT user_id FROM user_messages)</div>
                </div>
                <div class="stat-card">
                    <h3>总发送消息数</h3>
                    <div class="number">{stats.get('total_user_messages', 0)}</div>
                    <div class="description">用户发送的所有消息总数（排除AI回复和开场白）</div>
                    <div class="calculation">COUNT(messages WHERE message_type = 'human')</div>
                </div>
                <div class="stat-card">
                    <h3>包含用户消息的会话数</h3>
                    <div class="number">{stats.get('total_active_sessions', 0)}</div>
                    <div class="description">包含至少一条用户消息的会话总数（排除仅浏览开场白的会话）</div>
                    <div class="calculation">COUNT(DISTINCT chat_id WHERE has_user_message = true)</div>
                </div>
                <div class="stat-card">
                    <h3>总语音请求数</h3>
                    <div class="number">{stats.get('total_voice_requests', 0)}</div>
                    <div class="description">所有用户的语音消息请求总数（已排除开场白语音）</div>
                    <div class="calculation">COUNT(messages WHERE audio_url IS NOT NULL AND meta_data->>'isOpening' != 'true')</div>
                </div>
            </div>
        </div>

        <!-- 第二部分：用户维度（仅统计发送聊天的用户） -->
        <div class="stats-section">
            <div class="stats-section-title">👤 用户维度（仅统计发送聊天的用户）</div>
            <div class="stats">
                <div class="stat-card">
                    <h3>平均发送消息数</h3>
                    <div class="number">{stats.get('avg_messages_per_user', 0):.2f}</div>
                    <div class="description">发送聊天用户的平均消息数</div>
                    <div class="calculation">总发送消息数 / 发起聊天的人数</div>
                </div>
                <div class="stat-card">
                    <h3>平均会话数</h3>
                    <div class="number">{stats.get('avg_sessions_per_user', 0):.2f}</div>
                    <div class="description">发送聊天用户的平均会话数</div>
                    <div class="calculation">包含用户消息的会话数 / 发起聊天的人数</div>
                </div>
                <div class="stat-card">
                    <h3>平均发起语音请求数</h3>
                    <div class="number">{stats.get('avg_voice_requests_per_user', 0):.2f}</div>
                    <div class="description">发送聊天用户的平均语音请求数（已排除开场白语音）</div>
                    <div class="calculation">总语音请求数 / 发起聊天的人数</div>
                </div>
            </div>
        </div>

        <!-- 第三部分：会话维度（包含用户消息的会话） -->
        <div class="stats-section">
            <div class="stats-section-title">💬 会话维度（包含用户消息的会话）</div>
            <div class="stats">
                <div class="stat-card">
                    <h3>每个会话平均轮数</h3>
                    <div class="number">{stats.get('avg_rounds_per_session', 0):.2f}</div>
                    <div class="description">包含用户消息的会话中，平均每会话的对话轮数</div>
                    <div class="calculation">1轮 = 1条用户消息 + 1条AI回复<br/>总用户消息数 / 包含用户消息的会话数</div>
                </div>
            </div>
        </div>

        <!-- 长对话会话排行 -->
"""
            # 添加长对话会话表格
            if long_conversations is not None and not long_conversations.empty:
                html_content += """
        <div class="long-conversations-table">
            <div class="stats-section-title" style="margin-bottom: 20px;">🏆 长对话会话排行（Top 50）</div>
            <div style="font-size: 12px; color: #666; margin-bottom: 15px;">
                仅显示包含用户消息的会话（排除仅浏览开场白的会话），按对话轮数降序排列
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 60px;">排名</th>
                        <th style="width: 120px;">用户ID</th>
                        <th style="width: 150px;">昵称</th>
                        <th style="width: 100px;">认证类型</th>
                        <th style="width: 150px;">角色名称</th>
                        <th style="width: 100px;">对话轮数</th>
                        <th style="width: 120px;">消息总数<br/>(排除开场白)</th>
                        <th style="width: 100px;">语音请求数</th>
                    </tr>
                </thead>
                <tbody>
"""
                for idx, row in long_conversations.iterrows():
                    rank = row.get("rank", idx + 1)
                    user_id = row.get("user_id", "")
                    nickname = row.get("nickname", "") or "未设置"
                    auth_type = row.get("auth_type", "")
                    agent_name = row.get("agent_name", "")
                    rounds = int(row.get("rounds", 0))
                    message_count = int(row.get("message_count_excluding_opening", 0))
                    voice_count = int(row.get("voice_message_count", 0))

                    # 前10名高亮
                    tr_class = "top10" if rank <= 10 else ""

                    # 认证类型标签
                    auth_badge = ""
                    if auth_type == "GOOGLE":
                        auth_badge = '<span class="badge google">🔐 Google</span>'
                    elif auth_type == "GUEST":
                        auth_badge = '<span class="badge guest">🏷️ 游客</span>'

                    html_content += f"""
                    <tr class="{tr_class}">
                        <td><strong>#{rank}</strong></td>
                        <td style="font-family: monospace; font-size: 12px;">{user_id[:20]}...</td>
                        <td>{nickname}</td>
                        <td>{auth_badge}</td>
                        <td>{agent_name}</td>
                        <td><span class="rounds-badge">{rounds}</span></td>
                        <td>{message_count}</td>
                        <td>{voice_count if voice_count > 0 else '-'}</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
        </div>
"""
            else:
                html_content += """
        <div class="long-conversations-table">
            <div class="stats-section-title" style="margin-bottom: 20px;">🏆 长对话会话排行（Top 50）</div>
            <div style="font-size: 12px; color: #666; margin-bottom: 15px;">
                暂无包含用户消息的长对话会话记录
            </div>
        </div>
"""

            html_content += """
        <div class="filter-box">
            <div class="filter-title">📊 按认证类型筛选</div>
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterByAuthType('ALL')">全部</button>
                <button class="filter-btn" onclick="filterByAuthType('GUEST')">🏷️ 游客</button>
                <button class="filter-btn" onclick="filterByAuthType('GOOGLE')">🔐 Google</button>
            </div>
        </div>

        <div class="filter-box">
            <div class="filter-title">💬 按会话类型筛选</div>
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterBySessionType('ALL')">全部</button>
                <button class="filter-btn" onclick="filterBySessionType('WITH_USER_MSG')">✅ 有用户消息</button>
                <button class="filter-btn" onclick="filterBySessionType('ONLY_OPENING')">👁️ 仅浏览开场白</button>
            </div>
        </div>

        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 搜索用户ID、昵称、邮箱、角色名称..." onkeyup="filterUsers()">
        </div>

        <div id="userList">
"""

            # 先计算每个用户的总消息数（排除开场白），用于排序
            user_message_counts = {}
            for user_id, user_sessions in user_sessions_detail_df.groupby("user_id"):
                user_chat_ids = user_sessions["chat_id"].tolist()
                user_messages = messages_excluding_opening[
                    messages_excluding_opening["chat_id"].isin(user_chat_ids)
                ]
                user_message_counts[user_id] = len(user_messages)

            # 按消息数降序排序用户
            sorted_user_ids = sorted(
                user_message_counts.keys(),
                key=lambda x: user_message_counts[x],
                reverse=True,
            )

            # 按消息数降序生成用户卡片
            for user_id in sorted_user_ids:
                user_sessions = user_sessions_detail_df[
                    user_sessions_detail_df["user_id"] == user_id
                ]
                user_info = user_sessions.iloc[0]
                auth_type = user_info["auth_type"]
                user_created_at = pd.to_datetime(user_info["user_created_at"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                session_count = len(user_sessions)
                total_user_messages = user_message_counts[user_id]

                # 检查用户是否有包含用户消息的会话
                user_chat_ids = user_sessions["chat_id"].tolist()
                has_user_messages = any(
                    chat_id in chat_ids_with_user_msgs for chat_id in user_chat_ids
                )
                has_user_messages_str = "true" if has_user_messages else "false"

                # 获取nickname和email
                nickname = user_info.get("nickname", None)
                email = user_info.get("email", None)

                # HTML转义
                nickname_escaped = (
                    html.escape(nickname) if nickname and pd.notna(nickname) else None
                )
                email_escaped = (
                    html.escape(email) if email and pd.notna(email) else None
                )

                # 构建用户显示名称
                user_display = user_id[:30] + "..."
                if nickname_escaped:
                    user_display += (
                        f' <span class="user-nickname">({nickname_escaped})</span>'
                    )

                html_content += f"""
        <div class="user-card" data-user-id="{user_id}" data-auth-type="{auth_type}" data-nickname="{nickname_escaped or ''}" data-email="{email_escaped or ''}" data-has-user-messages="{has_user_messages_str}">
            <div class="user-header" onclick="toggleUser(this)">
                <div class="user-info">
                    <div class="user-info-item">
                        <label>用户信息</label>
                        <value>{user_display}"""

                if email_escaped:
                    html_content += (
                        f'<br><span class="user-email">{email_escaped}</span>'
                    )

                html_content += f"""</value>
                    </div>
                    <div class="user-info-item">
                        <label>认证类型</label>
                        <value><span class="badge {auth_type.lower()}">{auth_type}</span></value>
                    </div>
                    <div class="user-info-item">
                        <label>注册时间</label>
                        <value>{user_created_at}</value>
                    </div>
                    <div class="user-info-item">
                        <label>会话数</label>
                        <value>{session_count}</value>
                    </div>
                    <div class="user-info-item">
                        <label>消息数</label>
                        <value>{total_user_messages}</value>
                    </div>
                </div>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="user-content">
"""

                # 为每个会话生成内容
                for idx, (_, session) in enumerate(user_sessions.iterrows(), 1):
                    chat_id = session["chat_id"]
                    agent_name = session.get("agent_name", "未知角色")
                    message_count = session.get("message_count", 0)

                    html_content += f"""
                <div class="session-card">
                    <div class="session-header">
                        <div class="session-title">💬 会话 {idx}: {agent_name}</div>
                        <div class="session-meta">
                            <span>ID: {chat_id[:20]}...</span> | 
                            <span>{message_count} 条消息</span>
                        </div>
                    </div>
                    <div class="messages">
"""

                    # 获取该会话的消息
                    session_messages = messages_df[
                        messages_df["chat_id"] == chat_id
                    ].sort_values("created_at")

                    if not session_messages.empty:
                        for _, msg in session_messages.iterrows():
                            msg_type = msg["message_type"]
                            content = msg["content"]
                            timestamp = pd.to_datetime(msg["created_at"]).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )

                            role = "user" if msg_type == "human" else "assistant"
                            role_text = "👤 用户" if role == "user" else "🤖 AI"

                            # 限制内容长度
                            if content and len(content) > 500:
                                content = content[:500] + "..."

                            # HTML 转义防止 XSS
                            content_escaped = (
                                html.escape(content) if content else "(空消息)"
                            )

                            html_content += f"""
                        <div class="message {role}">
                            <div class="message-header">
                                <span class="message-role">{role_text}</span>
                                <span class="message-time">{timestamp}</span>
                            </div>
                            <div class="message-content">{content_escaped}</div>
                        </div>
"""
                    else:
                        html_content += """
                        <div class="no-messages">暂无对话记录</div>
"""

                    html_content += """
                    </div>
                </div>
"""

                html_content += """
            </div>
        </div>
"""

        html_content += """
        </div>
    </div>

    <script>
        let currentAuthTypeFilter = 'ALL';
        let currentSessionTypeFilter = 'ALL';
        
        function toggleUser(header) {
            const content = header.nextElementSibling;
            const icon = header.querySelector('.toggle-icon');
            
            content.classList.toggle('expanded');
            icon.classList.toggle('expanded');
        }

        function filterByAuthType(authType) {
            currentAuthTypeFilter = authType;
            
            // 更新按钮状态（只更新认证类型按钮）
            const authButtons = document.querySelectorAll('.filter-box:nth-child(2) .filter-btn');
            authButtons.forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // 应用过滤
            applyFilters();
        }

        function filterBySessionType(sessionType) {
            currentSessionTypeFilter = sessionType;
            
            // 更新按钮状态（只更新会话类型按钮）
            const sessionButtons = document.querySelectorAll('.filter-box:nth-child(3) .filter-btn');
            sessionButtons.forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // 应用过滤
            applyFilters();
        }

        function filterUsers() {
            applyFilters();
        }

        function applyFilters() {
            const searchInput = document.getElementById('searchInput');
            const searchFilter = searchInput.value.toLowerCase();
            const userCards = document.querySelectorAll('.user-card');
            
            userCards.forEach(card => {
                const userId = card.getAttribute('data-user-id').toLowerCase();
                const authType = card.getAttribute('data-auth-type');
                const nickname = card.getAttribute('data-nickname').toLowerCase();
                const email = card.getAttribute('data-email').toLowerCase();
                const hasUserMessages = card.getAttribute('data-has-user-messages') === 'true';
                const text = card.textContent.toLowerCase();
                
                // 认证类型过滤
                let authTypeMatch = currentAuthTypeFilter === 'ALL' || authType === currentAuthTypeFilter;
                
                // 会话类型过滤
                let sessionTypeMatch = true;
                if (currentSessionTypeFilter === 'WITH_USER_MSG') {
                    sessionTypeMatch = hasUserMessages;
                } else if (currentSessionTypeFilter === 'ONLY_OPENING') {
                    sessionTypeMatch = !hasUserMessages;
                }
                
                // 搜索过滤
                let searchMatch = !searchFilter || 
                                 userId.includes(searchFilter) || 
                                 nickname.includes(searchFilter) || 
                                 email.includes(searchFilter) || 
                                 text.includes(searchFilter);
                
                // 同时满足所有条件才显示
                if (authTypeMatch && sessionTypeMatch && searchMatch) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

        filepath = self.output_dir / "conversations_detailed.html"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"已保存详细对话报告: {filepath}")

    def generate_agent_analytics_html_report(
        self,
        agent_analytics_df: pd.DataFrame,
        date_range: Tuple[datetime, datetime],
    ):
        """生成角色数据分析的独立HTML报告页面"""
        if agent_analytics_df.empty:
            logger.warning("角色分析数据为空，跳过生成HTML报告")
            return

        # 为每个图表准备排序后的数据（按各自指标降序排序，取Top 50）
        # 保持降序排序，横向柱状图使用反转Y轴让最大值在顶部显示
        df_chat_users = agent_analytics_df.sort_values(
            "chat_user_count", ascending=False
        ).head(50)
        df_avg_rounds = agent_analytics_df.sort_values(
            "avg_rounds_per_user", ascending=False
        ).head(50)
        df_ge_5_ratio = agent_analytics_df.sort_values(
            "ge_5_rounds_ratio", ascending=False
        ).head(50)
        df_ge_10_ratio = agent_analytics_df.sort_values(
            "ge_10_rounds_ratio", ascending=False
        ).head(50)

        # 添加数据验证日志
        logger.info(
            f"图表数据准备完成 - "
            f"聊天人数图表: {len(df_chat_users)} 个角色, "
            f"人均轮数图表: {len(df_avg_rounds)} 个角色, "
            f"≥5轮占比图表: {len(df_ge_5_ratio)} 个角色, "
            f"≥10轮占比图表: {len(df_ge_10_ratio)} 个角色"
        )
        if not df_chat_users.empty:
            logger.info(
                f"聊天人数Top 3: {df_chat_users.head(3)[['agent_name', 'chat_user_count']].to_dict('records')}"
            )

        # 创建图表 - 使用横向柱状图避免标签重叠
        fig = make_subplots(
            rows=4,
            cols=1,
            subplot_titles=(
                "各角色聊天人数（Top 50）",
                "各角色人均聊天轮数（Top 50）",
                "各角色≥5轮聊天占比（Top 50）",
                "各角色≥10轮聊天占比（Top 50）",
            ),
            vertical_spacing=0.10,
            specs=[
                [{"type": "bar"}],
                [{"type": "bar"}],
                [{"type": "bar"}],
                [{"type": "bar"}],
            ],
        )

        # 图表1: 聊天人数（横向）
        fig.add_trace(
            go.Bar(
                y=df_chat_users["agent_name"],
                x=df_chat_users["chat_user_count"],
                name="聊天人数",
                orientation="h",
                showlegend=False,
                marker_color="lightblue",
            ),
            row=1,
            col=1,
        )

        # 图表2: 人均轮数（横向）
        fig.add_trace(
            go.Bar(
                y=df_avg_rounds["agent_name"],
                x=df_avg_rounds["avg_rounds_per_user"],
                name="人均轮数",
                orientation="h",
                showlegend=False,
                marker_color="lightcoral",
            ),
            row=2,
            col=1,
        )

        # 图表3: ≥5轮占比（横向）
        fig.add_trace(
            go.Bar(
                y=df_ge_5_ratio["agent_name"],
                x=df_ge_5_ratio["ge_5_rounds_ratio"],
                name="≥5轮占比(%)",
                orientation="h",
                showlegend=False,
                marker_color="lightgreen",
            ),
            row=3,
            col=1,
        )

        # 图表4: ≥10轮占比（横向）
        fig.add_trace(
            go.Bar(
                y=df_ge_10_ratio["agent_name"],
                x=df_ge_10_ratio["ge_10_rounds_ratio"],
                name="≥10轮占比(%)",
                orientation="h",
                showlegend=False,
                marker_color="lightsalmon",
            ),
            row=4,
            col=1,
        )

        # 更新布局 - 增加高度以容纳50个角色（每个角色约需80px高度）
        fig.update_layout(
            height=4200,
            title_text=f"角色数据分析报告 ({date_range[0].date()} 至 {date_range[1].date()})",
            showlegend=False,
        )

        # 更新坐标轴标签（横向图表，Y轴是角色名称，X轴是数值）
        # 数据按降序排序，使用反转Y轴让最大值显示在顶部
        # 设置categoryorder和tickmode确保显示所有标签
        fig.update_yaxes(
            title_text="角色名称",
            row=1,
            col=1,
            autorange="reversed",
            categoryorder="total descending",
            tickmode="linear",
            dtick=1,
        )
        fig.update_xaxes(title_text="聊天人数", row=1, col=1)

        fig.update_yaxes(
            title_text="角色名称",
            row=2,
            col=1,
            autorange="reversed",
            categoryorder="total descending",
            tickmode="linear",
            dtick=1,
        )
        fig.update_xaxes(title_text="人均轮数", row=2, col=1)

        fig.update_yaxes(
            title_text="角色名称",
            row=3,
            col=1,
            autorange="reversed",
            categoryorder="total descending",
            tickmode="linear",
            dtick=1,
        )
        fig.update_xaxes(title_text="占比 (%)", row=3, col=1)

        fig.update_yaxes(
            title_text="角色名称",
            row=4,
            col=1,
            autorange="reversed",
            categoryorder="total descending",
            tickmode="linear",
            dtick=1,
        )
        fig.update_xaxes(title_text="占比 (%)", row=4, col=1)

        # 保存 HTML
        filepath = self.output_dir / "agent_analytics_report.html"
        fig.write_html(str(filepath))
        logger.info(f"已保存角色分析HTML报告: {filepath}")

        # 同时保存CSV文件（按聊天人数排序）
        csv_sorted_df = agent_analytics_df.sort_values(
            "chat_user_count", ascending=False
        )
        csv_filepath = self.output_dir / "agent_analytics.csv"
        csv_sorted_df.to_csv(csv_filepath, index=False, encoding="utf-8-sig")
        logger.info(f"已保存角色分析CSV: {csv_filepath}")


def process_data(
    analytics: UserAnalytics,
    start_date: datetime,
    end_date: datetime,
    guest_limit: int = 10,
    google_limit: int = 100,
) -> Dict[str, Any]:
    """处理数据并返回各种统计结果"""
    results = {}

    # 1. 新用户统计
    logger.info("查询新用户数据...")
    daily_users_df = analytics.get_new_users(start_date, end_date)
    results["daily_users"] = daily_users_df

    if not daily_users_df.empty:
        total_users = daily_users_df["count"].sum()
        guest_users = daily_users_df[daily_users_df["auth_type"] == "GUEST"][
            "count"
        ].sum()
        google_users = daily_users_df[daily_users_df["auth_type"] == "GOOGLE"][
            "count"
        ].sum()
        logger.info(
            f"找到 {total_users} 个新用户 (游客: {guest_users}, Google: {google_users})"
        )
    else:
        logger.warning("未找到新用户数据")

    # 1.5. 新用户邮箱列表
    logger.info("查询新用户邮箱列表...")
    new_users_email_df = analytics.get_new_users_email_list(start_date, end_date)
    results["new_users_email_list"] = new_users_email_df
    if not new_users_email_df.empty:
        logger.info(f"找到 {len(new_users_email_df)} 个有邮箱的新用户")
    else:
        logger.warning("未找到有邮箱的新用户")

    # 2. 用户聊天活动
    logger.info("查询用户聊天活动...")
    user_chat_df = analytics.get_user_chat_activity(start_date, end_date)
    results["user_chat_raw"] = user_chat_df  # 保存原始数据用于后续处理

    if not user_chat_df.empty:
        # 聚合每个用户的聊天信息
        user_activity = []
        user_sessions_detail = []  # 存储每个用户的 session 详情

        for user_id, group in user_chat_df.groupby("user_id"):
            chat_ids = group[group["chat_id"].notna()]["chat_id"].tolist()
            chat_count = len(chat_ids)
            agent_names = (
                group[group["agent_name"].notna()]["agent_name"].unique().tolist()
            )

            user_activity.append(
                {
                    "user_id": user_id,
                    "auth_type": group.iloc[0]["auth_type"],
                    "created_at": group.iloc[0]["created_at"],
                    "session_count": chat_count,  # Session 数量
                    "agent_names": ", ".join(agent_names) if agent_names else "",
                }
            )

            # 记录每个用户的 session 详情
            for _, row in group[group["chat_id"].notna()].iterrows():
                user_sessions_detail.append(
                    {
                        "user_id": user_id,
                        "auth_type": row["auth_type"],
                        "user_created_at": group.iloc[0]["created_at"],
                        "nickname": group.iloc[0].get("nickname"),
                        "email": group.iloc[0].get("email"),
                        "chat_id": row["chat_id"],
                        "agent_name": row["agent_name"],
                    }
                )

        user_activity_df = pd.DataFrame(user_activity)
        results["user_activity"] = user_activity_df
        results["user_sessions_detail"] = pd.DataFrame(user_sessions_detail)

        active_users = len(user_activity_df[user_activity_df["session_count"] > 0])
        logger.info(f"找到 {active_users} 个活跃聊天用户")
    else:
        logger.warning("未找到用户聊天活动数据")
        results["user_activity"] = pd.DataFrame()
        results["user_sessions_detail"] = pd.DataFrame()

    # 3. 对话轮数统计
    logger.info("查询对话轮数...")
    rounds_df = analytics.get_conversation_rounds(start_date)

    if not rounds_df.empty:
        logger.info(f"统计 {len(rounds_df)} 个聊天会话")

        # 合并到用户聊天活动中
        if not user_chat_df.empty:
            chat_rounds = rounds_df.set_index("chat_id")["message_count"].to_dict()
            chat_rounds_excluding_opening = rounds_df.set_index("chat_id")[
                "message_count_excluding_opening"
            ].to_dict()

            # 为每个用户计算总对话轮数（排除开场白）
            if "user_activity" in results and not results["user_activity"].empty:
                user_rounds = []
                for _, row in results["user_activity"].iterrows():
                    user_chats = user_chat_df[user_chat_df["user_id"] == row["user_id"]]
                    total_rounds = sum(
                        chat_rounds_excluding_opening.get(chat_id, 0)
                        for chat_id in user_chats["chat_id"].dropna()
                    )
                    user_rounds.append(total_rounds)
                results["user_activity"]["total_rounds"] = user_rounds

            # 为每个 session 添加消息数（包含和排除开场白两个版本）
            if (
                "user_sessions_detail" in results
                and not results["user_sessions_detail"].empty
            ):
                results["user_sessions_detail"]["message_count"] = (
                    results["user_sessions_detail"]["chat_id"]
                    .map(chat_rounds)
                    .fillna(0)
                    .astype(int)
                )
                results["user_sessions_detail"]["message_count_excluding_opening"] = (
                    results["user_sessions_detail"]["chat_id"]
                    .map(chat_rounds_excluding_opening)
                    .fillna(0)
                    .astype(int)
                )

        # 热门角色统计（排除开场白）
        if not user_chat_df.empty:
            agent_stats = []
            for agent_id, group in user_chat_df[
                user_chat_df["agent_id"].notna()
            ].groupby("agent_id"):
                user_count = group["user_id"].nunique()
                agent_name = group.iloc[0]["agent_name"]
                chat_ids = group["chat_id"].dropna().unique()
                total_rounds = sum(
                    rounds_df[rounds_df["chat_id"].isin(chat_ids)][
                        "message_count_excluding_opening"
                    ]
                )
                agent_stats.append(
                    {
                        "agent_name": agent_name,
                        "user_count": user_count,
                        "total_rounds": int(total_rounds),
                    }
                )
            popular_agents_df = pd.DataFrame(agent_stats).sort_values(
                "user_count", ascending=False
            )
            results["popular_agents"] = popular_agents_df
        else:
            results["popular_agents"] = pd.DataFrame()

        # 角色数据分析统计
        logger.info("查询角色数据分析...")
        agent_analytics_df = analytics.get_agent_analytics(start_date, end_date)
        results["agent_analytics"] = agent_analytics_df
        if not agent_analytics_df.empty:
            logger.info(
                f"统计了 {len(agent_analytics_df)} 个角色的数据，"
                f"总聊天用户数: {agent_analytics_df['chat_user_count'].sum()}"
            )
        else:
            logger.warning("未找到角色分析数据")

        # 对话轮数分布（排除开场白），按10条消息（约5轮对话）一档
        bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, float("inf")]
        labels = [
            "1-10",
            "11-20",
            "21-30",
            "31-40",
            "41-50",
            "51-60",
            "61-70",
            "71-80",
            "81-90",
            "91-100",
            "100+",
        ]
        rounds_df["rounds_range"] = pd.cut(
            rounds_df["message_count_excluding_opening"],
            bins=bins,
            labels=labels,
            right=True,
        )
        rounds_dist = rounds_df["rounds_range"].value_counts().sort_index()
        rounds_dist_df = pd.DataFrame(
            {"rounds_range": rounds_dist.index, "count": rounds_dist.values}
        )
        results["rounds_distribution"] = rounds_dist_df

        # 按用户统计的轮数分布
        if (
            "user_sessions_detail" in results
            and not results["user_sessions_detail"].empty
        ):
            # 计算每个用户的总轮数
            user_total_rounds = {}
            for user_id, user_sessions in results["user_sessions_detail"].groupby(
                "user_id"
            ):
                total_rounds = user_sessions["message_count_excluding_opening"].sum()
                user_total_rounds[user_id] = total_rounds

            # 按10条消息区间分组统计用户数
            user_rounds_series = pd.Series(list(user_total_rounds.values()))
            user_rounds_series = user_rounds_series[
                user_rounds_series > 0
            ]  # 只统计有对话的用户

            user_rounds_dist = pd.cut(
                user_rounds_series, bins=bins, labels=labels, right=True
            )
            user_rounds_counts = user_rounds_dist.value_counts().sort_index()
            user_rounds_dist_df = pd.DataFrame(
                {
                    "rounds_range": user_rounds_counts.index,
                    "user_count": user_rounds_counts.values,
                }
            )
            results["user_rounds_distribution"] = user_rounds_dist_df
        else:
            results["user_rounds_distribution"] = pd.DataFrame()
    else:
        logger.warning("未找到对话轮数数据")
        results["popular_agents"] = pd.DataFrame()
        results["rounds_distribution"] = pd.DataFrame()
        results["user_rounds_distribution"] = pd.DataFrame()

    # 4. 语音使用统计
    if "user_sessions_detail" in results and not results["user_sessions_detail"].empty:
        logger.info("查询语音使用数据...")
        all_chat_ids = results["user_sessions_detail"]["chat_id"].unique().tolist()
        if all_chat_ids:
            voice_usage_df = analytics.get_voice_usage(all_chat_ids)
            if not voice_usage_df.empty:
                # 为每个session添加语音消息数
                voice_counts = voice_usage_df.set_index("chat_id")[
                    "voice_message_count"
                ].to_dict()
                results["user_sessions_detail"]["voice_message_count"] = (
                    results["user_sessions_detail"]["chat_id"]
                    .map(voice_counts)
                    .fillna(0)
                    .astype(int)
                )

                # 按用户汇总语音使用
                user_voice_usage = []
                for user_id, user_sessions in results["user_sessions_detail"].groupby(
                    "user_id"
                ):
                    total_voice = user_sessions["voice_message_count"].sum()
                    if total_voice > 0:
                        user_voice_usage.append(
                            {
                                "user_id": user_id,
                                "auth_type": user_sessions.iloc[0]["auth_type"],
                                "voice_message_count": int(total_voice),
                            }
                        )
                results["user_voice_usage"] = pd.DataFrame(user_voice_usage)
                logger.info(f"找到 {len(user_voice_usage)} 个用户使用了语音功能")
            else:
                results["user_voice_usage"] = pd.DataFrame()
                results["user_sessions_detail"]["voice_message_count"] = 0
        else:
            results["user_voice_usage"] = pd.DataFrame()
    else:
        results["user_voice_usage"] = pd.DataFrame()

    # 5. 获取对话详情
    if "user_sessions_detail" in results and not results["user_sessions_detail"].empty:
        logger.info("查询对话详情...")
        all_chat_ids = results["user_sessions_detail"]["chat_id"].unique().tolist()
        if all_chat_ids:
            logger.info(f"准备查询 {len(all_chat_ids)} 个会话的对话消息...")

            # 批量查询，避免一次查询太多
            batch_size = 500
            all_messages = []
            for i in range(0, len(all_chat_ids), batch_size):
                batch_ids = all_chat_ids[i : i + batch_size]
                logger.info(
                    f"查询第 {i//batch_size + 1} 批 ({len(batch_ids)} 个会话)..."
                )
                batch_messages = analytics.get_chat_messages(batch_ids)
                if not batch_messages.empty:
                    all_messages.append(batch_messages)

            if all_messages:
                messages_df = pd.concat(all_messages, ignore_index=True)
                results["messages"] = messages_df
                logger.info(f"找到 {len(messages_df)} 条对话消息")
            else:
                logger.warning("未找到任何对话消息")
                results["messages"] = pd.DataFrame()
        else:
            results["messages"] = pd.DataFrame()
    else:
        results["messages"] = pd.DataFrame()

    # 6. 计算统计指标
    if "user_sessions_detail" in results and not results["user_sessions_detail"].empty:
        # 计算有用户消息的session（排除仅浏览开场白）
        if "messages" in results and not results["messages"].empty:
            user_messages_df = results["messages"][
                results["messages"]["message_type"] == "human"
            ]
            active_chat_ids = user_messages_df["chat_id"].unique()
            active_sessions = results["user_sessions_detail"][
                results["user_sessions_detail"]["chat_id"].isin(active_chat_ids)
            ]

            if not active_sessions.empty:
                # 第一部分：统计类型
                total_active_sessions = len(active_sessions)  # 包含用户消息的会话数
                total_active_users = active_sessions[
                    "user_id"
                ].nunique()  # 发起聊天的人数
                total_user_messages = len(user_messages_df)  # 总发送消息数

                # 第二部分：用户维度（仅统计发送聊天的用户）
                avg_messages_per_user = (
                    total_user_messages / total_active_users
                    if total_active_users > 0
                    else 0
                )  # 平均发送消息数
                avg_sessions_per_user = (
                    total_active_sessions / total_active_users
                    if total_active_users > 0
                    else 0
                )  # 平均会话数

                # 计算总语音请求数（排除开场白）
                total_voice_requests = 0
                if "voice_message_count" in results["user_sessions_detail"].columns:
                    total_voice_requests = results["user_sessions_detail"][
                        results["user_sessions_detail"]["chat_id"].isin(active_chat_ids)
                    ]["voice_message_count"].sum()

                avg_voice_requests_per_user = (
                    total_voice_requests / total_active_users
                    if total_active_users > 0
                    else 0
                )  # 平均发起语音请求数

                # 第三部分：会话维度
                # 每个会话平均轮数：1轮 = 1条用户消息 + 1条AI回复
                # 总消息数（排除开场白）包含用户消息和AI回复，所以轮数 = 总消息数 / 2
                # 或者：总用户消息数就是轮数（因为每轮包含1条用户消息）
                total_messages_excluding_opening = 0
                if (
                    "message_count_excluding_opening"
                    in results["user_sessions_detail"].columns
                ):
                    total_messages_excluding_opening = results["user_sessions_detail"][
                        results["user_sessions_detail"]["chat_id"].isin(active_chat_ids)
                    ]["message_count_excluding_opening"].sum()

                # 每个会话平均轮数 = 总用户消息数 / 会话数（因为每轮包含1条用户消息）
                avg_rounds_per_session = (
                    total_user_messages / total_active_sessions
                    if total_active_sessions > 0
                    else 0
                )

                results["stats"] = {
                    # 统计类型
                    "total_new_users": (
                        results.get("daily_users", pd.DataFrame())["count"].sum()
                        if "daily_users" in results and not results["daily_users"].empty
                        else 0
                    ),
                    "total_chat_initiators": total_active_users,  # 发起聊天的人数
                    "total_user_messages": total_user_messages,  # 总发送消息数
                    "total_active_sessions": total_active_sessions,  # 包含用户消息的会话数
                    "total_voice_requests": int(
                        total_voice_requests
                    ),  # 总语音请求数（排除开场白）
                    # 用户维度
                    "avg_messages_per_user": avg_messages_per_user,  # 平均发送消息数
                    "avg_sessions_per_user": avg_sessions_per_user,  # 平均会话数
                    "avg_voice_requests_per_user": avg_voice_requests_per_user,  # 平均发起语音请求数
                    # 会话维度
                    "avg_rounds_per_session": avg_rounds_per_session,  # 每个会话平均轮数
                }
                logger.info(
                    f"统计指标 - "
                    f"新增用户: {results['stats']['total_new_users']}, "
                    f"发起聊天人数: {total_active_users}, "
                    f"总发送消息: {total_user_messages}, "
                    f"总会话数: {total_active_sessions}, "
                    f"总语音请求: {int(total_voice_requests)}, "
                    f"平均消息数/用户: {avg_messages_per_user:.2f}, "
                    f"平均会话数/用户: {avg_sessions_per_user:.2f}, "
                    f"平均语音请求/用户: {avg_voice_requests_per_user:.2f}, "
                    f"平均轮数/会话: {avg_rounds_per_session:.2f}"
                )
            else:
                total_new_users = (
                    results.get("daily_users", pd.DataFrame())["count"].sum()
                    if "daily_users" in results and not results["daily_users"].empty
                    else 0
                )
                results["stats"] = {
                    "total_new_users": total_new_users,
                    "total_chat_initiators": 0,
                    "total_user_messages": 0,
                    "total_active_sessions": 0,
                    "total_voice_requests": 0,
                    "avg_messages_per_user": 0,
                    "avg_sessions_per_user": 0,
                    "avg_voice_requests_per_user": 0,
                    "avg_rounds_per_session": 0,
                }
        else:
            total_new_users = (
                results.get("daily_users", pd.DataFrame())["count"].sum()
                if "daily_users" in results and not results["daily_users"].empty
                else 0
            )
            results["stats"] = {
                "total_new_users": total_new_users,
                "total_chat_initiators": 0,
                "total_user_messages": 0,
                "total_active_sessions": 0,
                "total_voice_requests": 0,
                "avg_messages_per_user": 0,
                "avg_sessions_per_user": 0,
                "avg_voice_requests_per_user": 0,
                "avg_rounds_per_session": 0,
            }
    else:
        total_new_users = (
            results.get("daily_users", pd.DataFrame())["count"].sum()
            if "daily_users" in results and not results["daily_users"].empty
            else 0
        )
        results["stats"] = {
            "total_new_users": total_new_users,
            "total_chat_initiators": 0,
            "total_user_messages": 0,
            "total_active_sessions": 0,
            "avg_messages_per_user": 0,
            "avg_sessions_per_user": 0,
            "avg_voice_requests_per_user": 0,
            "avg_rounds_per_session": 0,
        }

    # 7. 查询达到聊天限制的用户
    logger.info("查询达到聊天限制的用户...")
    users_hitting_limit_df = analytics.get_users_hitting_chat_limit(
        start_date, end_date, guest_limit, google_limit
    )
    results["users_hitting_chat_limit"] = users_hitting_limit_df

    if not users_hitting_limit_df.empty:
        total_hitting = len(users_hitting_limit_df)
        guest_hitting = len(
            users_hitting_limit_df[users_hitting_limit_df["auth_type"] == "GUEST"]
        )
        google_hitting = len(
            users_hitting_limit_df[users_hitting_limit_df["auth_type"] == "GOOGLE"]
        )
        unique_users = users_hitting_limit_df["user_id"].nunique()
        logger.info(
            f"找到 {total_hitting} 条达到限制的记录 (游客: {guest_hitting}, Google: {google_hitting}), "
            f"涉及 {unique_users} 个用户"
        )
    else:
        logger.info("未找到达到聊天限制的用户")

    # 8. 长对话会话列表（按轮数降序）
    if "user_sessions_detail" in results and not results["user_sessions_detail"].empty:
        if "messages" in results and not results["messages"].empty:
            user_messages_df = results["messages"][
                results["messages"]["message_type"] == "human"
            ]
            chat_ids_with_user_msgs = user_messages_df["chat_id"].unique()

            # 筛选有用户消息的会话
            active_sessions = results["user_sessions_detail"][
                results["user_sessions_detail"]["chat_id"].isin(chat_ids_with_user_msgs)
            ].copy()

            if not active_sessions.empty:
                # 计算每个会话的用户消息数（作为轮数）
                user_message_counts_by_chat = (
                    user_messages_df["chat_id"].value_counts().to_dict()
                )
                active_sessions["rounds"] = (
                    active_sessions["chat_id"]
                    .map(lambda x: user_message_counts_by_chat.get(x, 0))
                    .astype(int)
                )

                # 按轮数降序排序，取Top 50
                long_conversations = active_sessions.sort_values(
                    "rounds", ascending=False
                ).head(50)

                # 添加排名
                long_conversations = long_conversations.reset_index(drop=True)
                long_conversations["rank"] = long_conversations.index + 1

                results["long_conversations"] = long_conversations
                logger.info(f"生成长对话会话列表: {len(long_conversations)} 条记录")
            else:
                results["long_conversations"] = pd.DataFrame()
        else:
            results["long_conversations"] = pd.DataFrame()
    else:
        results["long_conversations"] = pd.DataFrame()

    return results


def load_database_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载数据库配置

    优先级：
    1. 命令行指定的配置文件
    2. 项目根目录的 config.yaml
    3. 环境变量
    """
    db_config = {}

    # 尝试从配置文件加载
    if config_file:
        config_path = Path(config_file)
    else:
        # 尝试项目根目录的配置文件
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                db_section = config.get("database", {})
                db_config = {
                    "host": db_section.get("host"),
                    "port": db_section.get("port"),
                    "user": db_section.get("user"),
                    "password": db_section.get("password"),
                    "dbname": db_section.get("db"),
                }
                logger.info(f"从配置文件加载数据库配置: {config_path}")
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")

    # 环境变量覆盖（如果有）
    db_config["host"] = os.getenv("DB_HOST", db_config.get("host", "localhost"))
    db_config["port"] = int(os.getenv("DB_PORT", db_config.get("port", 5432)))
    db_config["user"] = os.getenv("DB_USER", db_config.get("user", "postgres"))
    db_config["password"] = os.getenv("DB_PASSWORD", db_config.get("password", ""))
    db_config["dbname"] = os.getenv("DB_NAME", db_config.get("dbname", "inty"))

    return db_config


def load_chat_limits(config_file: Optional[str] = None) -> Dict[str, int]:
    """加载聊天限制配置

    优先级：
    1. 命令行指定的配置文件
    2. 项目根目录的 config.yaml
    3. 默认值（guest=10, google=100）

    Returns:
        Dict[str, int]: {"guest": 10, "google": 100}
    """
    default_limits = {
        "guest": 10,
        "google": 100,
    }

    # 尝试从配置文件加载
    if config_file:
        config_path = Path(config_file)
    else:
        # 尝试项目根目录的配置文件
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                limits_section = config.get("app", {}).get("limits", {})
                guest_limit = limits_section.get(
                    "guest_user_chat_24h_limit", default_limits["guest"]
                )
                google_limit = limits_section.get(
                    "free_user_chat_24h_limit", default_limits["google"]
                )
                return {
                    "guest": int(guest_limit),
                    "google": int(google_limit),
                }
        except Exception as e:
            logger.warning(f"读取配置限制值失败: {e}，使用默认值")

    logger.info(
        f"聊天限制配置: guest={default_limits['guest']}, google={default_limits['google']}"
    )
    return default_limits


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="用户行为分析脚本")

    # 时间范围参数
    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument("--last-days", type=int, help="分析最近 N 天的数据")
    time_group.add_argument("--start-date", type=str, help="开始日期 (YYYY-MM-DD)")

    parser.add_argument("--end-date", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./reports",
        help="输出目录 (默认: ./reports)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示统计信息，不生成报告",
    )

    # 数据库配置参数
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--db-host", type=str, help="数据库主机")
    parser.add_argument("--db-port", type=int, help="数据库端口")
    parser.add_argument("--db-user", type=str, help="数据库用户名")
    parser.add_argument("--db-password", type=str, help="数据库密码")
    parser.add_argument("--db-name", type=str, help="数据库名称")

    args = parser.parse_args()

    # 验证日期参数
    if args.start_date and not args.end_date:
        parser.error("--start-date 需要配合 --end-date 使用")

    return args


def generate_conversation_report(
    sessions_df: pd.DataFrame, messages_df: pd.DataFrame
) -> str:
    """生成对话详情文本报告"""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("用户对话详情报告")
    report_lines.append("=" * 80)
    report_lines.append("")

    # 按用户分组
    for user_id, user_sessions in sessions_df.groupby("user_id"):
        user_info = user_sessions.iloc[0]
        report_lines.append(f"\n{'=' * 80}")
        report_lines.append(f"用户ID: {user_id}")
        report_lines.append(f"认证类型: {user_info['auth_type']}")
        report_lines.append(f"注册时间: {user_info['user_created_at']}")
        report_lines.append(f"Session 数量: {len(user_sessions)}")
        report_lines.append(f"{'=' * 80}\n")

        # 遍历该用户的每个 session
        for idx, (_, session) in enumerate(user_sessions.iterrows(), 1):
            chat_id = session["chat_id"]
            agent_name = session["agent_name"]
            message_count = session.get("message_count", 0)

            report_lines.append(f"\n  Session {idx}:")
            report_lines.append(f"  Chat ID: {chat_id}")
            report_lines.append(f"  角色: {agent_name}")
            report_lines.append(f"  消息数: {message_count}")
            report_lines.append(f"  {'-' * 76}")

            # 获取该 session 的对话
            session_messages = messages_df[
                messages_df["chat_id"] == chat_id
            ].sort_values("created_at")

            if not session_messages.empty:
                report_lines.append("  对话内容:")
                for msg_idx, (_, msg) in enumerate(session_messages.iterrows(), 1):
                    msg_type = msg["message_type"]
                    content = msg["content"]
                    timestamp = msg["created_at"]

                    # 限制内容长度
                    if content and len(content) > 200:
                        content = content[:200] + "..."

                    speaker = "用户" if msg_type == "human" else "AI"
                    report_lines.append(f"    [{msg_idx}] {speaker} ({timestamp}):")
                    report_lines.append(f"        {content}")
                    report_lines.append("")
            else:
                report_lines.append("  (无对话记录)")

            report_lines.append("")

    return "\n".join(report_lines)


def calculate_date_range(args: argparse.Namespace) -> Tuple[datetime, datetime]:
    """计算日期范围"""
    now = datetime.now(timezone.utc)

    if args.last_days:
        end_date = now
        start_date = now - timedelta(days=args.last_days)
    else:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        # 包含结束日期的全天
        end_date = end_date + timedelta(days=1)

    return start_date, end_date


def main():
    """主函数"""
    args = parse_arguments()

    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    logger.info("开始分析用户行为数据")

    # 计算日期范围
    start_date, end_date = calculate_date_range(args)
    logger.info(f"时间范围: {start_date.date()} 到 {end_date.date()}")

    # 加载聊天限制配置
    chat_limits = load_chat_limits(args.config)
    guest_limit = chat_limits["guest"]
    google_limit = chat_limits["google"]

    # 加载数据库配置
    db_config = load_database_config(args.config)

    # 命令行参数覆盖配置文件
    if args.db_host:
        db_config["host"] = args.db_host
    if args.db_port:
        db_config["port"] = args.db_port
    if args.db_user:
        db_config["user"] = args.db_user
    if args.db_password:
        db_config["password"] = args.db_password
    if args.db_name:
        db_config["dbname"] = args.db_name

    # 连接数据库
    try:
        conn = psycopg2.connect(**db_config)
        logger.info(
            f"数据库连接成功: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
        )
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        logger.error("请检查数据库配置或使用命令行参数指定")
        sys.exit(1)

    try:
        # 分析数据
        analytics = UserAnalytics(conn)
        results = process_data(
            analytics, start_date, end_date, guest_limit, google_limit
        )

        if args.dry_run:
            logger.info("Dry-Run 模式，不生成报告文件")
            logger.info("数据统计完成")
            return

        # 生成报告
        logger.info("生成报告...")
        output_dir = Path(args.output_dir)
        generator = ReportGenerator(output_dir)

        # 保存 CSV 文件
        if "daily_users" in results and not results["daily_users"].empty:
            generator.save_csv(results["daily_users"], "daily_new_users.csv")

        if "user_activity" in results and not results["user_activity"].empty:
            generator.save_csv(results["user_activity"], "user_chat_activity.csv")

        if (
            "user_sessions_detail" in results
            and not results["user_sessions_detail"].empty
        ):
            generator.save_csv(
                results["user_sessions_detail"], "user_sessions_detail.csv"
            )

        if "popular_agents" in results and not results["popular_agents"].empty:
            generator.save_csv(results["popular_agents"], "popular_agents.csv")

        if (
            "rounds_distribution" in results
            and not results["rounds_distribution"].empty
        ):
            generator.save_csv(
                results["rounds_distribution"], "conversation_rounds_distribution.csv"
            )

        if (
            "user_rounds_distribution" in results
            and not results["user_rounds_distribution"].empty
        ):
            generator.save_csv(
                results["user_rounds_distribution"], "user_rounds_distribution.csv"
            )

        if "user_voice_usage" in results and not results["user_voice_usage"].empty:
            generator.save_csv(results["user_voice_usage"], "user_voice_usage.csv")

        if (
            "users_hitting_chat_limit" in results
            and not results["users_hitting_chat_limit"].empty
        ):
            generator.save_csv(
                results["users_hitting_chat_limit"], "users_hitting_chat_limit.csv"
            )

        if (
            "new_users_email_list" in results
            and not results["new_users_email_list"].empty
        ):
            generator.save_csv(
                results["new_users_email_list"], "new_users_email_list.csv"
            )

        # 生成对话详情文本报告
        if (
            "messages" in results
            and not results["messages"].empty
            and "user_sessions_detail" in results
        ):
            logger.info("生成对话详情报告...")
            conversation_report = generate_conversation_report(
                results["user_sessions_detail"], results["messages"]
            )
            generator.save_text_report(conversation_report, "conversations_detail.txt")

        # 生成 HTML 报告（图表）
        generator.generate_html_report(
            results.get("daily_users", pd.DataFrame()),
            results.get("user_activity", pd.DataFrame()),
            results.get("popular_agents", pd.DataFrame()),
            results.get("rounds_distribution", pd.DataFrame()),
            results.get("user_rounds_distribution", pd.DataFrame()),
            results.get("user_sessions_detail", pd.DataFrame()),
            results.get("users_hitting_chat_limit", pd.DataFrame()),
            (start_date, end_date),
        )

        # 生成详细对话HTML报告（可交互查看对话）
        if (
            "messages" in results
            and not results["messages"].empty
            and "user_sessions_detail" in results
            and not results["user_sessions_detail"].empty
        ):
            logger.info("生成详细对话HTML报告...")
            generator.generate_detailed_html_report(
                results["user_sessions_detail"],
                results["messages"],
                (start_date, end_date),
                results.get("stats"),
                results.get("long_conversations"),
            )

        # 生成角色数据分析HTML报告
        if "agent_analytics" in results and not results["agent_analytics"].empty:
            logger.info("生成角色数据分析HTML报告...")
            generator.generate_agent_analytics_html_report(
                results["agent_analytics"],
                (start_date, end_date),
            )

        logger.info(f"所有报告已保存到: {output_dir}")
        logger.info("分析完成！")

    except Exception as e:
        logger.error(f"分析过程出错: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
