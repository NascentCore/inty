#!/usr/bin/env python3
"""
数据库操作模块
提供安全的数据库连接和操作功能
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager

import yaml
import asyncpg

from .models import DatabaseConfig, Agent, AppConfig


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_config: DatabaseConfig):
        self.config = db_config
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """初始化数据库连接池"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.db,
                min_size=1,
                max_size=self.config.pool_size or 10,
                max_inactive_connection_lifetime=self.config.pool_recycle
                or 3600,
                command_timeout=self.config.command_timeout or 30,
            )
        except Exception as e:
            raise ConnectionError(f"无法连接到数据库: {e}")

    async def close(self):
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")

        async with self.pool.acquire() as connection:
            yield connection

    @asynccontextmanager
    async def get_transaction(self):
        """获取事务的上下文管理器"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn

    async def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def get_agents_with_personality(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Agent]:
        """
        获取包含personality字段的智能体

        Args:
            limit: 限制数量
            offset: 偏移量

        Returns:
            智能体列表
        """
        query = """
            SELECT id, readable_id, name, gender, personality, tags, created_at, updated_at
            FROM agents 
            WHERE personality IS NOT NULL 
            AND personality != ''
            AND deleted_at IS NULL
            ORDER BY created_at
        """

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [self._row_to_agent(row) for row in rows]

    async def count_agents_with_personality(self) -> int:
        """统计包含personality字段的智能体数量"""
        query = """
            SELECT COUNT(*) 
            FROM agents 
            WHERE personality IS NOT NULL 
            AND personality != ''
            AND deleted_at IS NULL
        """

        async with self.get_connection() as conn:
            return await conn.fetchval(query)

    async def get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """根据ID获取智能体"""
        query = """
            SELECT id, readable_id, name, gender, personality, tags, created_at, updated_at
            FROM agents 
            WHERE id = $1 AND deleted_at IS NULL
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, agent_id)
            return self._row_to_agent(row) if row else None

    async def update_agent_tags(self, agent_id: str, tags: List[str]) -> bool:
        """
        更新智能体的tags字段

        Args:
            agent_id: 智能体ID
            tags: 标签列表

        Returns:
            是否更新成功
        """
        query = """
            UPDATE agents 
            SET tags = $1, updated_at = $2
            WHERE id = $3 AND deleted_at IS NULL
        """

        try:
            async with self.get_connection() as conn:
                tags_json = json.dumps(tags) if tags else None
                result = await conn.execute(
                    query, tags_json, datetime.utcnow(), agent_id
                )
                return result == "UPDATE 1"
        except Exception:
            return False

    async def batch_update_agent_tags(
        self, updates: List[Tuple[str, List[str]]]
    ) -> Tuple[int, int]:
        """
        批量更新智能体tags

        Args:
            updates: [(agent_id, tags), ...] 更新列表

        Returns:
            Tuple[成功数量, 失败数量]
        """
        if not updates:
            return 0, 0

        success_count = 0
        failure_count = 0

        async with self.get_transaction() as conn:
            for agent_id, tags in updates:
                try:
                    query = """
                        UPDATE agents 
                        SET tags = $1, updated_at = $2
                        WHERE id = $3 AND deleted_at IS NULL
                    """
                    tags_json = json.dumps(tags) if tags else None
                    result = await conn.execute(
                        query, tags_json, datetime.utcnow(), agent_id
                    )

                    if result == "UPDATE 1":
                        success_count += 1
                    else:
                        failure_count += 1

                except Exception:
                    failure_count += 1

        return success_count, failure_count

    async def backup_agents_data(
        self, agent_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        备份智能体数据

        Args:
            agent_ids: 要备份的智能体ID列表

        Returns:
            备份数据列表
        """
        if not agent_ids:
            return []

        placeholders = ",".join(f"${i+1}" for i in range(len(agent_ids)))
        query = f"""
            SELECT id, readable_id, name, gender, personality, tags, created_at, updated_at
            FROM agents 
            WHERE id IN ({placeholders}) AND deleted_at IS NULL
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *agent_ids)
            return [dict(row) for row in rows]

    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {}

        async with self.get_connection() as conn:
            # 总智能体数量
            stats["total_agents"] = await conn.fetchval(
                "SELECT COUNT(*) FROM agents WHERE deleted_at IS NULL"
            )

            # 有personality的智能体数量
            stats["agents_with_personality"] = await conn.fetchval(
                "SELECT COUNT(*) FROM agents WHERE personality IS NOT NULL AND personality != '' AND deleted_at IS NULL"
            )

            # 有tags的智能体数量
            stats["agents_with_tags"] = await conn.fetchval(
                "SELECT COUNT(*) FROM agents WHERE tags IS NOT NULL AND tags::text != '[]' AND deleted_at IS NULL"
            )

            # 既有personality又有tags的智能体数量
            stats["agents_with_both"] = await conn.fetchval(
                """SELECT COUNT(*) FROM agents 
                   WHERE personality IS NOT NULL AND personality != '' 
                   AND tags IS NOT NULL AND tags::text != '[]' 
                   AND deleted_at IS NULL"""
            )

            # 最近创建的智能体数量（过去30天）
            stats["recent_agents"] = await conn.fetchval(
                """SELECT COUNT(*) FROM agents 
                   WHERE created_at > NOW() - INTERVAL '30 days' 
                   AND deleted_at IS NULL"""
            )

        return stats

    def _row_to_agent(self, row) -> Agent:
        """将数据库行转换为Agent对象"""
        tags = None
        if row["tags"]:
            try:
                if isinstance(row["tags"], str):
                    tags = json.loads(row["tags"])
                elif isinstance(row["tags"], list):
                    tags = row["tags"]
            except json.JSONDecodeError:
                tags = None

        return Agent(
            id=row["id"],
            readable_id=row["readable_id"],
            name=row["name"],
            gender=row["gender"],
            personality=row["personality"],
            tags=tags,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def load_config_from_yaml(config_path: str) -> AppConfig:
    """
    从YAML文件加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        应用配置对象
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 提取数据库配置
        db_config = DatabaseConfig(**config_data["database"])

        return AppConfig(
            database=db_config,
            environment=config_data.get("environment", "development"),
        )

    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件未找到: {config_path}")
    except KeyError as e:
        raise ValueError(f"配置文件缺少必需字段: {e}")
    except Exception as e:
        raise ValueError(f"配置文件格式错误: {e}")


async def create_database_manager(config_path: str) -> DatabaseManager:
    """
    创建并初始化数据库管理器

    Args:
        config_path: 配置文件路径

    Returns:
        初始化后的数据库管理器
    """
    app_config = load_config_from_yaml(config_path)
    db_manager = DatabaseManager(app_config.database)
    await db_manager.initialize()
    return db_manager
