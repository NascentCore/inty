#!/usr/bin/env python3
"""
同步dev环境的角色数据到prod环境

从dev环境中同步指定运营用户创建的未删除角色到prod环境。
支持创建、更新和删除操作。
"""
import argparse
import asyncio
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).parent.parent.parent))

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


def generate_readable_id() -> str:
    """生成8位随机数字ID"""
    return "".join(str(random.randint(0, 9)) for _ in range(8))


async def get_next_readable_id(session: AsyncSession) -> str:
    """获取下一个可用的 readable_id（自增）"""
    result = await session.execute(
        select(Agent.readable_id)
        .where(Agent.readable_id.regexp_match(r"^\d{8}$"))
        .order_by(Agent.readable_id.desc())
        .limit(1)
    )
    max_id = result.scalar_one_or_none()

    if max_id:
        next_id = int(max_id) + 1
        return str(next_id).zfill(8)
    else:
        return "10000000"


async def ensure_unique_readable_id(session: AsyncSession, readable_id: str) -> str:
    """确保 readable_id 唯一，如果冲突则生成新的自增 ID"""
    result = await session.execute(
        select(Agent).where(Agent.readable_id == readable_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        new_id = await get_next_readable_id(session)
        logger.warning(
            f"⚠️  readable_id 冲突: {readable_id} 已存在，使用新 ID: {new_id}"
        )
        return new_id

    return readable_id


async def ensure_operator_user(session: AsyncSession, user_config: dict) -> User:
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
        is_active=True,
        is_superuser=True,
        auth_type=AuthType.GOOGLE,
        readable_id=generate_readable_id(),
    )

    session.add(user)
    await session.commit()
    logger.info(f"运营用户创建成功: {user_id}")
    return user


async def fetch_agents(session: AsyncSession, user_id: str) -> list[Agent]:
    """获取指定用户的未删除角色"""
    result = await session.execute(
        select(Agent).where(Agent.creator_id == user_id, Agent.deleted_at.is_(None))
    )
    agents = result.scalars().all()
    return list(agents)


def compare_agents(agent1: Agent, agent2: Agent) -> bool:
    """
    比较两个Agent对象是否相同
    返回True表示不同需要更新，False表示相同不需要更新
    """
    fields_to_compare = [
        "readable_id",
        "name",
        "gender",
        "avatar",
        "background",
        "background_images",
        "voice_id",
        "settings",
        "intro",
        "opening",
        "visibility",
        "photos",
        "category",
        "status",
        "prompt",
        "main_prompt",
        "mode_prompt",
        "character_card_spec",
        "character_card_data",
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
        "opening_audio_url",
        "creator_id",
    ]

    for field in fields_to_compare:
        val1 = getattr(agent1, field)
        val2 = getattr(agent2, field)
        if val1 != val2:
            return True

    return False


def copy_agent_fields(source: Agent, target: Agent) -> None:
    """将源Agent的字段复制到目标Agent"""
    fields_to_copy = [
        "readable_id",
        "name",
        "gender",
        "avatar",
        "background",
        "background_images",
        "voice_id",
        "settings",
        "intro",
        "opening",
        "visibility",
        "photos",
        "category",
        "status",
        "prompt",
        "main_prompt",
        "mode_prompt",
        "character_card_spec",
        "character_card_data",
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
        "opening_audio_url",
        "creator_id",
    ]

    for field in fields_to_copy:
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

    potential_delete_ids = prod_agents.keys() - dev_agents.keys()
    to_delete_ids = set()
    skipped_delete_ids = set()

    for agent_id in potential_delete_ids:
        agent = prod_agents[agent_id]
        if agent.creator_id == user_id:
            to_delete_ids.add(agent_id)
        else:
            skipped_delete_ids.add(agent_id)
            logger.warning(
                f"⚠️  跳过删除（创建者不是运营用户）: {agent.name} "
                f"(ID: {agent_id}, 创建者: {agent.creator_id})"
            )

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
    logger.info(f"  需要删除: {len(to_delete_ids)} 个角色")
    if skipped_delete_ids:
        logger.info(
            f"  跳过删除: {len(skipped_delete_ids)} 个角色（创建者不是运营用户）"
        )
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

        if to_delete_ids:
            logger.info("")
            logger.info("删除角色列表:")
            for agent_id in to_delete_ids:
                agent = prod_agents[agent_id]
                logger.info(f"  🗑️  删除: {agent.name} (ID: {agent_id})")

        logger.info("")
        logger.info("=" * 60)
        logger.info("预览完成，未执行任何操作")
        logger.info("如需执行，请去掉 --dry-run 参数")
        logger.info("=" * 60)
        return

    logger.info("")
    logger.info("开始执行同步操作...")
    logger.info("操作顺序：1) 删除 → 2) 更新 → 3) 创建")
    logger.info("")

    created_count = 0
    updated_count = 0
    deleted_count = 0

    try:
        # 第一步：删除操作（先执行，避免 readable_id 冲突）
        if to_delete_ids:
            logger.info("第 1 步：执行删除操作...")
            for agent_id in to_delete_ids:
                result = await prod_session.execute(
                    select(Agent).where(Agent.id == agent_id)
                )
                prod_agent = result.scalar_one()

                prod_agent.deleted_at = datetime.now(UTC)
                await prod_session.flush()

                deleted_count += 1
                logger.info(f"🗑️  删除成功: {prod_agent.name} (ID: {agent_id})")
            logger.info("")

        # 第二步：更新操作
        if to_update_ids:
            logger.info("第 2 步：执行更新操作...")
            for agent_id in to_update_ids:
                source_agent = dev_agents[agent_id]
                target_agent = prod_agents[agent_id]

                result = await prod_session.execute(
                    select(Agent).where(Agent.id == agent_id)
                )
                prod_agent = result.scalar_one()

                copy_agent_fields(source_agent, prod_agent)
                await prod_session.flush()

                updated_count += 1
                logger.info(f"🔄 更新成功: {prod_agent.name} (ID: {agent_id})")
            logger.info("")

        # 第三步：创建操作（最后执行，此时已删除冲突的角色）
        if to_create_ids:
            logger.info("第 3 步：执行创建操作...")
            for agent_id in to_create_ids:
                source_agent = dev_agents[agent_id]
                dev_session.expunge(source_agent)

                new_agent = Agent(id=source_agent.id)
                copy_agent_fields(source_agent, new_agent)

                # 确保 readable_id 唯一，如果冲突则生成新的自增 ID
                new_agent.readable_id = await ensure_unique_readable_id(
                    prod_session, new_agent.readable_id
                )

                prod_session.add(new_agent)
                await prod_session.flush()

                created_count += 1
                logger.info(f"✨ 创建成功: {new_agent.name} (ID: {agent_id})")

        # 所有操作成功，提交事务
        await prod_session.commit()
        logger.info("")
        logger.info("=" * 60)
        logger.info("同步完成！")
        logger.info(f"  创建: {created_count} 个")
        logger.info(f"  更新: {updated_count} 个")
        logger.info(f"  删除: {deleted_count} 个")
        logger.info("=" * 60)

    except Exception as e:
        await prod_session.rollback()
        logger.error("")
        logger.error("=" * 60)
        logger.error("同步失败，已回滚所有操作")
        logger.error(
            f"  已完成: 创建 {created_count} 个，更新 {updated_count} 个，删除 {deleted_count} 个"
        )
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

    dev_url = create_db_url(config["dev_database"])
    prod_url = create_db_url(config["prod_database"])

    dev_engine = create_async_engine(dev_url, echo=False)
    prod_engine = create_async_engine(prod_url, echo=False)

    DevSession = sessionmaker(
        bind=dev_engine, class_=AsyncSession, expire_on_commit=False
    )
    ProdSession = sessionmaker(
        bind=prod_engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with DevSession() as dev_session, ProdSession() as prod_session:
            logger.info("数据库连接成功")

            user_config = config["operator_user"]
            user_id = user_config["id"]

            result = await dev_session.execute(select(User).where(User.id == user_id))
            dev_user = result.scalar_one_or_none()
            if not dev_user:
                logger.error(f"Dev环境中不存在运营用户: {user_id}")
                sys.exit(1)

            logger.info(f"Dev环境运营用户: {dev_user.nickname} ({user_id})")

            if not args.dry_run:
                await ensure_operator_user(prod_session, user_config)

            await sync_agents(dev_session, prod_session, user_id, args.dry_run)

    except Exception as e:
        logger.error(f"同步过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await dev_engine.dispose()
        await prod_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
