#!/usr/bin/env python3
# CREATED_BY_AGENT
"""
同步 dev 环境的角色主题专区数据到 prod 环境

从 dev 环境中同步所有角色主题专区及其关联的角色到 prod 环境。
支持创建、更新和删除操作。
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from app.models.agent import Agent
from app.models.character_theme import (
    CharacterTheme,
    CharacterThemeAgent,
    CharacterThemeVisibility,
)


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

    connect_args = {}
    if "command_timeout" in db_config:
        connect_args["command_timeout"] = db_config["command_timeout"]
    if "connect_timeout" in db_config:
        connect_args["timeout"] = db_config["connect_timeout"]

    connect_args["server_settings"] = {
        "application_name": "sync_character_themes_dev_to_prod",
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
        return False

    logger.info(f"✓ Alembic 版本一致: {dev_version}")
    return True


async def fetch_themes(session: AsyncSession) -> list[CharacterTheme]:
    """获取所有角色主题专区（包含关联的角色）"""
    stmt = select(CharacterTheme).options(selectinload(CharacterTheme.agents))
    result = await session.execute(stmt)
    themes = result.scalars().all()
    return list(themes)


async def fetch_prod_agent_ids(session: AsyncSession) -> set[str]:
    """获取 prod 环境中所有 agent 的 ID 集合"""
    stmt = select(Agent.id).where(Agent.deleted_at.is_(None))
    result = await session.execute(stmt)
    return {row[0] for row in result.fetchall()}


FIELDS_TO_SYNC = [
    "name",
    "description",
    "background_image_url",
    "visibility",
]


def compare_themes(theme1: CharacterTheme, theme2: CharacterTheme) -> bool:
    """
    比较两个 CharacterTheme 对象是否相同
    返回 True 表示不同需要更新，False 表示相同不需要更新
    """
    for field in FIELDS_TO_SYNC:
        val1 = getattr(theme1, field)
        val2 = getattr(theme2, field)
        if val1 != val2:
            return True
    return False


def compare_theme_agents(
    agents1: list[CharacterThemeAgent], agents2: list[CharacterThemeAgent]
) -> bool:
    """
    比较两个主题的角色关联是否相同
    返回 True 表示不同需要更新，False 表示相同不需要更新
    """
    if len(agents1) != len(agents2):
        return True

    sorted1 = sorted(agents1, key=lambda x: x.order_index)
    sorted2 = sorted(agents2, key=lambda x: x.order_index)

    for a1, a2 in zip(sorted1, sorted2):
        if a1.agent_id != a2.agent_id or a1.order_index != a2.order_index:
            return True

    return False


def copy_theme_fields(source: CharacterTheme, target: CharacterTheme) -> None:
    """将源 CharacterTheme 的字段复制到目标 CharacterTheme"""
    for field in FIELDS_TO_SYNC:
        value = getattr(source, field)
        setattr(target, field, value)


async def ensure_visibility_uniqueness(
    session: AsyncSession,
    visibility: CharacterThemeVisibility,
    exclude_theme_id: Optional[str] = None,
) -> None:
    """
    确保可见性的唯一性约束
    当设置专区为 PRIMARY 或 SECONDARY 时，将其他具有相同可见性的专区改为 HIDDEN
    """
    if visibility == CharacterThemeVisibility.HIDDEN:
        return

    stmt = select(CharacterTheme).where(CharacterTheme.visibility == visibility)
    if exclude_theme_id:
        stmt = stmt.where(CharacterTheme.id != exclude_theme_id)

    result = await session.execute(stmt)
    conflicting_themes = result.scalars().all()

    for theme in conflicting_themes:
        theme.visibility = CharacterThemeVisibility.HIDDEN
        logger.info(
            f"将专区 {theme.id} ({theme.name}) 的可见性从 {visibility} 改为 HIDDEN"
        )


async def sync_theme_agents(
    prod_session: AsyncSession,
    theme_id: str,
    dev_agents: list[CharacterThemeAgent],
    prod_agent_ids: set[str],
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    同步主题的角色关联

    返回: (成功同步数, 跳过数)
    """
    if dry_run:
        synced = 0
        skipped = 0
        for dev_agent in dev_agents:
            if dev_agent.agent_id not in prod_agent_ids:
                skipped += 1
            else:
                synced += 1
        return synced, skipped

    # 删除 prod 中该主题的所有关联
    await prod_session.execute(
        delete(CharacterThemeAgent).where(
            CharacterThemeAgent.theme_id == theme_id
        )
    )

    synced = 0
    skipped = 0

    for dev_agent in dev_agents:
        if dev_agent.agent_id not in prod_agent_ids:
            logger.warning(
                f"  ⚠️  跳过角色关联: agent_id={dev_agent.agent_id} 在 prod 中不存在"
            )
            skipped += 1
            continue

        new_agent_rel = CharacterThemeAgent(
            theme_id=theme_id,
            agent_id=dev_agent.agent_id,
            order_index=dev_agent.order_index,
        )
        prod_session.add(new_agent_rel)
        synced += 1

    return synced, skipped


async def sync_themes(
    dev_session: AsyncSession,
    prod_session: AsyncSession,
    dry_run: bool = False,
) -> None:
    """同步角色主题专区数据"""
    logger.info("=" * 60)
    logger.info("开始同步角色主题专区数据")
    logger.info(f"模式: {'预览模式 (dry-run)' if dry_run else '执行模式'}")
    logger.info("=" * 60)

    dev_themes_list = await fetch_themes(dev_session)
    logger.info(f"Dev 环境找到 {len(dev_themes_list)} 个主题专区")

    prod_themes_list = await fetch_themes(prod_session)
    logger.info(f"Prod 环境找到 {len(prod_themes_list)} 个主题专区")

    prod_agent_ids = await fetch_prod_agent_ids(prod_session)
    logger.info(f"Prod 环境找到 {len(prod_agent_ids)} 个有效角色")

    dev_themes = {theme.id: theme for theme in dev_themes_list}
    prod_themes = {theme.id: theme for theme in prod_themes_list}

    to_delete_ids = prod_themes.keys() - dev_themes.keys()
    to_create_ids = dev_themes.keys() - prod_themes.keys()
    to_check_update_ids = dev_themes.keys() & prod_themes.keys()

    to_update_ids = []
    for theme_id in to_check_update_ids:
        dev_theme = dev_themes[theme_id]
        prod_theme = prod_themes[theme_id]
        fields_diff = compare_themes(dev_theme, prod_theme)
        agents_diff = compare_theme_agents(
            list(dev_theme.agents), list(prod_theme.agents)
        )
        if fields_diff or agents_diff:
            to_update_ids.append(theme_id)

    logger.info("")
    logger.info("同步计划:")
    logger.info(f"  需要删除: {len(to_delete_ids)} 个主题专区")
    logger.info(f"  需要创建: {len(to_create_ids)} 个主题专区")
    logger.info(f"  需要更新: {len(to_update_ids)} 个主题专区")
    logger.info(
        f"  无需变更: {len(to_check_update_ids) - len(to_update_ids)} 个主题专区"
    )

    if dry_run:
        logger.info("")
        logger.info("【预览模式】以下是详细操作列表:")
        logger.info("")

        if to_delete_ids:
            logger.info("删除主题专区列表:")
            for theme_id in to_delete_ids:
                theme = prod_themes[theme_id]
                logger.info(f"  🗑️  删除: {theme.name} (ID: {theme_id})")

        if to_create_ids:
            logger.info("")
            logger.info("创建主题专区列表:")
            for theme_id in to_create_ids:
                theme = dev_themes[theme_id]
                synced, skipped = await sync_theme_agents(
                    prod_session,
                    theme_id,
                    list(theme.agents),
                    prod_agent_ids,
                    dry_run=True,
                )
                skip_note = (
                    f" [将跳过 {skipped} 个不存在的角色关联]" if skipped else ""
                )
                logger.info(
                    f"  ✨ 创建: {theme.name} (ID: {theme_id}, "
                    f"角色数: {synced}{skip_note})"
                )

        if to_update_ids:
            logger.info("")
            logger.info("更新主题专区列表:")
            for theme_id in to_update_ids:
                theme = dev_themes[theme_id]
                synced, skipped = await sync_theme_agents(
                    prod_session,
                    theme_id,
                    list(theme.agents),
                    prod_agent_ids,
                    dry_run=True,
                )
                skip_note = (
                    f" [将跳过 {skipped} 个不存在的角色关联]" if skipped else ""
                )
                logger.info(
                    f"  🔄 更新: {theme.name} (ID: {theme_id}, "
                    f"角色数: {synced}{skip_note})"
                )

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

    deleted_count = 0
    updated_count = 0
    created_count = 0

    try:
        # 第一步：删除操作
        if to_delete_ids:
            logger.info("第 1 步：执行删除操作...")
            for theme_id in to_delete_ids:
                theme = prod_themes[theme_id]

                # 删除关联记录（由于外键 CASCADE，删除主题时会自动删除关联）
                result = await prod_session.execute(
                    select(CharacterTheme).where(CharacterTheme.id == theme_id)
                )
                prod_theme = result.scalar_one()
                await prod_session.delete(prod_theme)
                await prod_session.flush()

                deleted_count += 1
                logger.info(f"🗑️  删除成功: {theme.name} (ID: {theme_id})")
            logger.info("")

        # 第二步：更新操作
        if to_update_ids:
            logger.info("第 2 步：执行更新操作...")
            for theme_id in to_update_ids:
                source_theme = dev_themes[theme_id]

                result = await prod_session.execute(
                    select(CharacterTheme).where(CharacterTheme.id == theme_id)
                )
                prod_theme = result.scalar_one()

                # 处理可见性唯一性约束
                if source_theme.visibility != CharacterThemeVisibility.HIDDEN:
                    await ensure_visibility_uniqueness(
                        prod_session,
                        source_theme.visibility,
                        exclude_theme_id=theme_id,
                    )

                copy_theme_fields(source_theme, prod_theme)
                await prod_session.flush()

                # 同步角色关联
                synced, skipped = await sync_theme_agents(
                    prod_session,
                    theme_id,
                    list(source_theme.agents),
                    prod_agent_ids,
                )

                updated_count += 1
                skip_note = f" (跳过 {skipped} 个角色)" if skipped else ""
                logger.info(
                    f"🔄 更新成功: {prod_theme.name} (ID: {theme_id}, "
                    f"角色数: {synced}{skip_note})"
                )
            logger.info("")

        # 第三步：创建操作
        if to_create_ids:
            logger.info("第 3 步：执行创建操作...")
            for theme_id in to_create_ids:
                source_theme = dev_themes[theme_id]
                dev_session.expunge(source_theme)

                # 处理可见性唯一性约束
                if source_theme.visibility != CharacterThemeVisibility.HIDDEN:
                    await ensure_visibility_uniqueness(
                        prod_session, source_theme.visibility
                    )

                new_theme = CharacterTheme(
                    id=source_theme.id,
                    name=source_theme.name,
                    description=source_theme.description,
                    background_image_url=source_theme.background_image_url,
                    visibility=source_theme.visibility,
                )
                prod_session.add(new_theme)
                await prod_session.flush()

                # 同步角色关联
                synced, skipped = await sync_theme_agents(
                    prod_session,
                    theme_id,
                    list(source_theme.agents),
                    prod_agent_ids,
                )

                created_count += 1
                skip_note = f" (跳过 {skipped} 个角色)" if skipped else ""
                logger.info(
                    f"✨ 创建成功: {new_theme.name} (ID: {theme_id}, "
                    f"角色数: {synced}{skip_note})"
                )

        # 所有操作成功，提交事务
        await prod_session.commit()
        logger.info("")
        logger.info("=" * 60)
        logger.info("同步完成！")
        logger.info(f"  删除: {deleted_count} 个")
        logger.info(f"  更新: {updated_count} 个")
        logger.info(f"  创建: {created_count} 个")
        logger.info("=" * 60)

    except Exception as e:
        await prod_session.rollback()
        logger.error("")
        logger.error("=" * 60)
        logger.error("同步失败，已回滚所有操作")
        logger.error(
            f"  已完成: 删除 {deleted_count} 个，更新 {updated_count} 个，"
            f"创建 {created_count} 个"
        )
        logger.error(f"  错误: {e}")
        logger.error("=" * 60)
        raise


async def main():
    parser = argparse.ArgumentParser(
        description="同步 dev 环境主题专区到 prod 环境"
    )
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
        f"正在连接 Dev 数据库: "
        f"{dev_db_config['host']}:{dev_db_config['port']}/{dev_db_config['db']}"
    )
    dev_engine = create_async_engine(dev_url, echo=False, **dev_engine_kwargs)

    logger.info(
        f"正在连接 Prod 数据库: "
        f"{prod_db_config['host']}:{prod_db_config['port']}/{prod_db_config['db']}"
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

            await sync_themes(dev_session, prod_session, args.dry_run)

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
