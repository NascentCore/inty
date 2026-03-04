#!/usr/bin/env python3
"""
AI角色迁移脚本

用于在测试环境和生产环境之间导出和导入AI角色数据。
该脚本独立于项目代码运行，使用自己的配置文件。

使用方法:
    python agent_migration.py export --from test --config agent_migration_config.yaml
    python agent_migration.py import --to production --file agents_export.json --config agent_migration_config.yaml
"""

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio

import yaml
import asyncpg
from pydantic import BaseModel, ValidationError

from loguru import logger


class DatabaseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    db: str


class EnvironmentConfig(BaseModel):
    name: str
    database: DatabaseConfig


class MigrationConfig(BaseModel):
    environments: Dict[str, EnvironmentConfig]
    migration: Dict[str, Any]
    logging: Dict[str, Any]


class AgentData(BaseModel):
    """AI角色数据模型"""

    id: str
    readable_id: str
    name: str
    gender: str
    avatar: Optional[str] = None
    background: Optional[str] = None
    background_images: Optional[List[str]] = None
    voice_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    intro: Optional[str] = None
    opening: Optional[str] = None
    visibility: str
    photos: Optional[List[str]] = None
    category: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    prompt: Optional[str] = None
    main_prompt: Optional[str] = None
    mode_prompt: Optional[str] = None
    character_card_spec: Optional[str] = None
    character_card_data: Optional[Dict[str, Any]] = None
    personality: Optional[str] = None
    scenario: Optional[str] = None
    message_example: Optional[str] = None
    creator_notes: Optional[str] = None
    post_history_instructions: Optional[str] = None
    alternate_greetings: Optional[List[str]] = None
    character_book: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    character_version: Optional[str] = None
    extensions: Optional[Dict[str, Any]] = None
    creator_id: Optional[str] = None
    creator_info: Optional[Dict[str, Any]] = None


class AgentMigrator:
    """AI角色迁移器"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self._setup_logging()

    def _load_config(self, config_path: str) -> MigrationConfig:
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            return MigrationConfig(**config_data)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {config_path}")
        except ValidationError as e:
            raise ValueError(f"配置文件格式错误: {e}")

    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.logging
        logging.basicConfig(
            level=getattr(logging, log_config.get("level", "INFO")),
            format=log_config.get(
                "format", "%(asctime)s - %(levelname)s - %(message)s"
            ),
            handlers=[
                logging.FileHandler(
                    log_config.get("file", "migration.log"), encoding="utf-8"
                ),
                logging.StreamHandler(sys.stdout),
            ],
        )

    async def _get_db_connection(self, env_name: str) -> asyncpg.Connection:
        """获取数据库连接"""
        if env_name not in self.config.environments:
            raise ValueError(f"未知环境: {env_name}")

        db_config = self.config.environments[env_name].database
        try:
            conn = await asyncpg.connect(
                host=db_config.host,
                port=db_config.port,
                user=db_config.user,
                password=db_config.password,
                database=db_config.db,
            )
            logger.info(f"成功连接到 {env_name} 环境数据库")
            return conn
        except Exception as e:
            logger.error(f"连接 {env_name} 环境数据库失败: {e}")
            raise

    def _parse_json_fields(self, agent_dict: Dict[str, Any]):
        """解析JSON字段"""
        json_fields = [
            "background_images",
            "settings",
            "photos",
            "character_card_data",
            "alternate_greetings",
            "character_book",
            "tags",
            "extensions",
        ]

        for field in json_fields:
            if field in agent_dict and agent_dict[field] is not None:
                value = agent_dict[field]
                if isinstance(value, str):
                    try:
                        if value.lower() == "null":
                            agent_dict[field] = None
                        else:
                            agent_dict[field] = json.loads(value)
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析JSON字段 {field}: {value}")
                        agent_dict[field] = None

    async def export_agents(
        self, from_env: str, output_file: Optional[str] = None
    ) -> str:
        """从指定环境导出AI角色"""
        logger.info(f"开始从 {from_env} 环境导出AI角色")

        export_config = self.config.migration.get("export", {})
        if not output_file:
            output_file = export_config.get("output_file", "agents_export.json")

        conn = await self._get_db_connection(from_env)

        try:
            # 构建查询条件
            where_conditions = []
            params = []
            param_count = 0

            # 过滤已删除的角色
            if not export_config.get("include_deleted", False):
                where_conditions.append("a.deleted_at IS NULL")

            # 状态过滤
            status_filter = export_config.get("status_filter")
            if status_filter:
                param_count += 1
                where_conditions.append(f"a.status = ${param_count}")
                params.append(status_filter)

            # 可见性过滤
            visibility_filter = export_config.get("visibility_filter")
            if visibility_filter:
                param_count += 1
                where_conditions.append(f"a.visibility = ${param_count}")
                params.append(visibility_filter)

            where_clause = (
                " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            # 基础查询
            query = f"""
                SELECT 
                    a.*,
                    u.email as creator_email,
                    u.nickname as creator_nickname,
                    u.phone as creator_phone
                FROM agents a
                LEFT JOIN users u ON a.creator_id = u.id
                {where_clause}
                ORDER BY a.created_at
            """

            rows = await conn.fetch(query, *params)
            logger.info(f"查询到 {len(rows)} 个AI角色")

            # 转换数据
            agents_data = []
            for row in rows:
                agent_dict = dict(row)

                # 处理创建者信息
                creator_info = None
                if export_config.get("include_creator_info", True):
                    creator_info = {
                        "email": agent_dict.pop("creator_email", None),
                        "nickname": agent_dict.pop("creator_nickname", None),
                        "phone": agent_dict.pop("creator_phone", None),
                    }
                    # 移除None值
                    creator_info = {
                        k: v for k, v in creator_info.items() if v is not None
                    }

                agent_dict["creator_info"] = creator_info if creator_info else None

                # 处理JSON字段
                self._parse_json_fields(agent_dict)

                try:
                    agent = AgentData(**agent_dict)
                    agents_data.append(agent.dict())
                except ValidationError as e:
                    logger.warning(
                        f"跳过无效角色数据 {agent_dict.get('id', 'unknown')}: {e}"
                    )
                    continue

            # 保存到文件
            export_data = {
                "export_info": {
                    "source_environment": from_env,
                    "export_time": datetime.now().isoformat(),
                    "total_count": len(agents_data),
                    "config": export_config,
                },
                "agents": agents_data,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"成功导出 {len(agents_data)} 个AI角色到文件: {output_file}")
            return output_file

        finally:
            await conn.close()

    async def import_agents(self, to_env: str, import_file: str) -> int:
        """向指定环境导入AI角色"""
        logger.info(f"开始向 {to_env} 环境导入AI角色")

        import_config = self.config.migration.get("import", {})

        # 读取导入文件
        try:
            with open(import_file, "r", encoding="utf-8") as f:
                import_data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"导入文件未找到: {import_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"导入文件格式错误: {e}")

        agents_data = import_data.get("agents", [])
        if not agents_data:
            logger.warning("导入文件中没有AI角色数据")
            return 0

        logger.info(f"读取到 {len(agents_data)} 个AI角色待导入")

        conn = await self._get_db_connection(to_env)

        try:
            imported_count = 0
            skipped_count = 0
            error_count = 0

            for agent_data in agents_data:
                try:
                    await self._import_single_agent(conn, agent_data, import_config)
                    imported_count += 1
                    logger.debug(f"成功导入角色: {agent_data.get('name', 'unknown')}")
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"导入角色失败 {agent_data.get('name', 'unknown')}: {e}"
                    )
                    if not import_config.get("skip_validation", False):
                        continue

            logger.info(
                f"导入完成: 成功 {imported_count}, 跳过 {skipped_count}, 错误 {error_count}"
            )
            return imported_count

        finally:
            await conn.close()

    async def _import_single_agent(
        self,
        conn: asyncpg.Connection,
        agent_data: Dict[str, Any],
        import_config: Dict[str, Any],
    ):
        """导入单个AI角色"""
        # 处理ID
        original_id = agent_data["id"]
        if import_config.get("keep_original_ids", False):
            new_id = original_id
        else:
            new_id = str(uuid.uuid4())

        # 检查是否已存在
        existing = await conn.fetchrow(
            "SELECT id FROM agents WHERE id = $1 OR readable_id = $2",
            new_id,
            agent_data["readable_id"],
        )

        if existing:
            if import_config.get("update_existing", False):
                await self._update_agent(conn, agent_data, import_config, new_id)
            else:
                logger.info(f"跳过已存在的角色: {agent_data['name']}")
                return
        else:
            await self._insert_agent(conn, agent_data, import_config, new_id)

    async def _ensure_creator_exists(
        self,
        conn: asyncpg.Connection,
        agent_data: Dict[str, Any],
        creator_id: Optional[str],
        import_config: Dict[str, Any],
    ) -> Optional[str]:
        """确保创建者存在，如果不存在则创建或使用默认值"""
        if not creator_id:
            logger.warning(
                f"角色 {agent_data.get('name', 'unknown')} 没有创建者ID，将设置为NULL"
            )
            return None

        # 检查创建者是否存在
        existing_user = await conn.fetchrow(
            "SELECT id FROM users WHERE id = $1", creator_id
        )
        if existing_user:
            return creator_id

        # 创建者不存在，尝试创建
        creator_info = agent_data.get("creator_info", {})
        if creator_info and import_config.get("create_missing_users", True):
            try:
                await self._create_user(conn, creator_id, creator_info)
                logger.info(f"创建了缺失的用户: {creator_id}")
                return creator_id
            except Exception as e:
                logger.error(f"创建用户失败 {creator_id}: {e}")

        # 使用默认创建者ID或设为NULL
        default_creator = import_config.get("default_creator_id")
        if default_creator:
            # 检查默认创建者是否存在
            default_exists = await conn.fetchrow(
                "SELECT id FROM users WHERE id = $1", default_creator
            )
            if default_exists:
                logger.warning(
                    f"使用默认创建者 {default_creator} 替代不存在的创建者 {creator_id}"
                )
                return default_creator

        logger.warning(f"创建者 {creator_id} 不存在且无法创建，将设置为NULL")
        return None

    async def _create_user(
        self, conn: asyncpg.Connection, user_id: str, creator_info: Dict[str, Any]
    ):
        """创建用户"""
        email = creator_info.get("email")
        nickname = creator_info.get("nickname", "Imported User")
        phone = creator_info.get("phone")

        # 基本用户信息
        user_data = {
            "id": user_id,
            "email": email,
            "nickname": nickname,
            "phone": phone,
            "is_active": True,
            "created_at": datetime.now(),
            "auth_method": "IMPORTED",
        }

        # 移除None值
        user_data = {k: v for k, v in user_data.items() if v is not None}

        # 构建插入语句
        columns = list(user_data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = [user_data[col] for col in columns]

        query = f"""
            INSERT INTO users ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """

        await conn.execute(query, *values)

    async def _insert_agent(
        self,
        conn: asyncpg.Connection,
        agent_data: Dict[str, Any],
        import_config: Dict[str, Any],
        new_id: str,
    ):
        """插入新的AI角色"""
        # 处理创建者ID
        creator_id = agent_data.get("creator_id")
        if not creator_id:
            creator_id = import_config.get("default_creator_id")

        # 确保创建者存在
        creator_id = await self._ensure_creator_exists(
            conn, agent_data, creator_id, import_config
        )

        # 如果指定了强制状态
        status = import_config.get("force_status") or agent_data["status"]

        # 移除不需要的字段
        agent_data_clean = {
            k: v
            for k, v in agent_data.items()
            if k not in ["creator_info"] and v is not None
        }

        # 更新字段
        agent_data_clean["id"] = new_id
        agent_data_clean["creator_id"] = creator_id
        agent_data_clean["status"] = status
        agent_data_clean["created_at"] = datetime.now()
        agent_data_clean["updated_at"] = None

        # 构建插入语句
        columns = list(agent_data_clean.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = [agent_data_clean[col] for col in columns]

        # 处理JSON字段
        for i, (col, val) in enumerate(zip(columns, values)):
            if (
                col
                in [
                    "background_images",
                    "settings",
                    "photos",
                    "character_card_data",
                    "alternate_greetings",
                    "character_book",
                    "tags",
                    "extensions",
                ]
                and val
            ):
                values[i] = json.dumps(val) if not isinstance(val, str) else val

        query = f"""
            INSERT INTO agents ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """

        await conn.execute(query, *values)

    async def _update_agent(
        self,
        conn: asyncpg.Connection,
        agent_data: Dict[str, Any],
        import_config: Dict[str, Any],
        agent_id: str,
    ):
        """更新现有AI角色"""
        # 构建更新语句
        update_fields = []
        values = []
        param_count = 0

        # 要更新的字段（排除ID和时间戳）
        exclude_fields = {"id", "readable_id", "created_at", "creator_info"}

        for key, value in agent_data.items():
            if key in exclude_fields or value is None:
                continue

            param_count += 1
            update_fields.append(f"{key} = ${param_count}")

            # 处理JSON字段
            if key in [
                "background_images",
                "settings",
                "photos",
                "character_card_data",
                "alternate_greetings",
                "character_book",
                "tags",
                "extensions",
            ]:
                value = json.dumps(value) if not isinstance(value, str) else value

            values.append(value)

        # 添加更新时间
        param_count += 1
        update_fields.append(f"updated_at = ${param_count}")
        values.append(datetime.now())

        # 添加WHERE条件
        param_count += 1
        values.append(agent_id)

        query = f"""
            UPDATE agents 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
        """

        await conn.execute(query, *values)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI角色迁移工具")
    parser.add_argument("action", choices=["export", "import"], help="操作类型")
    parser.add_argument(
        "--config", "-c", default="agent_migration_config.yaml", help="配置文件路径"
    )
    parser.add_argument("--from", dest="from_env", help="源环境名称 (export时使用)")
    parser.add_argument("--to", dest="to_env", help="目标环境名称 (import时使用)")
    parser.add_argument("--file", "-f", help="导入/导出文件路径")

    args = parser.parse_args()

    try:
        migrator = AgentMigrator(args.config)

        if args.action == "export":
            if not args.from_env:
                print("错误: export操作需要指定 --from 参数")
                sys.exit(1)

            output_file = await migrator.export_agents(args.from_env, args.file)
            print(f"导出完成: {output_file}")

        elif args.action == "import":
            if not args.to_env:
                print("错误: import操作需要指定 --to 参数")
                sys.exit(1)
            if not args.file:
                print("错误: import操作需要指定 --file 参数")
                sys.exit(1)

            count = await migrator.import_agents(args.to_env, args.file)
            print(f"导入完成: {count} 个角色")

    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
