#!/usr/bin/env python3
"""
同步角色数据在 dev 与 prod 环境之间

支持两个方向：
- dev-to-prod：从 dev 同步指定运营用户创建的角色到 prod
- prod-to-dev：从 prod 按名称同步指定角色到 dev

支持创建和更新操作。
"""

import argparse
import asyncio
import random
import sys
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.agent import prompts
from app.models.agent import Agent
from app.models.user import AuthType, Gender, User


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    config_file = Path(__file__).parent / config_path
    if not config_file.exists():
        logger.error(f"配置文件不存在: {config_file}")
        logger.info("请复制 config.yaml.example 为 config.yaml 并修改配置")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_db_url(db_config: dict) -> str:
    """创建数据库连接URL"""
    return (
        f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['db']}"
    )


def get_engine_kwargs(db_config: dict) -> dict:
    """从配置中提取引擎参数"""
    kwargs = {}

    if "pool_size" in db_config:
        kwargs["pool_size"] = db_config["pool_size"]
    if "max_overflow" in db_config:
        kwargs["max_overflow"] = db_config["max_overflow"]
    if "pool_timeout" in db_config:
        kwargs["pool_timeout"] = db_config["pool_timeout"]
    if "pool_recycle" in db_config:
        kwargs["pool_recycle"] = db_config["pool_recycle"]
    if "pool_pre_ping" in db_config:
        kwargs["pool_pre_ping"] = db_config["pool_pre_ping"]

    # 配置 asyncpg 连接参数
    connect_args = {}
    if "command_timeout" in db_config:
        connect_args["command_timeout"] = db_config["command_timeout"]
    if "connect_timeout" in db_config:
        connect_args["timeout"] = db_config["connect_timeout"]

    # 设置应用名称
    connect_args["server_settings"] = {
        "application_name": "sync_agents_dev_to_prod",
    }

    if connect_args:
        kwargs["connect_args"] = connect_args

    return kwargs


async def test_connection(engine, db_name: str) -> bool:
    """测试数据库连接"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
            logger.info(f"✓ {db_name} 数据库连接测试成功")
            return True
    except Exception as e:
        logger.error(f"✗ {db_name} 数据库连接测试失败: {e}")
        return False


def generate_readable_id() -> str:
    """生成8位随机数字ID"""
    return "".join(str(random.randint(0, 9)) for _ in range(8))


async def get_next_readable_id(session: AsyncSession) -> str:
    """获取下一个可用的 readable_id（自增），确保唯一性"""
    # 使用 no_autoflush 避免在查询时触发 autoflush（同步上下文管理器）
    with session.no_autoflush:
        result = await session.execute(
            select(Agent.readable_id)
            .where(Agent.readable_id.regexp_match(r"^\d{8}$"))
            .order_by(Agent.readable_id.desc())
            .limit(1)
        )
        max_id = result.scalar_one_or_none()

        if max_id:
            next_id = int(max_id) + 1
        else:
            next_id = 10000000

        # 确保生成的 ID 是唯一的（循环检查直到找到可用的）
        max_attempts = 1000
        for _ in range(max_attempts):
            candidate_id = str(next_id).zfill(8)
            check_result = await session.execute(
                select(Agent).where(Agent.readable_id == candidate_id)
            )
            if check_result.scalar_one_or_none() is None:
                return candidate_id
            next_id += 1

        # 如果循环了 1000 次还没找到，抛出异常
        raise RuntimeError(
            f"无法生成唯一的 readable_id，已尝试 {max_attempts} 次"
        )


async def ensure_unique_readable_id(
    session: AsyncSession,
    readable_id: Optional[str],
    exclude_agent_id: Optional[str] = None,
) -> str:
    """确保 readable_id 唯一，如果冲突或为空则使用自增 ID

    Args:
        session: 数据库会话
        readable_id: 要检查的 readable_id，可以为 None 或空字符串
        exclude_agent_id: 排除的 agent ID（用于更新场景，排除当前 agent）

    Returns:
        唯一的 readable_id，如果冲突或为空则返回自增的新 ID
    """
    # 如果 readable_id 为空（None、空字符串或只包含空白字符），直接生成新的自增 ID
    if not readable_id or not readable_id.strip():
        new_id = await get_next_readable_id(session)
        logger.warning(f"⚠️  readable_id 为空，使用自增 ID: {new_id}")
        return new_id

    # 使用 no_autoflush 避免在查询时触发 autoflush，防止冲突（同步上下文管理器）
    with session.no_autoflush:
        query = select(Agent).where(Agent.readable_id == readable_id)
        if exclude_agent_id:
            query = query.where(Agent.id != exclude_agent_id)

        result = await session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            new_id = await get_next_readable_id(session)
            logger.warning(
                f"⚠️  readable_id 冲突: {readable_id} 已被其他 agent 使用，"
                f"使用自增 ID: {new_id}"
            )
            return new_id

    return readable_id


async def ensure_operator_user(
    session: AsyncSession, user_config: dict
) -> User:
    """确保运营用户存在，不存在则创建"""
    user_id = user_config["id"]

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user:
        logger.info(f"运营用户已存在: {user_id}")
        return user

    logger.warning(f"运营用户不存在，正在创建: {user_id}")
    user = User(
        id=user_id,
        nickname=user_config["nickname"],
        email=user_config["email"],
        gender=Gender[user_config["gender"]],
        age_group=user_config["age_group"],
        description=user_config["description"],
        is_superuser=True,
        auth_type=AuthType.GOOGLE,
        readable_id=generate_readable_id(),
    )

    session.add(user)
    await session.commit()
    logger.info(f"运营用户创建成功: {user_id}")
    return user


async def get_alembic_version(session: AsyncSession) -> Optional[str]:
    """获取数据库的 alembic 版本"""
    result = await session.execute(
        text("SELECT version_num FROM alembic_version LIMIT 1")
    )
    version = result.scalar_one_or_none()
    return version


async def check_alembic_versions(
    dev_session: AsyncSession, prod_session: AsyncSession
) -> bool:
    """检查 dev 和 prod 数据库的 alembic 版本是否一致"""
    dev_version = await get_alembic_version(dev_session)
    prod_version = await get_alembic_version(prod_session)

    if dev_version is None or prod_version is None:
        logger.warning("无法获取 alembic 版本，跳过版本检查")
        return True

    if dev_version != prod_version:
        logger.error("=" * 60)
        logger.error("⚠️  Alembic 版本不一致！")
        logger.error(f"  Dev 环境版本: {dev_version}")
        logger.error(f"  Prod 环境版本: {prod_version}")
        logger.error("=" * 60)
        logger.error("请确保两个数据库的 alembic 版本一致后再进行同步")
        logger.error("可以使用以下命令检查版本:")
        logger.error("  alembic current")
        logger.error("=" * 60)
        return False

    logger.info(f"✓ Alembic 版本一致: {dev_version}")
    return True


async def fetch_agents(session: AsyncSession, user_id: str) -> list[Agent]:
    """获取指定用户的未删除角色"""
    result = await session.execute(
        select(Agent).where(
            Agent.creator_id == user_id, Agent.deleted_at.is_(None)
        )
    )
    agents = result.scalars().all()
    return list(agents)


async def fetch_agents_by_name(session: AsyncSession, name: str) -> list[Agent]:
    """按名称获取未删除角色"""
    result = await session.execute(
        select(Agent).where(Agent.name == name, Agent.deleted_at.is_(None))
    )
    return list(result.scalars().all())


FIELDS_TO_SYNC = [
    # 基础字段
    "name",
    "gender",
    "avatar",
    "background",
    "background_images",
    "background_animated",
    "voice_id",
    "settings",
    "intro",
    "opening",
    "visibility",
    "photos",
    "exclusive_photos",
    "category",
    "status",
    "source",
    "prompt",
    # 主提示词和模式提示词字段
    "main_prompt",
    "mode_prompt",
    # 角色设定相关字段
    "personality",
    "scenario",
    "message_example",
    "creator_notes",
    "post_history_instructions",
    "alternate_greetings",
    "character_book",
    "tags",
    "character_version",
    "extensions",
    "meta_data",
    # 语音相关字段
    "opening_audio_url",
    # 外键
    "creator_id",
]


def is_custom_main_prompt(prompt_value: Optional[str]) -> bool:
    """判断 main_prompt 是否为自定义文本（而非预设 ID）"""
    if not prompt_value:
        return False
    try:
        prompts.get_main_prompt_by_id(prompt_value)
        return False
    except ValueError:
        return True


def is_custom_mode_prompt(prompt_value: Optional[str]) -> bool:
    """判断 mode_prompt 是否为自定义文本（而非预设 ID）"""
    if not prompt_value:
        return False
    try:
        prompts.get_mode_prompt_by_id(prompt_value)
        return False
    except ValueError:
        return True


def compare_agents(agent1: Agent, agent2: Agent) -> bool:
    """
    比较两个Agent对象是否相同
    返回True表示不同需要更新，False表示相同不需要更新
    """
    for field in FIELDS_TO_SYNC:
        val1 = getattr(agent1, field)
        val2 = getattr(agent2, field)
        if val1 != val2:
            return True

    return False


def needs_agent_update(source_agent: Agent, target_agent: Agent) -> bool:
    """判断目标角色是否需要更新（包含恢复软删除）。"""
    if target_agent.deleted_at is not None:
        return True
    return compare_agents(source_agent, target_agent)


def copy_agent_fields(source: Agent, target: Agent) -> None:
    """将源Agent的字段复制到目标Agent"""
    for field in FIELDS_TO_SYNC:
        value = getattr(source, field)
        # 如果 main_prompt 或 mode_prompt 是自定义文本，则设置为 None 使用默认值
        if field == "main_prompt" and is_custom_main_prompt(value):
            value = None
        elif field == "mode_prompt" and is_custom_mode_prompt(value):
            value = None
        setattr(target, field, value)


async def sync_agents(
    source_session: AsyncSession,
    target_session: AsyncSession,
    source_agents: dict[str, Agent],
    target_agents: dict[str, Agent],
    source_label: str,
    target_label: str,
    dry_run: bool = False,
) -> None:
    """同步角色数据：从 source 到 target"""
    logger.info("=" * 60)
    logger.info("开始同步角色数据")
    logger.info(f"方向: {source_label} → {target_label}")
    logger.info(f"模式: {'预览模式 (dry-run)' if dry_run else '执行模式'}")
    logger.info("=" * 60)

    logger.info(f"{source_label}环境找到 {len(source_agents)} 个角色")
    logger.info(f"{target_label}环境找到 {len(target_agents)} 个角色")

    to_create_ids = source_agents.keys() - target_agents.keys()
    to_check_update_ids = source_agents.keys() & target_agents.keys()
    to_update_ids = [
        agent_id
        for agent_id in to_check_update_ids
        if needs_agent_update(source_agents[agent_id], target_agents[agent_id])
    ]

    logger.info("")
    logger.info("同步计划:")
    logger.info(f"  需要创建: {len(to_create_ids)} 个角色")
    logger.info(f"  需要更新: {len(to_update_ids)} 个角色")
    logger.info(
        f"  无需变更: {len(to_check_update_ids) - len(to_update_ids)} 个角色"
    )

    if dry_run:
        logger.info("")
        logger.info("【预览模式】以下是详细操作列表:")
        logger.info("")

        if to_create_ids:
            logger.info("创建角色列表:")
            for agent_id in to_create_ids:
                agent = source_agents[agent_id]
                custom_prompts = []
                if is_custom_main_prompt(agent.main_prompt):
                    custom_prompts.append("main_prompt")
                if is_custom_mode_prompt(agent.mode_prompt):
                    custom_prompts.append("mode_prompt")
                prompt_note = (
                    f" [自定义提示词将被忽略: {', '.join(custom_prompts)}]"
                    if custom_prompts
                    else ""
                )
                logger.info(
                    f"  ✨ 创建: {agent.name} (ID: {agent_id}){prompt_note}"
                )

        if to_update_ids:
            logger.info("")
            logger.info("更新角色列表:")
            for agent_id in to_update_ids:
                agent = source_agents[agent_id]
                custom_prompts = []
                if is_custom_main_prompt(agent.main_prompt):
                    custom_prompts.append("main_prompt")
                if is_custom_mode_prompt(agent.mode_prompt):
                    custom_prompts.append("mode_prompt")
                prompt_note = (
                    f" [自定义提示词将被忽略: {', '.join(custom_prompts)}]"
                    if custom_prompts
                    else ""
                )
                logger.info(
                    f"  🔄 更新: {agent.name} (ID: {agent_id}){prompt_note}"
                )

        logger.info("")
        logger.info("=" * 60)
        logger.info("预览完成，未执行任何操作")
        logger.info("如需执行，请去掉 --dry-run 参数")
        logger.info("=" * 60)
        return

    logger.info("")
    logger.info("开始执行同步操作...")
    logger.info("操作顺序：1) 更新 → 2) 创建")
    logger.info("")

    created_count = 0
    updated_count = 0

    try:
        if to_update_ids:
            logger.info("第 1 步：执行更新操作...")
            for agent_id in to_update_ids:
                source_agent = source_agents[agent_id]

                result = await target_session.execute(
                    select(Agent).where(Agent.id == agent_id)
                )
                target_agent = result.scalar_one()

                copy_agent_fields(source_agent, target_agent)
                target_agent.deleted_at = None
                target_agent.readable_id = await ensure_unique_readable_id(
                    target_session,
                    target_agent.readable_id,
                    exclude_agent_id=agent_id,
                )

                await target_session.flush()
                updated_count += 1
                logger.info(
                    f"🔄 更新成功: {target_agent.name} (ID: {agent_id})"
                )
            logger.info("")

        if to_create_ids:
            logger.info("第 2 步：执行创建操作...")
            for agent_id in to_create_ids:
                source_agent = source_agents[agent_id]
                source_session.expunge(source_agent)

                new_agent = Agent(id=source_agent.id)
                copy_agent_fields(source_agent, new_agent)
                new_agent.readable_id = await ensure_unique_readable_id(
                    target_session, new_agent.readable_id
                )

                target_session.add(new_agent)
                await target_session.flush()
                created_count += 1
                logger.info(f"✨ 创建成功: {new_agent.name} (ID: {agent_id})")

        await target_session.commit()
        logger.info("")
        logger.info("=" * 60)
        logger.info("同步完成！")
        logger.info(f"  创建: {created_count} 个")
        logger.info(f"  更新: {updated_count} 个")
        logger.info("=" * 60)

    except Exception as e:
        await target_session.rollback()
        logger.error("")
        logger.error("=" * 60)
        logger.error("同步失败，已回滚所有操作")
        logger.error(
            f"  已完成: 创建 {created_count} 个，更新 {updated_count} 个"
        )
        logger.error(f"  错误: {e}")
        logger.error("=" * 60)
        raise


async def main():
    parser = argparse.ArgumentParser(
        description="同步角色数据在 dev 与 prod 环境之间"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）",
    )
    parser.add_argument(
        "--direction",
        choices=["dev-to-prod", "prod-to-dev"],
        default="dev-to-prod",
        help="同步方向（默认: dev-to-prod）",
    )
    parser.add_argument(
        "--agent-name",
        help="按名称筛选角色；prod-to-dev 时必填",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际执行操作",
    )
    args = parser.parse_args()

    if args.direction == "prod-to-dev" and not args.agent_name:
        logger.error("prod-to-dev 方向必须指定 --agent-name")
        sys.exit(1)

    config = load_config(args.config)

    log_level = config.get("logging", {}).get("level", "INFO")
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    dev_db_config = config["dev_database"]
    prod_db_config = config["prod_database"]

    dev_url = create_db_url(dev_db_config)
    prod_url = create_db_url(prod_db_config)

    dev_engine_kwargs = get_engine_kwargs(dev_db_config)
    prod_engine_kwargs = get_engine_kwargs(prod_db_config)

    logger.info(
        f"正在连接 Dev 数据库: {dev_db_config['host']}:{dev_db_config['port']}/{dev_db_config['db']}"
    )
    dev_engine = create_async_engine(dev_url, echo=False, **dev_engine_kwargs)

    logger.info(
        f"正在连接 Prod 数据库: {prod_db_config['host']}:{prod_db_config['port']}/{prod_db_config['db']}"
    )
    prod_engine = create_async_engine(
        prod_url, echo=False, **prod_engine_kwargs
    )

    DevSession = sessionmaker(
        bind=dev_engine, class_=AsyncSession, expire_on_commit=False
    )
    ProdSession = sessionmaker(
        bind=prod_engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        logger.info("正在测试数据库连接...")
        dev_ok = await test_connection(dev_engine, "Dev")
        prod_ok = await test_connection(prod_engine, "Prod")

        if not dev_ok:
            logger.error(
                "Dev 数据库连接失败，请检查配置和网络连接，需要运行在 GCP 上"
            )
            sys.exit(1)
        if not prod_ok:
            logger.error(
                "Prod 数据库连接失败，请检查配置和网络连接，需要运行在 GCP 上"
            )
            sys.exit(1)

        logger.info("")
        async with DevSession() as dev_session, ProdSession() as prod_session:
            logger.info("数据库会话创建成功")

            if not await check_alembic_versions(dev_session, prod_session):
                logger.error("同步终止：Alembic 版本不一致")
                sys.exit(1)

            user_config = config["operator_user"]
            user_id = user_config["id"]

            if args.direction == "dev-to-prod":
                source_session = dev_session
                target_session = prod_session
                source_label = "Dev"
                target_label = "Prod"

                source_list = await fetch_agents(dev_session, user_id)
                if args.agent_name:
                    source_list = [
                        a for a in source_list if a.name == args.agent_name
                    ]
                source_agents = {a.id: a for a in source_list}

                source_ids = list(source_agents.keys())
                if source_ids:
                    result = await prod_session.execute(
                        select(Agent).where(Agent.id.in_(source_ids))
                    )
                    target_agents = {a.id: a for a in result.scalars().all()}
                else:
                    target_agents = {}

                result = await dev_session.execute(
                    select(User).where(User.id == user_id)
                )
                dev_user = result.scalar_one_or_none()
                if not dev_user:
                    logger.error(f"Dev环境中不存在运营用户: {user_id}")
                    sys.exit(1)
                logger.info(f"Dev环境运营用户: {dev_user.nickname} ({user_id})")

                if not args.dry_run:
                    await ensure_operator_user(prod_session, user_config)
            else:
                source_session = prod_session
                target_session = dev_session
                source_label = "Prod"
                target_label = "Dev"

                source_list = await fetch_agents_by_name(
                    prod_session, args.agent_name
                )
                if not source_list:
                    logger.error(
                        f"Prod 中不存在名为 {args.agent_name!r} 的未删除角色"
                    )
                    sys.exit(1)
                source_agents = {a.id: a for a in source_list}

                target_ids = [a.id for a in source_list]
                result = await target_session.execute(
                    select(Agent).where(Agent.id.in_(target_ids))
                )
                target_agents = {a.id: a for a in result.scalars().all()}

                if not args.dry_run:
                    await ensure_operator_user(dev_session, user_config)

            await sync_agents(
                source_session,
                target_session,
                source_agents,
                target_agents,
                source_label,
                target_label,
                args.dry_run,
            )

    except ConnectionResetError as e:
        logger.error("数据库连接被重置，可能的原因：")
        logger.error("  1. 数据库服务器拒绝连接")
        logger.error("  2. 网络连接不稳定")
        logger.error("  3. 防火墙或安全组配置问题")
        logger.error("  4. SSL/TLS 配置问题")
        logger.error(f"详细错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        logger.error(f"同步过程中发生错误: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await dev_engine.dispose()
        await prod_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
