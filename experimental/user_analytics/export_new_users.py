#!/usr/bin/env python3
"""
导出用户列表脚本

查询指定时间范围内注册的新用户或导出所有用户，并导出为 CSV 文件。
支持显示性别和年龄段信息。
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import psycopg2
import yaml
from loguru import logger


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


def get_new_users(
    conn: psycopg2.extensions.connection,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """查询指定时间范围内注册的新用户"""
    query = """
        SELECT 
            id as user_id,
            email,
            nickname,
            auth_type,
            created_at,
            phone,
            readable_id,
            gender,
            age_group
        FROM users
        WHERE created_at >= %s 
          AND created_at < %s
          AND deleted_at IS NULL
        ORDER BY created_at DESC
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, (start_date, end_date))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        return pd.DataFrame(data, columns=columns)
    finally:
        cursor.close()


def get_all_users(conn: psycopg2.extensions.connection) -> pd.DataFrame:
    """查询所有用户"""
    query = """
        SELECT 
            id as user_id,
            email,
            nickname,
            auth_type,
            created_at,
            phone,
            readable_id,
            gender,
            age_group
        FROM users
        WHERE deleted_at IS NULL
        ORDER BY created_at DESC
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        return pd.DataFrame(data, columns=columns)
    finally:
        cursor.close()


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


def generate_output_filename(start_date: datetime, end_date: datetime) -> str:
    """生成默认输出文件名"""
    start_str = start_date.strftime("%Y%m%d")
    end_str = (end_date - timedelta(days=1)).strftime("%Y%m%d")
    return f"new_users_{start_str}_{end_str}.csv"


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="导出用户列表到 CSV 文件")

    # 时间范围参数（互斥）
    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument(
        "--last-days", type=int, help="导出最近 N 天注册的新用户"
    )
    time_group.add_argument(
        "--start-date", type=str, help="开始日期 (YYYY-MM-DD)"
    )
    time_group.add_argument(
        "--all", action="store_true", help="导出所有用户（忽略时间范围）"
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="结束日期 (YYYY-MM-DD)，与 --start-date 配合使用",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="输出 CSV 文件路径（可选，默认：new_users_YYYYMMDD_YYYYMMDD.csv）",
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


def main():
    """主函数"""
    args = parse_arguments()

    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # 计算日期范围（--all 模式下不需要）
    export_all = getattr(args, "all", False)
    start_date, end_date = None, None
    if not export_all:
        start_date, end_date = calculate_date_range(args)
        logger.info(
            f"查询时间范围: {start_date.date()} 到 {(end_date - timedelta(days=1)).date()}"
        )
    else:
        logger.info("导出所有用户模式")

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
        # 查询用户
        if export_all:
            logger.info("查询所有用户列表...")
            users_df = get_all_users(conn)
        else:
            logger.info("查询新用户列表...")
            users_df = get_new_users(conn, start_date, end_date)

        if users_df.empty:
            if export_all:
                logger.warning("没有找到用户")
                print("\n未找到用户")
            else:
                logger.warning("在指定时间范围内没有找到新用户")
                print(
                    f"\n时间范围: {start_date.date()} 到 {(end_date - timedelta(days=1)).date()}"
                )
                print("未找到新用户")
            return

        logger.info(f"找到 {len(users_df)} 个用户")

        # 格式化日期列
        if not users_df.empty and "created_at" in users_df.columns:
            users_df["created_at"] = pd.to_datetime(
                users_df["created_at"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

        # 确定输出文件路径
        if args.output:
            output_path = Path(args.output)
        elif export_all:
            today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            output_path = Path(f"all_users_{today_str}.csv")
        else:
            output_path = Path(generate_output_filename(start_date, end_date))

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 导出 CSV
        users_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"已导出 {len(users_df)} 个用户到: {output_path}")

        # 显示统计信息
        print("\n" + "=" * 60)
        print("导出完成")
        print("=" * 60)
        if export_all:
            print("模式: 导出所有用户")
        else:
            print(
                f"时间范围: {start_date.date()} 到 {(end_date - timedelta(days=1)).date()}"
            )
        print(f"用户数量: {len(users_df)}")
        print(f"输出文件: {output_path}")
        print("\n字段说明:")
        print("  - user_id: 用户ID")
        print("  - email: 邮箱地址")
        print("  - nickname: 昵称")
        print("  - auth_type: 认证类型")
        print("  - created_at: 注册时间")
        print("  - phone: 手机号")
        print("  - readable_id: 可读ID")
        print("  - gender: 性别 (MALE/FEMALE/OTHER)")
        print("  - age_group: 年龄段")

    except Exception as e:
        logger.error(f"导出过程出错: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
