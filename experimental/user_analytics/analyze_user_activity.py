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
                    COUNT(*) as message_count
                FROM chat_history
                WHERE session_id::text IN ({placeholders})
                GROUP BY session_id
            """
            cursor.execute(history_query, tuple(session_ids))

            # 构建 session_id 到消息数的映射
            session_to_count = {row[0]: row[1] for row in cursor.fetchall()}

            # 转换回 chat_id 和消息数
            data = []
            for chat_id, session_id in chat_to_session.items():
                if session_id in session_to_count:
                    data.append((chat_id, session_to_count[session_id]))

            logger.info(f"找到 {len(data)} 个有对话记录的会话")

            return pd.DataFrame(data, columns=["chat_id", "message_count"])
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
                ch.created_at
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
                    result_data.append((chat_id, row[1], row[2], row[3]))

            return pd.DataFrame(
                result_data,
                columns=["chat_id", "message_type", "content", "created_at"],
            )
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
        user_sessions_detail_df: pd.DataFrame,
        date_range: Tuple[datetime, datetime],
    ):
        """生成 HTML 可视化报告"""
        fig = make_subplots(
            rows=5,
            cols=1,
            subplot_titles=(
                "每日新用户趋势",
                "用户聊天活跃度分布",
                "Top 20 热门聊天角色",
                "对话轮数分布",
                "新增用户会话详情表",
            ),
            vertical_spacing=0.06,
            specs=[
                [{"type": "bar"}],
                [{"type": "histogram"}],
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

        # 图表 4: 对话轮数分布
        if not rounds_dist_df.empty:
            fig.add_trace(
                go.Bar(
                    x=rounds_dist_df["rounds_range"],
                    y=rounds_dist_df["count"],
                    name="聊天数",
                    showlegend=False,
                ),
                row=4,
                col=1,
            )

        # 图表 5: 新增用户会话详情表
        if not user_sessions_detail_df.empty:
            # 准备表格数据，限制显示前100条
            display_df = user_sessions_detail_df.head(100).copy()

            # 格式化时间
            if "user_created_at" in display_df.columns:
                display_df["user_created_at"] = pd.to_datetime(
                    display_df["user_created_at"]
                ).dt.strftime("%Y-%m-%d %H:%M")

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
                row=5,
                col=1,
            )

        # 更新布局
        fig.update_layout(
            height=2800,  # 增加高度以容纳表格
            title_text=f"用户行为分析报告 ({date_range[0].date()} 至 {date_range[1].date()})",
            showlegend=True,
        )

        fig.update_xaxes(title_text="日期", row=1, col=1)
        fig.update_yaxes(title_text="用户数", row=1, col=1)

        fig.update_xaxes(title_text="聊天角色数量", row=2, col=1)
        fig.update_yaxes(title_text="用户数", row=2, col=1)

        fig.update_xaxes(title_text="聊天用户数", row=3, col=1)
        fig.update_yaxes(title_text="角色名称", row=3, col=1)

        fig.update_xaxes(title_text="对话轮数", row=4, col=1)
        fig.update_yaxes(title_text="聊天数量", row=4, col=1)

        # 保存 HTML
        filepath = self.output_dir / "user_analytics_report.html"
        fig.write_html(str(filepath))
        logger.info(f"已保存 HTML 报告: {filepath}")

    def generate_detailed_html_report(
        self,
        user_sessions_detail_df: pd.DataFrame,
        messages_df: pd.DataFrame,
        date_range: Tuple[datetime, datetime],
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
            # 统计信息
            total_users = user_sessions_detail_df["user_id"].nunique()
            total_browse_sessions = len(
                user_sessions_detail_df
            )  # 总浏览数（包含只有开场白的）
            total_messages = len(messages_df)

            # 计算真实会话数（排除只有AI开场白的会话）
            # 统计每个chat_id中的用户消息数量
            user_messages_df = messages_df[messages_df["message_type"] == "human"]
            chat_ids_with_user_msgs = user_messages_df["chat_id"].unique()
            total_real_sessions = user_sessions_detail_df[
                user_sessions_detail_df["chat_id"].isin(chat_ids_with_user_msgs)
            ].shape[0]

            html_content += f"""
        <div class="stats">
            <div class="stat-card">
                <h3>新增用户数</h3>
                <div class="number">{total_users}</div>
            </div>
            <div class="stat-card">
                <h3>总浏览数</h3>
                <div class="number">{total_browse_sessions}</div>
                <p style="font-size: 12px; opacity: 0.8; margin-top: 5px;">含仅浏览开场白</p>
            </div>
            <div class="stat-card">
                <h3>总会话数</h3>
                <div class="number">{total_real_sessions}</div>
                <p style="font-size: 12px; opacity: 0.8; margin-top: 5px;">含用户消息</p>
            </div>
            <div class="stat-card">
                <h3>总消息数</h3>
                <div class="number">{total_messages}</div>
            </div>
            <div class="stat-card">
                <h3>平均对话数</h3>
                <div class="number">{total_messages / total_users if total_users > 0 else 0:.1f}</div>
            </div>
        </div>

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

            # 先计算每个用户的总消息数，用于排序
            user_message_counts = {}
            for user_id, user_sessions in user_sessions_detail_df.groupby("user_id"):
                user_chat_ids = user_sessions["chat_id"].tolist()
                user_messages = messages_df[messages_df["chat_id"].isin(user_chat_ids)]
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
                    "%Y-%m-%d %H:%M"
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
                                "%H:%M:%S"
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


def process_data(
    analytics: UserAnalytics, start_date: datetime, end_date: datetime
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

            # 为每个用户计算总对话轮数
            if "user_activity" in results and not results["user_activity"].empty:
                user_rounds = []
                for _, row in results["user_activity"].iterrows():
                    user_chats = user_chat_df[user_chat_df["user_id"] == row["user_id"]]
                    total_rounds = sum(
                        chat_rounds.get(chat_id, 0)
                        for chat_id in user_chats["chat_id"].dropna()
                    )
                    user_rounds.append(total_rounds)
                results["user_activity"]["total_rounds"] = user_rounds

            # 为每个 session 添加消息数
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

        # 热门角色统计
        if not user_chat_df.empty:
            agent_stats = []
            for agent_id, group in user_chat_df[
                user_chat_df["agent_id"].notna()
            ].groupby("agent_id"):
                user_count = group["user_id"].nunique()
                agent_name = group.iloc[0]["agent_name"]
                chat_ids = group["chat_id"].dropna().unique()
                total_rounds = sum(
                    rounds_df[rounds_df["chat_id"].isin(chat_ids)]["message_count"]
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

        # 对话轮数分布
        bins = [0, 5, 10, 20, 50, 100, 500, float("inf")]
        labels = ["1-5", "6-10", "11-20", "21-50", "51-100", "101-500", "500+"]
        rounds_df["rounds_range"] = pd.cut(
            rounds_df["message_count"], bins=bins, labels=labels, right=True
        )
        rounds_dist = rounds_df["rounds_range"].value_counts().sort_index()
        rounds_dist_df = pd.DataFrame(
            {"rounds_range": rounds_dist.index, "count": rounds_dist.values}
        )
        results["rounds_distribution"] = rounds_dist_df
    else:
        logger.warning("未找到对话轮数数据")
        results["popular_agents"] = pd.DataFrame()
        results["rounds_distribution"] = pd.DataFrame()

    # 4. 获取对话详情
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
                report_lines.append(f"  对话内容:")
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
                report_lines.append(f"  (无对话记录)")

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
        results = process_data(analytics, start_date, end_date)

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
            results.get("user_sessions_detail", pd.DataFrame()),
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
