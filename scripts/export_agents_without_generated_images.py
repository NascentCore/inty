#!/usr/bin/env python3
"""
CREATED_BY_AGENT

导出没有任何用户生成图片的公开角色列表到 CSV 文件。

用法:
    export PYTHONPATH=.
    python scripts/export_agents_without_generated_images.py
    python scripts/export_agents_without_generated_images.py --output agents_no_images.csv
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import cyclopts
import psycopg2

from app.core.config import global_config_loaded_from_config_yaml

app = cyclopts.App()


def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host=global_config_loaded_from_config_yaml.database.host,
        port=global_config_loaded_from_config_yaml.database.port,
        user=global_config_loaded_from_config_yaml.database.user,
        password=global_config_loaded_from_config_yaml.database.password,
        dbname=global_config_loaded_from_config_yaml.database.db,
    )


def query_agents_without_generated_images(cursor) -> list:
    """
    查询没有任何生成图片的公开角色

    Returns:
        包含 (agent_id, agent_name, visibility, created_at) 的列表
    """
    query = """
        SELECT a.id, a.name, a.visibility, a.created_at
        FROM agents a
        LEFT JOIN resources r ON a.id = r.agent_id 
            AND r.type = 'IMAGE' 
            AND r.resource_metadata->>'generation_prompt' IS NOT NULL
        WHERE a.visibility = 'PUBLIC' 
            AND a.deleted_at IS NULL
        GROUP BY a.id, a.name, a.visibility, a.created_at
        HAVING COUNT(r.url) = 0
        ORDER BY a.created_at DESC
    """
    cursor.execute(query)
    return cursor.fetchall()


def export_to_csv(agents: list, output_path: Path):
    """导出角色列表到 CSV 文件"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "agent_name", "visibility", "created_at"])

        for agent in agents:
            agent_id, name, visibility, created_at = agent
            created_at_str = (
                created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else ""
            )
            writer.writerow([agent_id, name, visibility, created_at_str])


@app.default
def main(output: Optional[str] = None):
    """
    导出没有任何用户生成图片的公开角色列表

    Args:
        output: 输出 CSV 文件路径，默认为 agents_without_generated_images_YYYYMMDD_HHMMSS.csv
    """
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"agents_without_generated_images_{timestamp}.csv"

    output_path = Path(output)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print("正在查询没有生成图片的公开角色...")
        agents = query_agents_without_generated_images(cursor)

        print(f"找到 {len(agents)} 个没有生成图片的公开角色")

        if agents:
            export_to_csv(agents, output_path)
            print(f"已导出到: {output_path}")

            print("\n前 10 个角色预览:")
            for i, (agent_id, name, visibility, created_at) in enumerate(
                agents[:10], 1
            ):
                print(f"  {i}. {name} ({agent_id})")
        else:
            print("没有找到符合条件的角色")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    app()
