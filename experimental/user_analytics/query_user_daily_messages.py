#!/usr/bin/env python3
"""
用户每日聊天消息统计脚本

通过邮箱查询某个用户每日的聊天情况（发了多少消息）。
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import psycopg2
import yaml
from loguru import logger


def generate_session_id(chat_id: str) -> str:
    """
    生成 session_id，与 app/services/chat_service.py 中的逻辑一致

    验证：使用相同的 UUID5 生成方式，确保与后端代码完全一致
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


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
    db_config["password"] = os.getenv(
        "DB_PASSWORD", db_config.get("password", "")
    )
    db_config["dbname"] = os.getenv("DB_NAME", db_config.get("dbname", "inty"))

    return db_config


def find_user_by_email(
    conn: psycopg2.extensions.connection, email: str
) -> Optional[Dict[str, Any]]:
    """通过邮箱查找用户"""
    query = """
        SELECT id, email, nickname, auth_type, created_at
        FROM users
        WHERE email = %s AND deleted_at IS NULL
        LIMIT 1
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, (email,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "nickname": row[2],
                "auth_type": row[3],
                "created_at": row[4],
            }
        return None
    finally:
        cursor.close()


def get_user_chat_ids(
    conn: psycopg2.extensions.connection, user_id: str
) -> list:
    """获取用户的所有 chat_id"""
    query = """
        SELECT id
        FROM chats
        WHERE user_id = %s AND is_active = true
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, (user_id,))
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()


def get_daily_message_count(
    conn: psycopg2.extensions.connection,
    session_ids: list,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """统计每日消息数"""
    if not session_ids:
        return pd.DataFrame(columns=["date", "message_count"])

    # 生成占位符
    placeholders = ",".join(["%s"] * len(session_ids))

    # 构建查询
    query = f"""
        SELECT 
            DATE(ch.created_at AT TIME ZONE 'UTC') as date,
            COUNT(*) as message_count
        FROM chat_history ch
        WHERE ch.session_id::text IN ({placeholders})
          AND ch.message->>'type' = 'human'
          AND (ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
    """

    params = list(session_ids)

    # 添加时间范围过滤
    if start_date:
        query += " AND ch.created_at >= %s"
        params.append(start_date)
    if end_date:
        query += " AND ch.created_at < %s"
        params.append(end_date)

    query += """
        GROUP BY DATE(ch.created_at AT TIME ZONE 'UTC')
        ORDER BY date
    """

    cursor = conn.cursor()
    try:
        cursor.execute(query, tuple(params))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        return pd.DataFrame(data, columns=columns)
    finally:
        cursor.close()


def format_table_output(df: pd.DataFrame, user_info: Dict[str, Any]) -> str:
    """格式化表格输出"""
    if df.empty:
        return "无聊天记录"

    lines = []
    lines.append("=" * 60)
    lines.append(f"用户信息")
    lines.append("=" * 60)
    lines.append(f"用户ID: {user_info['id']}")
    lines.append(f"邮箱: {user_info['email']}")
    lines.append(f"昵称: {user_info.get('nickname', 'N/A')}")
    lines.append(f"认证类型: {user_info['auth_type']}")
    lines.append(f"注册时间: {user_info['created_at']}")
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"每日消息统计")
    lines.append("=" * 60)
    lines.append("")

    # 表头
    lines.append(f"{'日期':<12} {'消息数':<10}")
    lines.append("-" * 60)

    # 数据行
    total_messages = 0
    for _, row in df.iterrows():
        date_str = str(row["date"])
        count = int(row["message_count"])
        total_messages += count
        lines.append(f"{date_str:<12} {count:<10}")

    lines.append("-" * 60)
    lines.append(f"{'总计':<12} {total_messages:<10}")
    lines.append("")

    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="通过邮箱查询用户每日聊天消息统计"
    )

    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="用户邮箱地址",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        help="开始日期 (YYYY-MM-DD)，可选",
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="结束日期 (YYYY-MM-DD)，可选",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="输出 CSV 文件路径，可选",
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
    if args.end_date and not args.start_date:
        parser.error("--end-date 需要配合 --start-date 使用")

    return args


def parse_date_range(
    start_date_str: Optional[str], end_date_str: Optional[str]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """解析日期范围"""
    start_date = None
    end_date = None

    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        # 包含结束日期的全天
        end_date = end_date.replace(hour=23, minute=59, second=59) + timedelta(
            seconds=1
        )

    return start_date, end_date


def main():
    """主函数"""
    args = parse_arguments()

    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    logger.info(f"查询用户每日聊天消息统计: {args.email}")

    # 解析日期范围
    start_date, end_date = parse_date_range(args.start_date, args.end_date)
    if start_date and end_date:
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
        # 查找用户
        logger.info(f"查找用户: {args.email}")
        user_info = find_user_by_email(conn, args.email)
        if not user_info:
            logger.error(f"未找到邮箱为 {args.email} 的用户")
            sys.exit(1)

        logger.info(
            f"找到用户: {user_info['id']} ({user_info.get('nickname', 'N/A')})"
        )

        # 获取用户的 chat_id
        logger.info("查询用户的聊天会话...")
        chat_ids = get_user_chat_ids(conn, user_info["id"])
        logger.info(f"找到 {len(chat_ids)} 个活跃聊天会话")

        if not chat_ids:
            logger.warning("该用户没有活跃的聊天会话")
            print("\n用户信息:")
            print(f"  用户ID: {user_info['id']}")
            print(f"  邮箱: {user_info['email']}")
            print(f"  昵称: {user_info.get('nickname', 'N/A')}")
            print(f"  认证类型: {user_info['auth_type']}")
            print("\n无聊天记录")
            return

        # 生成 session_id
        session_ids = [generate_session_id(chat_id) for chat_id in chat_ids]

        # 统计每日消息数
        logger.info("统计每日消息数...")
        daily_df = get_daily_message_count(
            conn, session_ids, start_date, end_date
        )

        if daily_df.empty:
            logger.warning("在指定时间范围内没有找到消息记录")
            print("\n用户信息:")
            print(f"  用户ID: {user_info['id']}")
            print(f"  邮箱: {user_info['email']}")
            print(f"  昵称: {user_info.get('nickname', 'N/A')}")
            print(f"  认证类型: {user_info['auth_type']}")
            if start_date and end_date:
                print(f"\n时间范围: {start_date.date()} 到 {end_date.date()}")
            print("\n无聊天记录")
            return

        # 输出结果
        print("\n" + format_table_output(daily_df, user_info))

        # 保存 CSV
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 添加用户信息列
            result_df = daily_df.copy()
            result_df["user_id"] = user_info["id"]
            result_df["email"] = user_info["email"]
            result_df["nickname"] = user_info.get("nickname", "")
            result_df["auth_type"] = user_info["auth_type"]

            # 重新排列列顺序
            result_df = result_df[
                [
                    "user_id",
                    "email",
                    "nickname",
                    "auth_type",
                    "date",
                    "message_count",
                ]
            ]

            result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            logger.info(f"已保存 CSV 文件: {output_path}")

        logger.info("查询完成！")

    except Exception as e:
        logger.error(f"查询过程出错: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
