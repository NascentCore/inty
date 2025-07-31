#!/usr/bin/env python3
import psycopg2
from app.core.config import settings


def analyze_agent_data():
    """分析Agent数据库中的字段使用情况"""

    # 建立数据库连接
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        user=settings.database.user,
        password=settings.database.password,
        dbname=settings.database.db,
    )

    cursor = conn.cursor()

    try:
        # 1. 基础统计
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_agents,
                COUNT(CASE WHEN prompt IS NOT NULL AND LENGTH(TRIM(prompt)) > 0 THEN 1 END) as has_prompt,
                COUNT(CASE WHEN personality IS NOT NULL AND LENGTH(TRIM(personality)) > 0 THEN 1 END) as has_personality,
                COUNT(CASE WHEN scenario IS NOT NULL AND LENGTH(TRIM(scenario)) > 0 THEN 1 END) as has_scenario,
                COUNT(CASE WHEN first_message IS NOT NULL AND LENGTH(TRIM(first_message)) > 0 THEN 1 END) as has_first_message
            FROM agents 
            WHERE deleted_at IS NULL
        """
        )
        stats = cursor.fetchone()

        print("=== Agent字段使用统计 ===")
        print(f"总Agent数量: {stats[0]}")

        if stats[0] > 0:
            print(f"有prompt字段: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
            print(f"有personality字段: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
            print(f"有scenario字段: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")
            print(f"有first_message字段: {stats[4]} ({stats[4]/stats[0]*100:.1f}%)")

            # 2. 长度分析
            cursor.execute(
                """
                SELECT 
                    ROUND(AVG(LENGTH(prompt))) as avg_prompt_length,
                    ROUND(AVG(LENGTH(personality))) as avg_personality_length,
                    COUNT(CASE WHEN LENGTH(prompt) > 100 THEN 1 END) as long_prompts,
                    COUNT(CASE WHEN LENGTH(prompt) > 0 AND LENGTH(personality) > 0 THEN 1 END) as has_both
                FROM agents 
                WHERE deleted_at IS NULL
            """
            )
            lengths = cursor.fetchone()

            print(f"\n=== 字段长度分析 ===")
            print(f"平均prompt长度: {lengths[0] or 0}字符")
            print(f"平均personality长度: {lengths[1] or 0}字符")
            print(f"长prompt(>100字符): {lengths[2]}个")
            print(f"同时有prompt和personality: {lengths[3]}个")

            # 3. 示例数据
            cursor.execute(
                """
                SELECT name, 
                       CASE WHEN LENGTH(prompt) > 50 THEN LEFT(prompt, 50) || '...' ELSE prompt END as prompt_preview,
                       CASE WHEN LENGTH(personality) > 50 THEN LEFT(personality, 50) || '...' ELSE personality END as personality_preview
                FROM agents 
                WHERE deleted_at IS NULL 
                  AND (prompt IS NOT NULL OR personality IS NOT NULL)
                LIMIT 3
            """
            )
            examples = cursor.fetchall()

            print(f"\n=== 示例数据 ===")
            for i, (name, prompt_preview, personality_preview) in enumerate(
                examples, 1
            ):
                print(f"Agent {i}: {name}")
                print(f'  Prompt: {prompt_preview or "无"}')
                print(f'  Personality: {personality_preview or "无"}')

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    analyze_agent_data()
