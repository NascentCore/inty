#!/usr/bin/env python3
"""
生图失败原因分析脚本

分析 subscription_usage 表中生图请求的失败原因，包括失败类型统计、失败原因分析、时间趋势等。
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import yaml
from loguru import logger
from plotly.subplots import make_subplots


class ImageGenerationAnalytics:
    """生图失败分析类"""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def get_summary_stats(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """获取总体统计"""
        query = """
            SELECT 
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures,
                COUNT(*) FILTER (WHERE extra_data->>'success' IS NULL OR extra_data->>'success' = '') as unknown_status
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= %s 
              AND usage_date < %s
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)

            if not df.empty:
                total = df.iloc[0]["total_requests"]
                success = df.iloc[0]["total_success"]
                failures = df.iloc[0]["total_failures"]
                unknown = df.iloc[0]["unknown_status"]

                df["success_rate"] = (success / total * 100) if total > 0 else 0.0
                df["failure_rate"] = (failures / total * 100) if total > 0 else 0.0
                df["unknown_rate"] = (unknown / total * 100) if total > 0 else 0.0

            return df
        finally:
            cursor.close()

    def get_fallback_stats(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """获取兜底占比统计（新生成 vs 兜底 vs 失败，与日报口径一致）"""
        query = """
            SELECT
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true' AND (extra_data->>'is_matched' IS NULL OR extra_data->>'is_matched' = 'false')) as new_generation,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true' AND extra_data->>'is_matched' = 'true') as fallback_used,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'false' OR extra_data->>'success' IS NULL) as failures
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= %s
              AND usage_date < %s
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
            if not df.empty:
                row = df.iloc[0]
                total = row["total_requests"]
                new_gen = row["new_generation"]
                fallback = row["fallback_used"]
                success_total = new_gen + fallback
                df["total_success"] = success_total
                df["fallback_ratio_of_success_pct"] = (
                    (fallback / success_total * 100) if success_total > 0 else 0.0
                )
                df["fallback_ratio_of_requests_pct"] = (
                    (fallback / total * 100) if total > 0 else 0.0
                )
            return df
        finally:
            cursor.close()

    def get_failures_by_type(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """按失败类型统计"""
        query = """
            WITH failure_counts AS (
                SELECT 
                    extra_data->>'failure_type' as failure_type,
                    COUNT(*) as count
                FROM subscription_usage
                WHERE usage_type = 'image_generation'
                  AND usage_date >= %s 
                  AND usage_date < %s
                  AND (extra_data->>'success' = 'false' OR extra_data->>'success' IS NULL)
                GROUP BY extra_data->>'failure_type'
            )
            SELECT 
                failure_type,
                count,
                count * 100.0 / SUM(count) OVER () as percentage
            FROM failure_counts
            ORDER BY count DESC
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)

            # 处理 NULL 值
            df["failure_type"] = df["failure_type"].fillna("unknown")

            return df
        finally:
            cursor.close()

    def get_failures_by_reason(
        self, start_date: datetime, end_date: datetime, top_n: int = 20
    ) -> pd.DataFrame:
        """按失败原因统计（Top N）"""
        query = """
            SELECT 
                extra_data->>'failure_reason' as failure_reason,
                extra_data->>'failure_type' as failure_type,
                COUNT(*) as count
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= %s 
              AND usage_date < %s
              AND (extra_data->>'success' = 'false' OR extra_data->>'success' IS NULL)
              AND extra_data->>'failure_reason' IS NOT NULL
            GROUP BY extra_data->>'failure_reason', extra_data->>'failure_type'
            ORDER BY count DESC
            LIMIT %s
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date, top_n))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)

            # 处理 NULL 值
            df["failure_type"] = df["failure_type"].fillna("unknown")

            # 截断过长的失败原因
            if not df.empty and "failure_reason" in df.columns:
                df["failure_reason_short"] = df["failure_reason"].apply(
                    lambda x: x[:200] + "..." if x and len(x) > 200 else x
                )

            return df
        finally:
            cursor.close()

    def get_daily_trend(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """按日期统计趋势"""
        query = """
            SELECT 
                DATE(usage_date AT TIME ZONE 'UTC') as date,
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'true') as total_success,
                COUNT(*) FILTER (WHERE extra_data->>'success' = 'false') as total_failures,
                COUNT(*) FILTER (WHERE extra_data->>'success' IS NULL OR extra_data->>'success' = '') as unknown_status
            FROM subscription_usage
            WHERE usage_type = 'image_generation'
              AND usage_date >= %s 
              AND usage_date < %s
            GROUP BY DATE(usage_date AT TIME ZONE 'UTC')
            ORDER BY date
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)

            if not df.empty:
                df["success_rate"] = (
                    df["total_success"] / df["total_requests"] * 100
                ).round(2)
                df["failure_rate"] = (
                    df["total_failures"] / df["total_requests"] * 100
                ).round(2)
                df["unknown_rate"] = (
                    df["unknown_status"] / df["total_requests"] * 100
                ).round(2)

            return df
        finally:
            cursor.close()

    def get_failures_by_agent(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """按 Agent 统计失败率"""
        query = """
            SELECT 
                su.extra_data->>'agent_id' as agent_id,
                a.name as agent_name,
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE su.extra_data->>'success' = 'true') as total_success,
                COUNT(*) FILTER (WHERE su.extra_data->>'success' = 'false') as total_failures,
                COUNT(*) FILTER (WHERE su.extra_data->>'success' IS NULL OR su.extra_data->>'success' = '') as unknown_status
            FROM subscription_usage su
            LEFT JOIN agents a ON su.extra_data->>'agent_id' = a.id::text
            WHERE su.usage_type = 'image_generation'
              AND su.usage_date >= %s 
              AND su.usage_date < %s
              AND su.extra_data->>'agent_id' IS NOT NULL
            GROUP BY su.extra_data->>'agent_id', a.name
            HAVING COUNT(*) >= 5
            ORDER BY total_requests DESC
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)

            if not df.empty:
                df["success_rate"] = (
                    df["total_success"] / df["total_requests"] * 100
                ).round(2)
                df["failure_rate"] = (
                    df["total_failures"] / df["total_requests"] * 100
                ).round(2)
                df["unknown_rate"] = (
                    df["unknown_status"] / df["total_requests"] * 100
                ).round(2)
                df["agent_name"] = df["agent_name"].fillna("Unknown")

            return df
        finally:
            cursor.close()

    def get_detailed_failures(
        self, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> pd.DataFrame:
        """获取详细失败记录"""
        query = """
            SELECT 
                su.id,
                su.user_id,
                su.usage_date,
                su.extra_data->>'agent_id' as agent_id,
                a.name as agent_name,
                su.extra_data->>'failure_type' as failure_type,
                su.extra_data->>'failure_reason' as failure_reason,
                su.extra_data->>'message_content' as message_content,
                su.extra_data->>'success' as success
            FROM subscription_usage su
            LEFT JOIN agents a ON su.extra_data->>'agent_id' = a.id::text
            WHERE su.usage_type = 'image_generation'
              AND su.usage_date >= %s 
              AND su.usage_date < %s
              AND (su.extra_data->>'success' = 'false' OR su.extra_data->>'success' IS NULL)
            ORDER BY su.usage_date DESC
            LIMIT %s
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (start_date, end_date, limit))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)

            # 处理 NULL 值
            df["failure_type"] = df["failure_type"].fillna("unknown")
            df["agent_name"] = df["agent_name"].fillna("Unknown")

            # 截断过长的文本
            if not df.empty:
                if "failure_reason" in df.columns:
                    df["failure_reason"] = df["failure_reason"].apply(
                        lambda x: x[:200] + "..." if x and len(x) > 200 else x
                    )
                if "message_content" in df.columns:
                    df["message_content"] = df["message_content"].apply(
                        lambda x: x[:100] + "..." if x and len(x) > 100 else x
                    )

            return df
        finally:
            cursor.close()


class ReportGenerator:
    """报告生成类"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_csv(self, df: pd.DataFrame, filename: str):
        """保存 CSV 文件"""
        if df.empty:
            logger.warning(f"数据为空，跳过保存: {filename}")
            return

        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"已保存 CSV: {filepath}")

    def generate_html_report(
        self,
        summary_df: pd.DataFrame,
        failures_by_type_df: pd.DataFrame,
        failures_by_reason_df: pd.DataFrame,
        daily_trend_df: pd.DataFrame,
        failures_by_agent_df: pd.DataFrame,
        date_range: Tuple[datetime, datetime],
    ):
        """生成 HTML 可视化报告"""
        fig = make_subplots(
            rows=5,
            cols=1,
            subplot_titles=(
                "生图请求总体统计",
                "失败类型分布",
                "每日趋势（成功率/失败率）",
                "Top 失败原因",
                "按 Agent 统计失败率（请求数 >= 5）",
            ),
            vertical_spacing=0.08,
            specs=[
                [{"type": "bar"}],
                [{"type": "pie"}],
                [{"type": "scatter"}],
                [{"type": "bar"}],
                [{"type": "bar"}],
            ],
        )

        # 图表 1: 总体统计
        if not summary_df.empty:
            summary = summary_df.iloc[0]
            fig.add_trace(
                go.Bar(
                    x=["总请求数", "成功数", "失败数", "未知状态"],
                    y=[
                        summary.get("total_requests", 0),
                        summary.get("total_success", 0),
                        summary.get("total_failures", 0),
                        summary.get("unknown_status", 0),
                    ],
                    marker_color=["blue", "green", "red", "orange"],
                    showlegend=False,
                ),
                row=1,
                col=1,
            )

        # 图表 2: 失败类型分布（饼图）
        if not failures_by_type_df.empty:
            fig.add_trace(
                go.Pie(
                    labels=failures_by_type_df["failure_type"],
                    values=failures_by_type_df["count"],
                    hole=0.3,
                    textinfo="label+percent",
                ),
                row=2,
                col=1,
            )

        # 图表 3: 每日趋势
        if not daily_trend_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=daily_trend_df["date"],
                    y=daily_trend_df["success_rate"],
                    mode="lines+markers",
                    name="成功率 (%)",
                    line=dict(color="green"),
                ),
                row=3,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=daily_trend_df["date"],
                    y=daily_trend_df["failure_rate"],
                    mode="lines+markers",
                    name="失败率 (%)",
                    line=dict(color="red"),
                ),
                row=3,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=daily_trend_df["date"],
                    y=daily_trend_df["unknown_rate"],
                    mode="lines+markers",
                    name="未知状态率 (%)",
                    line=dict(color="orange"),
                ),
                row=3,
                col=1,
            )

        # 图表 4: Top 失败原因
        if not failures_by_reason_df.empty:
            top_reasons = failures_by_reason_df.head(15)
            # 使用简短版本显示
            labels = top_reasons.get(
                "failure_reason_short", top_reasons["failure_reason"]
            )
            fig.add_trace(
                go.Bar(
                    x=top_reasons["count"],
                    y=labels,
                    orientation="h",
                    marker_color="coral",
                    showlegend=False,
                ),
                row=4,
                col=1,
            )

        # 图表 5: 按 Agent 统计失败率
        if not failures_by_agent_df.empty:
            top_agents = failures_by_agent_df.head(20)
            fig.add_trace(
                go.Bar(
                    x=top_agents["agent_name"],
                    y=top_agents["failure_rate"],
                    marker_color="lightcoral",
                    showlegend=False,
                    text=top_agents["failure_rate"].round(1).astype(str) + "%",
                    textposition="outside",
                ),
                row=5,
                col=1,
            )

        # 更新布局
        fig.update_layout(
            height=2000,
            title_text=f"生图失败原因分析报告 ({date_range[0].date()} 至 {date_range[1].date()})",
            title_x=0.5,
            showlegend=True,
        )

        # 更新 x 轴标签
        fig.update_xaxes(title_text="日期", row=3, col=1)
        fig.update_xaxes(title_text="失败数", row=4, col=1)
        fig.update_xaxes(title_text="Agent", row=5, col=1, tickangle=-45)

        # 更新 y 轴标签
        fig.update_yaxes(title_text="数量", row=1, col=1)
        fig.update_yaxes(title_text="百分比 (%)", row=3, col=1)
        fig.update_yaxes(title_text="失败原因", row=4, col=1)
        fig.update_yaxes(title_text="失败率 (%)", row=5, col=1)

        # 保存 HTML
        filepath = self.output_dir / "image_generation_failures_report.html"
        fig.write_html(str(filepath))
        logger.info(f"已保存 HTML 报告: {filepath}")


def load_database_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载数据库配置"""
    db_config = {}

    # 尝试从配置文件加载
    if config_file:
        config_path = Path(config_file)
    else:
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
                    "replica_host": db_section.get("replica_host"),
                    "replica_port": db_section.get("replica_port"),
                }
                logger.info(f"从配置文件加载数据库配置: {config_path}")
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")

    # 环境变量覆盖
    db_config["host"] = os.getenv("DB_HOST", db_config.get("host", "localhost"))
    db_config["port"] = int(os.getenv("DB_PORT", db_config.get("port", 5432)))
    db_config["user"] = os.getenv("DB_USER", db_config.get("user", "postgres"))
    db_config["password"] = os.getenv("DB_PASSWORD", db_config.get("password", ""))
    db_config["dbname"] = os.getenv("DB_NAME", db_config.get("dbname", "inty"))
    if "replica_host" not in db_config:
        db_config["replica_host"] = None
    if "replica_port" not in db_config:
        db_config["replica_port"] = None
    db_config["replica_host"] = os.getenv(
        "DB_REPLICA_HOST", db_config.get("replica_host")
    )
    if db_config.get("replica_port") is not None:
        db_config["replica_port"] = int(db_config["replica_port"])
    elif os.getenv("DB_REPLICA_PORT"):
        db_config["replica_port"] = int(os.getenv("DB_REPLICA_PORT"))

    return db_config


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="生图失败原因分析脚本")

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
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Top N 失败原因数量 (默认: 20)",
    )

    # 数据库配置参数
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument(
        "--replica",
        action="store_true",
        help="使用只读副本（config 中 database.replica_host）；未配置时回退到主库",
    )
    parser.add_argument(
        "--db-host", type=str, help="数据库主机（显式指定时覆盖 config 与 --replica）"
    )
    parser.add_argument("--db-port", type=int, help="数据库端口")
    parser.add_argument("--db-user", type=str, help="数据库用户名")
    parser.add_argument("--db-password", type=str, help="数据库密码")
    parser.add_argument("--db-name", type=str, help="数据库名称")

    args = parser.parse_args()

    # 验证日期参数
    if args.start_date and not args.end_date:
        parser.error("--start-date 需要配合 --end-date 使用")

    return args


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

    logger.info("开始分析生图失败原因")

    # 计算日期范围
    start_date, end_date = calculate_date_range(args)
    logger.info(f"时间范围: {start_date.date()} 到 {end_date.date()}")

    # 加载数据库配置
    db_config = load_database_config(args.config)

    # 若指定 --replica 且配置了 replica_host，则连接只读副本
    if args.replica and db_config.get("replica_host"):
        db_config["host"] = db_config["replica_host"]
        if db_config.get("replica_port") is not None:
            db_config["port"] = db_config["replica_port"]
        logger.info(f"使用只读副本: {db_config['host']}:{db_config['port']}")
    elif args.replica:
        logger.warning("未配置 replica_host，使用主库连接")

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

    # 连接数据库（仅传入 psycopg2 接受的参数）
    connect_params = {
        k: v
        for k, v in db_config.items()
        if k in ("host", "port", "user", "password", "dbname") and v is not None
    }
    try:
        conn = psycopg2.connect(**connect_params)
        logger.info(
            f"数据库连接成功: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
        )
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        logger.error("请检查数据库配置或使用命令行参数指定")
        sys.exit(1)

    try:
        # 分析数据
        analytics = ImageGenerationAnalytics(conn)

        logger.info("查询总体统计...")
        summary_df = analytics.get_summary_stats(start_date, end_date)

        logger.info("查询兜底占比统计...")
        fallback_df = analytics.get_fallback_stats(start_date, end_date)

        logger.info("查询失败类型统计...")
        failures_by_type_df = analytics.get_failures_by_type(start_date, end_date)

        logger.info("查询失败原因统计...")
        failures_by_reason_df = analytics.get_failures_by_reason(
            start_date, end_date, args.top_n
        )

        logger.info("查询每日趋势...")
        daily_trend_df = analytics.get_daily_trend(start_date, end_date)

        logger.info("查询 Agent 维度统计...")
        failures_by_agent_df = analytics.get_failures_by_agent(start_date, end_date)

        logger.info("查询详细失败记录...")
        detailed_failures_df = analytics.get_detailed_failures(start_date, end_date)

        # 显示统计信息
        if not summary_df.empty:
            summary = summary_df.iloc[0]
            logger.info("=" * 60)
            logger.info("总体统计:")
            logger.info(f"  总请求数: {summary.get('total_requests', 0)}")
            logger.info(f"  成功数: {summary.get('total_success', 0)}")
            logger.info(f"  失败数: {summary.get('total_failures', 0)}")
            logger.info(f"  未知状态: {summary.get('unknown_status', 0)}")
            logger.info(f"  成功率: {summary.get('success_rate', 0):.2f}%")
            logger.info(f"  失败率: {summary.get('failure_rate', 0):.2f}%")
            logger.info(f"  未知状态率: {summary.get('unknown_rate', 0):.2f}%")
            logger.info("=" * 60)
        if not fallback_df.empty:
            fb = fallback_df.iloc[0]
            logger.info("兜底占比（与日报口径一致）:")
            logger.info(f"  新生成次数: {fb.get('new_generation', 0)}")
            logger.info(f"  兜底图片次数: {fb.get('fallback_used', 0)}")
            logger.info(f"  失败次数: {fb.get('failures', 0)}")
            logger.info(
                f"  兜底占成功比例: {fb.get('fallback_ratio_of_success_pct', 0):.2f}%"
            )
            logger.info(
                f"  兜底占请求比例: {fb.get('fallback_ratio_of_requests_pct', 0):.2f}%"
            )
            logger.info("=" * 60)

        if args.dry_run:
            logger.info("Dry-Run 模式，不生成报告文件")
            logger.info("数据统计完成")
            return

        # 生成报告
        logger.info("生成报告...")
        output_dir = Path(args.output_dir)
        generator = ReportGenerator(output_dir)

        # 保存 CSV 文件
        generator.save_csv(summary_df, "image_generation_summary.csv")
        generator.save_csv(fallback_df, "image_generation_fallback_stats.csv")
        generator.save_csv(failures_by_type_df, "image_generation_failures_by_type.csv")
        generator.save_csv(
            failures_by_reason_df, "image_generation_failures_by_reason.csv"
        )
        generator.save_csv(daily_trend_df, "image_generation_daily_trend.csv")
        generator.save_csv(
            failures_by_agent_df, "image_generation_failures_by_agent.csv"
        )
        generator.save_csv(
            detailed_failures_df, "image_generation_detailed_failures.csv"
        )

        # 生成 HTML 报告
        generator.generate_html_report(
            summary_df,
            failures_by_type_df,
            failures_by_reason_df,
            daily_trend_df,
            failures_by_agent_df,
            (start_date, end_date),
        )

        logger.info("报告生成完成！")

    except Exception as e:
        logger.error(f"分析过程中出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
