#!/usr/bin/env python3
"""
同步dev环境的角色数据到prod环境

从dev环境中同步指定运营用户创建的未删除角色到prod环境。
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
from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import load_only, sessionmaker

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


async def ensure_operator_user(session: AsyncSession, user_config: dict) -> User:
    """确保运营用户存在，不存在则创建"""
    user_id = user_config["id"]

    result = await session.execute(
        select(User)
        .options(
            load_only(
                User.id,
            )
        )
        .where(User.id == user_id)
    )
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
        is_active=True,
        is_superuser=True,
        auth_type=AuthType.GOOGLE,
    )

    session.add(user)
    await session.commit()
    logger.info(f"运营用户创建成功: {user_id}")
    return user


async def fetch_agents(session: AsyncSession, user_id: str) -> list[Agent]:
    """获取指定用户的未删除角色"""
    result = await session.execute(
        select(Agent)
        .options(load_only(*AGENT_FIELDS_TO_SYNC))
        .where(Agent.creator_id == user_id, Agent.deleted_at.is_(None))
    )
    agents = result.scalars().all()
    return list(agents)


AGENT_FIELDS_TO_SYNC = [
    # 基础字段
    Agent.id,
    Agent.name,
    Agent.gender,
    Agent.avatar,
    Agent.background,
    Agent.background_images,
    Agent.background_animated,
    Agent.voice_id,
    Agent.settings,
    Agent.intro,
    Agent.opening,
    Agent.visibility,
    Agent.photos,
    Agent.category,
    Agent.status,
    Agent.prompt,
    # 主提示词和模式提示词字段
    Agent.main_prompt,
    Agent.mode_prompt,
    # 角色卡相关字段
    Agent.character_card_spec,
    Agent.character_card_data,
    Agent.personality,
    Agent.scenario,
    Agent.message_example,
    Agent.creator_notes,
    Agent.post_history_instructions,
    Agent.alternate_greetings,
    Agent.character_book,
    Agent.tags,
    Agent.character_version,
    Agent.extensions,
    Agent.meta_data,
    # 语音相关字段
    Agent.opening_audio_url,
    # 外键
    Agent.creator_id,
]

FIELDS_TO_SYNC = [field.name for field in AGENT_FIELDS_TO_SYNC]


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


def copy_agent_fields(source: Agent, target: Agent) -> None:
    """将源Agent的字段复制到目标Agent"""
    for field in FIELDS_TO_SYNC:
        setattr(target, field, getattr(source, field))


async def sync_agents(
    dev_session: AsyncSession,
    prod_session: AsyncSession,
    user_id: str,
    dry_run: bool = False,
) -> None:
    """同步角色数据"""
    logger.info("=" * 60)
    logger.info("开始同步角色数据")
    logger.info(f"运营用户ID: {user_id}")
    logger.info(f"模式: {'预览模式 (dry-run)' if dry_run else '执行模式'}")
    logger.info("=" * 60)

    dev_agents_list = await fetch_agents(dev_session, user_id)
    logger.info(f"Dev环境找到 {len(dev_agents_list)} 个未删除角色")

    prod_agents_list = await fetch_agents(prod_session, user_id)
    logger.info(f"Prod环境找到 {len(prod_agents_list)} 个未删除角色")

    dev_agents = {agent.id: agent for agent in dev_agents_list}
    prod_agents = {agent.id: agent for agent in prod_agents_list}

    to_create_ids = dev_agents.keys() - prod_agents.keys()

    to_check_update_ids = dev_agents.keys() & prod_agents.keys()

    to_update_ids = [
        agent_id
        for agent_id in to_check_update_ids
        if compare_agents(dev_agents[agent_id], prod_agents[agent_id])
    ]

    logger.info("")
    logger.info("同步计划:")
    logger.info(f"  需要创建: {len(to_create_ids)} 个角色")
    logger.info(f"  需要更新: {len(to_update_ids)} 个角色")
    logger.info(f"  无需变更: {len(to_check_update_ids) - len(to_update_ids)} 个角色")

    if dry_run:
        logger.info("")
        logger.info("【预览模式】以下是详细操作列表:")
        logger.info("")

        if to_create_ids:
            logger.info("创建角色列表:")
            for agent_id in to_create_ids:
                agent = dev_agents[agent_id]
                logger.info(f"  ✨ 创建: {agent.name} (ID: {agent_id})")

        if to_update_ids:
            logger.info("")
            logger.info("更新角色列表:")
            for agent_id in to_update_ids:
                agent = dev_agents[agent_id]
                logger.info(f"  🔄 更新: {agent.name} (ID: {agent_id})")

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
        # 第一步：更新操作
        if to_update_ids:
            logger.info("第 1 步：执行更新操作...")
            for agent_id in to_update_ids:
                source_agent = dev_agents[agent_id]

                # 构建更新字典，只包含 FIELDS_TO_SYNC 中的字段
                update_dict = {}
                for field in FIELDS_TO_SYNC:
                    update_dict[field] = getattr(source_agent, field)

                # 使用 update() 语句避免触发乐观锁机制
                await prod_session.execute(
                    update(Agent).where(Agent.id == agent_id).values(**update_dict)
                )

                updated_count += 1
                logger.info(f"🔄 更新成功: {source_agent.name} (ID: {agent_id})")
            logger.info("")

        # 第二步：创建操作
        if to_create_ids:
            logger.info("第 2 步：执行创建操作...")
            for agent_id in to_create_ids:
                source_agent = dev_agents[agent_id]

                insert_dict = {}
                for field in FIELDS_TO_SYNC:
                    insert_dict[field] = getattr(source_agent, field)

                # 使用 insert() 语句避免触发乐观锁机制
                await prod_session.execute(insert(Agent).values(**insert_dict))

                created_count += 1
                logger.info(f"✨ 创建成功: {source_agent.name} (ID: {agent_id})")

        # 所有操作成功，提交事务
        await prod_session.commit()
        logger.info("")
        logger.info("=" * 60)
        logger.info("同步完成！")
        logger.info(f"  创建: {created_count} 个")
        logger.info(f"  更新: {updated_count} 个")
        logger.info("=" * 60)

    except Exception as e:
        await prod_session.rollback()
        logger.error("")
        logger.error("=" * 60)
        logger.error("同步失败，已回滚所有操作")
        logger.error(f"  已完成: 创建 {created_count} 个，更新 {updated_count} 个")
        logger.error(f"  错误: {e}")
        logger.error("=" * 60)
        raise


async def main():
    parser = argparse.ArgumentParser(description="同步dev环境角色到prod环境")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际执行操作",
    )
    args = parser.parse_args()

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
    prod_engine = create_async_engine(prod_url, echo=False, **prod_engine_kwargs)

    DevSession = sessionmaker(
        bind=dev_engine, class_=AsyncSession, expire_on_commit=False
    )
    ProdSession = sessionmaker(
        bind=prod_engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        # 先测试连接
        logger.info("正在测试数据库连接...")
        dev_ok = await test_connection(dev_engine, "Dev")
        prod_ok = await test_connection(prod_engine, "Prod")

        if not dev_ok:
            logger.error("Dev 数据库连接失败，请检查配置和网络连接，需要运行在 GCP 上")
            sys.exit(1)
        if not prod_ok:
            logger.error("Prod 数据库连接失败，请检查配置和网络连接，需要运行在 GCP 上")
            sys.exit(1)

        logger.info("")
        async with DevSession() as dev_session, ProdSession() as prod_session:
            logger.info("数据库会话创建成功")

            user_config = config["operator_user"]
            user_id = user_config["id"]

            result = await dev_session.execute(
                select(User)
                .options(
                    load_only(
                        User.id,
                    )
                )
                .where(User.id == user_id)
            )
            dev_user = result.scalar_one_or_none()
            if not dev_user:
                logger.error(f"Dev环境中不存在运营用户: {user_id}")
                sys.exit(1)

            logger.info(f"Dev环境运营用户: {user_id=}")

            if not args.dry_run:
                await ensure_operator_user(prod_session, user_config)

            await sync_agents(dev_session, prod_session, user_id, args.dry_run)

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
