#!/usr/bin/env python3
"""
检查并修复chat_history表结构
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.services.chat_history_service import (
    get_chat_history_connection,
    ensure_table_initialized,
)
from app.core.config import global_config_loaded_from_config_yaml
import psycopg


def check_table_structure():
    """检查chat_history表结构"""
    try:
        # 获取数据库连接
        conn = psycopg.connect(
            global_config_loaded_from_config_yaml.database.url, autocommit=True
        )

        with conn.cursor() as cur:
            # 检查表是否存在
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'chat_history'
                );
            """
            )
            table_exists = cur.fetchone()[0]

            if not table_exists:
                print("chat_history表不存在，将创建新表")
                ensure_table_initialized()
                return

            # 检查session_id列的类型
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'chat_history' 
                AND column_name = 'session_id';
            """
            )
            session_id_info = cur.fetchone()

            if session_id_info:
                column_name, data_type, is_nullable = session_id_info
                print(
                    f"session_id列信息: {column_name}, 类型: {data_type}, 可空: {is_nullable}"
                )

                # 如果session_id不是uuid类型，需要重建表
                if data_type != "uuid":
                    print(f"session_id列类型为 {data_type}，期望uuid类型，将重建表")
                    drop_and_recreate_table(conn)
                else:
                    print("表结构正确")
            else:
                print("session_id列不存在，将重建表")
                drop_and_recreate_table(conn)

    except Exception as e:
        print(f"检查表结构时出错: {str(e)}")
        raise


def drop_and_recreate_table(conn):
    """删除并重建chat_history表"""
    try:
        with conn.cursor() as cur:
            print("删除现有chat_history表...")
            cur.execute("DROP TABLE IF EXISTS chat_history CASCADE")

            print("重新创建chat_history表...")
            ensure_table_initialized()

            print("表重建完成")

    except Exception as e:
        print(f"重建表时出错: {str(e)}")
        raise


if __name__ == "__main__":
    print("开始检查chat_history表结构...")
    check_table_structure()
    print("检查完成")
