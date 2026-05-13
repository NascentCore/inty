"""
CREATED_BY_AGENT

数据迁移脚本：将 chat_history 中的生成图片迁移到新的 GCS 路径结构并同步到 resources 表

迁移内容：
1. 将 GCS 路径从 chat_images/{timestamp}_{uuid}.jpg 改为 chat_images/{agent_id}/{timestamp}_{uuid}.jpg
2. 在 resources 表中创建对应记录（包含 generation_prompt）
3. 更新 chat_history.meta_data 中的 image_url 为新路径

使用方法：
    # 预览模式（不做任何修改）
    python tools/scripts/migrate_generated_images.py --dry-run

    # 执行迁移
    python tools/scripts/migrate_generated_images.py

    # 跳过 GCS 复制（仅更新数据库）
    python tools/scripts/migrate_generated_images.py --skip-gcs-copy

    # 指定批次大小
    python tools/scripts/migrate_generated_images.py --batch-size 50
"""

import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from typing import Optional

import cyclopts
from loguru import logger
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.external_services.gcs import (
    GCS_GS_PREFIX,
    check_gcs_file_exists,
    copy_gcs_file,
    get_bucket_and_path_from_gcs_url,
)
from app.models.chat_history import ChatHistory
from app.models.resource import ImageResourceMetadata, Resource, ResourceType
from app.schemas.resource import ResourceCreate
from app.utils.image import ImageFormat, ImageSize


@dataclass
class MigrationStats:
    """迁移统计"""

    total: int = 0
    migrated: int = 0
    skipped_already_migrated: int = 0
    skipped_no_chat: int = 0
    skipped_file_not_found: int = 0
    skipped_resource_exists: int = 0
    error: int = 0


def is_already_migrated(image_url: str) -> bool:
    """
    检查图片是否已迁移到新路径结构

    新路径格式: gs://bucket/chat_images/{agent_id}/{timestamp}_{uuid}.jpg
    旧路径格式: gs://bucket/chat_images/{timestamp}_{uuid}.jpg
    """
    if not image_url:
        return False

    try:
        _, path = get_bucket_and_path_from_gcs_url(image_url)
        if not path:
            return False

        # 检查路径层级
        # 旧格式: chat_images/20241201_123456_abc123.jpg (2 层)
        # 新格式: chat_images/agent_id/20241201_123456_abc123.jpg (3 层)
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "chat_images":
            # 新格式有 3 层或更多
            return True
        return False
    except Exception:
        return False


def build_new_gcs_path(old_url: str, agent_id: str) -> str:
    """
    根据旧路径和 agent_id 构建新的 GCS 路径

    Args:
        old_url: 旧的 GCS URL，如 gs://bucket/chat_images/20241201_123456_abc.jpg
        agent_id: Agent ID

    Returns:
        新的 GCS 路径（不含 bucket），如 chat_images/agent_id/20241201_123456_abc.jpg
    """
    _, path = get_bucket_and_path_from_gcs_url(old_url)
    if not path:
        raise ValueError(f"无法解析 GCS URL: {old_url}")

    # 提取文件名
    filename = path.split("/")[-1]

    # 构建新路径
    return f"chat_images/{agent_id}/{filename}"


# 全局缓存: session_id -> chat_info
_session_id_to_chat_cache: dict = {}


def generate_session_id(chat_id: str) -> str:
    """
    根据 chat_id 生成 session_id

    与 chat_service.py 中的 generate_session_id 保持一致
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


async def load_chat_session_mapping(db: AsyncSession) -> dict:
    """
    加载所有 chats 并构建 session_id -> chat_info 的映射

    Returns:
        session_id -> {"chat_id": ..., "user_id": ..., "agent_id": ...}
    """
    global _session_id_to_chat_cache

    if _session_id_to_chat_cache:
        return _session_id_to_chat_cache

    logger.info("加载 chats 表构建 session_id 映射...")

    query = text("SELECT id, user_id, agent_id FROM chats")
    result = await db.execute(query)
    rows = result.fetchall()

    for row in rows:
        chat_id, user_id, agent_id = row
        session_id = generate_session_id(chat_id)
        _session_id_to_chat_cache[session_id] = {
            "chat_id": chat_id,
            "user_id": user_id,
            "agent_id": agent_id,
        }

    logger.info(f"已加载 {len(_session_id_to_chat_cache)} 条 chat 记录")
    return _session_id_to_chat_cache


async def get_chat_info_by_session_id(
    db: AsyncSession, session_id: str
) -> Optional[dict]:
    """
    根据 session_id 查询对应的 chat 信息

    session_id = uuid5(uuid.NAMESPACE_DNS, chat_id)
    使用预加载的缓存进行查找
    """
    cache = await load_chat_session_mapping(db)
    return cache.get(session_id)


async def get_generated_images_to_migrate(
    db: AsyncSession, batch_size: int, offset: int
) -> list:
    """
    查询需要迁移的生成图片记录

    Returns:
        包含 chat_history 记录信息的列表
    """
    query = text("""
        SELECT 
            ch.id,
            ch.session_id::text,
            ch.meta_data,
            ch.created_at
        FROM chat_history ch
        WHERE ch.meta_data->'generated_image' IS NOT NULL
          AND ch.meta_data->'generated_image'->>'image_url' IS NOT NULL
          AND ch.deleted_at IS NULL
        ORDER BY ch.id
        LIMIT :limit OFFSET :offset
        """)

    result = await db.execute(query, {"limit": batch_size, "offset": offset})
    return result.fetchall()


async def create_resource_record(
    db: AsyncSession,
    gcs_uri: str,
    user_id: str,
    agent_id: str,
    prompt: Optional[str],
    width: Optional[int],
    height: Optional[int],
    image_format: str = "jpeg",
    dry_run: bool = False,
) -> bool:
    """
    在 resources 表中创建图片资源记录

    Returns:
        True 如果创建成功，False 如果记录已存在
    """
    # 检查记录是否已存在
    existing = await db.execute(select(Resource).where(Resource.url == gcs_uri))
    if existing.scalar_one_or_none():
        logger.debug(f"资源记录已存在: {gcs_uri}")
        return False

    if dry_run:
        logger.info(f"DRY-RUN: 将创建资源记录 {gcs_uri}")
        return True

    # 构建 ImageResourceMetadata
    size = ImageSize(width=width or 0, height=height or 0)

    image_metadata = ImageResourceMetadata(
        creator=user_id,
        size=size,
        content_type=f"image/{image_format}",
        byte_size=0,  # 历史数据无法获取实际大小
        compressed=False,
        cropped=False,
        gcs_url=gcs_uri,
        generation_prompt=prompt,
    )

    # 创建资源记录
    resource = Resource(
        url=gcs_uri,
        type=ResourceType.IMAGE,
        user_id=user_id,
        agent_id=agent_id,
        resource_metadata=image_metadata.model_dump(),
    )

    db.add(resource)
    return True


async def update_chat_history_metadata(
    db: AsyncSession,
    record_id: int,
    new_image_url: str,
    original_meta_data: dict,
    dry_run: bool = False,
) -> bool:
    """
    更新 chat_history 的 meta_data 中的 image_url

    Returns:
        True 如果更新成功
    """
    if dry_run:
        logger.info(f"DRY-RUN: 将更新记录 {record_id} 的 image_url 为 {new_image_url}")
        return True

    # 更新 meta_data 中的 image_url
    updated_meta = dict(original_meta_data)
    if "generated_image" in updated_meta:
        updated_meta["generated_image"]["image_url"] = new_image_url
        updated_meta["generated_image"]["migrated"] = True

    stmt = (
        update(ChatHistory)
        .where(ChatHistory.id == record_id)
        .values(meta_data=updated_meta)
    )

    await db.execute(stmt)
    return True


async def migrate_single_record(
    db: AsyncSession,
    record: tuple,
    bucket_name: str,
    dry_run: bool = False,
    skip_gcs_copy: bool = False,
) -> tuple[bool, str]:
    """
    迁移单条记录

    Returns:
        (success, reason) 元组
    """
    record_id, session_id, meta_data, created_at = record

    # 解析 meta_data
    if isinstance(meta_data, str):
        meta_data = json.loads(meta_data)

    generated_image = meta_data.get("generated_image", {})
    old_image_url = generated_image.get("image_url")

    if not old_image_url:
        return False, "no_image_url"

    # 检查是否已迁移
    if is_already_migrated(old_image_url):
        # 已迁移的记录可能只需要创建 resources 记录
        logger.debug(f"记录 {record_id} 的图片已在新路径结构中")

        # 获取 chat 信息
        chat_info = await get_chat_info_by_session_id(db, session_id)
        if not chat_info:
            return False, "no_chat"

        # 检查 resources 表是否已有记录
        existing = await db.execute(
            select(Resource).where(Resource.url == old_image_url)
        )
        if existing.scalar_one_or_none():
            return False, "already_migrated"

        # 创建 resources 记录
        await create_resource_record(
            db=db,
            gcs_uri=old_image_url,
            user_id=chat_info["user_id"],
            agent_id=chat_info["agent_id"],
            prompt=generated_image.get("prompt"),
            width=generated_image.get("width"),
            height=generated_image.get("height"),
            image_format=generated_image.get("format", "jpeg"),
            dry_run=dry_run,
        )

        return True, "created_resource_only"

    # 获取 chat 信息
    chat_info = await get_chat_info_by_session_id(db, session_id)
    if not chat_info:
        logger.warning(f"记录 {record_id} 找不到对应的 chat，session_id={session_id}")
        return False, "no_chat"

    agent_id = chat_info["agent_id"]
    user_id = chat_info["user_id"]

    # 构建新路径
    new_gcs_path = build_new_gcs_path(old_image_url, agent_id)
    new_gcs_uri = f"{GCS_GS_PREFIX}{bucket_name}/{new_gcs_path}"

    # 复制 GCS 文件
    if not skip_gcs_copy:
        # 检查源文件是否存在
        _, old_path = get_bucket_and_path_from_gcs_url(old_image_url)
        if not check_gcs_file_exists(bucket_name, old_path):
            logger.warning(f"源文件不存在: {old_image_url}")
            return False, "file_not_found"

        # 检查目标文件是否已存在
        if check_gcs_file_exists(bucket_name, new_gcs_path):
            logger.debug(f"目标文件已存在: {new_gcs_uri}")
        else:
            if dry_run:
                logger.info(f"DRY-RUN: 将复制 {old_image_url} -> {new_gcs_uri}")
            else:
                try:
                    copy_gcs_file(old_image_url, new_gcs_path, bucket_name)
                    logger.debug(f"已复制文件: {old_image_url} -> {new_gcs_uri}")
                except Exception as e:
                    logger.error(f"复制文件失败: {e}")
                    return False, "copy_failed"

    # 创建 resources 记录
    created = await create_resource_record(
        db=db,
        gcs_uri=new_gcs_uri,
        user_id=user_id,
        agent_id=agent_id,
        prompt=generated_image.get("prompt"),
        width=generated_image.get("width"),
        height=generated_image.get("height"),
        image_format=generated_image.get("format", "jpeg"),
        dry_run=dry_run,
    )

    if not created and not dry_run:
        return False, "resource_exists"

    # 更新 chat_history 的 meta_data
    await update_chat_history_metadata(
        db=db,
        record_id=record_id,
        new_image_url=new_gcs_uri,
        original_meta_data=meta_data,
        dry_run=dry_run,
    )

    return True, "migrated"


async def run_migration(
    dry_run: bool = False,
    skip_gcs_copy: bool = False,
    batch_size: int = 100,
) -> MigrationStats:
    """
    执行迁移

    Args:
        dry_run: 预览模式，不做任何修改
        skip_gcs_copy: 跳过 GCS 复制
        batch_size: 每批处理的记录数

    Returns:
        迁移统计信息
    """
    stats = MigrationStats()
    bucket_name = global_config_loaded_from_config_yaml.gcs.bucket

    # 清空缓存，确保使用最新数据
    global _session_id_to_chat_cache
    _session_id_to_chat_cache = {}

    logger.info(f"开始迁移，bucket: {bucket_name}")
    if dry_run:
        logger.info("DRY-RUN 模式：不会做任何实际修改")
    if skip_gcs_copy:
        logger.info("跳过 GCS 复制：仅更新数据库记录")

    offset = 0

    while True:
        # 每批使用新的数据库连接，避免事务污染
        async with AsyncSessionLocal() as db:
            records = await get_generated_images_to_migrate(db, batch_size, offset)
            if not records:
                break

            logger.info(
                f"处理第 {offset // batch_size + 1} 批，共 {len(records)} 条记录"
            )

        # 逐条处理，每条记录使用独立的事务
        for record in records:
            stats.total += 1
            record_id = record[0]

            async with AsyncSessionLocal() as db:
                try:
                    success, reason = await migrate_single_record(
                        db=db,
                        record=record,
                        bucket_name=bucket_name,
                        dry_run=dry_run,
                        skip_gcs_copy=skip_gcs_copy,
                    )

                    if success:
                        if not dry_run:
                            await db.commit()
                        stats.migrated += 1
                        logger.debug(f"记录 {record_id} 迁移成功: {reason}")
                    else:
                        if reason == "already_migrated":
                            stats.skipped_already_migrated += 1
                        elif reason == "no_chat":
                            stats.skipped_no_chat += 1
                        elif reason == "file_not_found":
                            stats.skipped_file_not_found += 1
                        elif reason == "resource_exists":
                            stats.skipped_resource_exists += 1
                        else:
                            stats.error += 1
                        logger.debug(f"记录 {record_id} 跳过: {reason}")

                except Exception as e:
                    stats.error += 1
                    logger.error(f"处理记录 {record_id} 时出错: {e}")
                    await db.rollback()
                    import traceback

                    traceback.print_exc()

        offset += batch_size

    return stats


async def main(
    dry_run: bool = False,
    skip_gcs_copy: bool = False,
    batch_size: int = 100,
):
    """
    生成图片数据迁移脚本

    将 chat_history 中的生成图片迁移到新的 GCS 路径结构并同步到 resources 表。

    Parameters
    ----------
    dry_run
        预览模式：显示将要执行的操作但不实际修改
    skip_gcs_copy
        跳过 GCS 文件复制（仅更新数据库）
    batch_size
        每批处理的记录数

    Examples
    --------
    # 预览模式
    python tools/scripts/migrate_generated_images.py --dry-run

    # 执行迁移
    python tools/scripts/migrate_generated_images.py

    # 跳过 GCS 复制
    python tools/scripts/migrate_generated_images.py --skip-gcs-copy

    # 指定批次大小
    python tools/scripts/migrate_generated_images.py --batch-size 50
    """
    logger.info("=" * 60)
    logger.info("生成图片数据迁移脚本")
    logger.info("=" * 60)

    # 确认操作
    if not dry_run:
        print("\n⚠️  警告：此操作将迁移所有生成图片数据！")
        print("将要执行的操作：")
        print("  1. 复制 GCS 文件到新路径结构 chat_images/{agent_id}/...")
        print("  2. 在 resources 表创建图片资源记录")
        print("  3. 更新 chat_history.meta_data 中的 image_url")
        print("\n建议先使用 --dry-run 预览")

        confirmation = input("\n请输入 'MIGRATE' 确认执行迁移: ")
        if confirmation != "MIGRATE":
            logger.info("操作已取消")
            return

    stats = await run_migration(
        dry_run=dry_run,
        skip_gcs_copy=skip_gcs_copy,
        batch_size=batch_size,
    )

    logger.info("=" * 60)
    logger.info("迁移完成！统计信息：")
    logger.info(f"  总记录数: {stats.total}")
    logger.info(f"  成功迁移: {stats.migrated}")
    logger.info(f"  跳过（已迁移）: {stats.skipped_already_migrated}")
    logger.info(f"  跳过（无对应 chat）: {stats.skipped_no_chat}")
    logger.info(f"  跳过（文件不存在）: {stats.skipped_file_not_found}")
    logger.info(f"  跳过（资源已存在）: {stats.skipped_resource_exists}")
    logger.info(f"  错误: {stats.error}")
    logger.info("=" * 60)

    if dry_run:
        logger.info("DRY-RUN 完成，未做任何实际修改")
    else:
        logger.success("✅ 迁移成功完成")


if __name__ == "__main__":
    cyclopts.run(main)
