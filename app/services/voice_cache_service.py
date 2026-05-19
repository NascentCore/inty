"""
语音缓存服务
用于管理语音文件的缓存和清理
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.voice_cache import VoiceCache
from app.services.gcs_service import GCSService


class VoiceCacheService:
    """语音缓存服务"""

    def __init__(self):
        self.gcs_service = GCSService()
        self.cache_ttl_days = 30  # 缓存保留30天

    def _generate_content_hash(
        self, text: str, voice_id: str, model: str, language: str
    ) -> str:
        """生成内容哈希值"""
        content = f"{text}_{voice_id}_{model}_{language}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get_cached_voice(
        self,
        db: AsyncSession,
        text: str,
        voice_id: str,
        model: str,
        language: str,
    ) -> Optional[Tuple[str, float]]:
        """
        获取缓存的语音文件URL和时长

        Args:
            db: 数据库会话
            text: 文本内容
            voice_id: 语音ID
            model: 模型名称
            language: 语言

        Returns:
            缓存的音频URL和时长的元组，如果不存在则返回None
        """
        try:
            content_hash = self._generate_content_hash(
                text, voice_id, model, language
            )

            # 查询缓存，使用 COALESCE 将 NULL duration 转换为 0.0
            result = await db.execute(
                select(
                    VoiceCache.audio_url,
                    # 保持兼容性；coalesce 返回参数列表中第一个非 NULL 的值。
                    # TODO：清除掉 func.coalesce，填充 duration 值到数据库
                    func.coalesce(VoiceCache.duration, 0.0).label("duration"),
                ).where(
                    VoiceCache.content_hash == content_hash,
                    VoiceCache.is_active == True,
                )
            )
            cache_entry = result.one_or_none()

            if cache_entry:
                # 检查文件是否还存在
                if self.gcs_service.check_voice_file_exists(
                    cache_entry.audio_url
                ):
                    logger.debug(f"语音缓存命中: {content_hash}")

                    # 异步更新访问统计，不阻塞主流程
                    import asyncio

                    asyncio.create_task(
                        self._update_cache_hit_async(
                            content_hash, text, voice_id, model, language
                        )
                    )

                    return (cache_entry.audio_url, cache_entry.duration)
                else:
                    # 文件不存在，标记为无效（使用独立事务）
                    try:
                        await self._mark_cache_invalid_async(content_hash)
                        logger.warning(
                            f"语音缓存文件不存在，标记为无效: {cache_entry.audio_url}"
                        )
                    except Exception as e:
                        logger.error(f"标记缓存无效失败: {str(e)}")

            return None

        except Exception as e:
            logger.error(f"获取语音缓存失败: {str(e)}")
            return None

    async def save_voice_cache(
        self,
        db: Optional[AsyncSession],
        text: str,
        voice_id: str,
        model: str,
        language: str,
        audio_url: str,
        duration: float,
        file_size: int = 0,
    ) -> bool:
        """
        保存语音缓存

        Args:
            db: 数据库会话（可选，如果为空则创建新会话）
            text: 文本内容
            voice_id: 语音ID
            model: 模型名称
            language: 语言
            audio_url: 音频文件URL
            duration: 音频时长（秒）
            file_size: 文件大小

        Returns:
            是否保存成功
        """
        # 如果没有提供数据库会话，创建新的会话
        if db is None:
            from app.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as db_session:
                return await self._save_voice_cache_impl(
                    db_session,
                    text,
                    voice_id,
                    model,
                    language,
                    audio_url,
                    duration,
                    file_size,
                )
        else:
            return await self._save_voice_cache_impl(
                db,
                text,
                voice_id,
                model,
                language,
                audio_url,
                duration,
                file_size,
            )

    async def _save_voice_cache_impl(
        self,
        db: AsyncSession,
        text: str,
        voice_id: str,
        model: str,
        language: str,
        audio_url: str,
        duration: float,
        file_size: int = 0,
    ) -> bool:
        """
        实际的保存语音缓存实现
        """
        try:
            import uuid

            content_hash = self._generate_content_hash(
                text, voice_id, model, language
            )

            # 检查是否已存在
            result = await db.execute(
                select(VoiceCache).where(
                    VoiceCache.content_hash == content_hash
                )
            )
            existing_cache = result.scalar_one_or_none()

            if existing_cache:
                # 更新现有缓存
                existing_cache.audio_url = audio_url
                existing_cache.duration = duration
                existing_cache.file_size = file_size
                existing_cache.is_active = True
                existing_cache.last_accessed = datetime.now()
                logger.debug(f"更新语音缓存: {content_hash}")
            else:
                # 创建新缓存
                cache_entry = VoiceCache(
                    id=str(uuid.uuid4()),
                    content_hash=content_hash,
                    text_content=text[:1000],  # 限制文本长度
                    voice_id=voice_id,
                    model=model,
                    language=language,
                    audio_url=audio_url,
                    duration=duration,
                    file_size=file_size,
                    hit_count=0,
                )
                db.add(cache_entry)
                logger.debug(f"创建新语音缓存: {content_hash}")

            await db.commit()
            return True

        except Exception as e:
            logger.error(f"保存语音缓存失败: {str(e)}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(
                    f"保存语音缓存失败后回滚失败: voice_id={voice_id}, model={model}, language={language}, "
                    f"original_error={str(e)}, rollback_error={str(rollback_error)}"
                )
            return False

    async def update_access_stats(
        self,
        db: Optional[AsyncSession],
        text: str,
        voice_id: str,
        model: str,
        language: str,
    ) -> None:
        """
        异步更新缓存访问统计，不阻塞主流程
        """
        # 如果没有提供数据库会话，创建新的会话
        if db is None:
            from app.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as db_session:
                await self._update_access_stats_impl(
                    db_session, text, voice_id, model, language
                )
        else:
            await self._update_access_stats_impl(
                db, text, voice_id, model, language
            )

    async def _update_access_stats_impl(
        self,
        db: AsyncSession,
        text: str,
        voice_id: str,
        model: str,
        language: str,
    ) -> None:
        """实际的更新访问统计实现"""
        try:
            content_hash = self._generate_content_hash(
                text, voice_id, model, language
            )

            # 更新访问统计
            stmt = (
                update(VoiceCache)
                .where(VoiceCache.content_hash == content_hash)
                .values(
                    last_accessed=datetime.now(),
                    hit_count=VoiceCache.hit_count + 1,
                )
            )

            await db.execute(stmt)
            await db.commit()

            logger.debug(f"更新缓存访问统计: {content_hash}")

        except Exception as e:
            logger.error(f"更新缓存访问统计失败: {str(e)}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(
                    f"更新缓存访问统计失败后回滚失败: voice_id={voice_id}, model={model}, language={language}, "
                    f"original_error={str(e)}, rollback_error={str(rollback_error)}"
                )

    async def _update_cache_hit_async(
        self,
        content_hash: str,
        text: str,
        voice_id: str,
        model: str,
        language: str,
    ) -> None:
        """异步更新缓存命中统计，使用独立的数据库会话"""
        try:
            from app.db.session import AsyncSessionLocal

            # 创建独立的数据库会话
            async with AsyncSessionLocal() as db_session:
                try:
                    # 更新访问统计
                    stmt = (
                        update(VoiceCache)
                        .where(VoiceCache.content_hash == content_hash)
                        .values(
                            last_accessed=datetime.now(),
                            hit_count=VoiceCache.hit_count + 1,
                        )
                    )

                    await db_session.execute(stmt)
                    await db_session.commit()

                    logger.debug(f"异步更新缓存访问统计: {content_hash}")

                except Exception as e:
                    logger.error(f"异步更新缓存访问统计失败: {str(e)}")
                    await db_session.rollback()

        except Exception as e:
            logger.error(f"创建异步数据库会话失败: {str(e)}")

    async def _mark_cache_invalid_async(self, content_hash: str) -> None:
        """异步标记缓存为无效，使用独立的数据库会话"""
        try:
            from app.db.session import AsyncSessionLocal

            # 创建独立的数据库会话
            async with AsyncSessionLocal() as db_session:
                try:
                    # 标记为无效
                    stmt = (
                        update(VoiceCache)
                        .where(VoiceCache.content_hash == content_hash)
                        .values(is_active=False)
                    )

                    await db_session.execute(stmt)
                    await db_session.commit()

                    logger.debug(f"异步标记缓存无效: {content_hash}")

                except Exception as e:
                    logger.error(f"异步标记缓存无效失败: {str(e)}")
                    await db_session.rollback()

        except Exception as e:
            logger.error(f"创建异步数据库会话失败: {str(e)}")

    async def get_cache_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Args:
            db: 数据库会话

        Returns:
            缓存统计信息
        """
        try:
            # 总缓存数
            total_result = await db.execute(
                select(func.count(VoiceCache.id)).where(
                    VoiceCache.is_active == True
                )
            )
            total_count = total_result.scalar()

            # 今日命中次数
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_hits_result = await db.execute(
                select(func.sum(VoiceCache.hit_count)).where(
                    VoiceCache.is_active == True,
                    VoiceCache.last_accessed >= today_start,
                )
            )
            today_hits = today_hits_result.scalar() or 0

            # 总文件大小
            size_result = await db.execute(
                select(func.sum(VoiceCache.file_size)).where(
                    VoiceCache.is_active == True
                )
            )
            total_size = size_result.scalar() or 0

            # 热门语音
            popular_result = await db.execute(
                select(VoiceCache.text_content, VoiceCache.hit_count)
                .where(VoiceCache.is_active == True)
                .order_by(VoiceCache.hit_count.desc())
                .limit(10)
            )
            popular_voices = [
                {"text": row[0], "hits": row[1]}
                for row in popular_result.fetchall()
            ]

            return {
                "total_cached": total_count,
                "today_hits": today_hits,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "popular_voices": popular_voices,
            }

        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return {
                "total_cached": 0,
                "today_hits": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "popular_voices": [],
            }

    async def cleanup_old_cache(self, db: AsyncSession) -> int:
        """
        清理过期的缓存

        Args:
            db: 数据库会话

        Returns:
            清理的缓存数量
        """
        try:
            # 计算过期时间
            expire_time = datetime.now() - timedelta(days=self.cache_ttl_days)

            # 查询要删除的缓存
            result = await db.execute(
                select(VoiceCache).where(
                    VoiceCache.last_accessed < expire_time,
                    VoiceCache.is_active == True,
                )
            )
            old_caches = result.scalars().all()

            deleted_count = 0
            for cache in old_caches:
                try:
                    # 删除GCS文件
                    await self.gcs_service.delete_voice_file(cache.audio_url)

                    # 标记为无效
                    cache.is_active = False
                    deleted_count += 1

                except Exception as e:
                    logger.warning(
                        f"删除缓存文件失败: {cache.audio_url}, 错误: {str(e)}"
                    )
                    continue

            await db.commit()

            logger.info(f"清理过期缓存完成，删除 {deleted_count} 个文件")
            return deleted_count

        except Exception as e:
            logger.error(f"清理过期缓存失败: {str(e)}")
            await db.rollback()
            return 0

    async def cleanup_invalid_cache(self, db: AsyncSession) -> int:
        """
        清理无效的缓存（文件不存在的缓存）

        Args:
            db: 数据库会话

        Returns:
            清理的缓存数量
        """
        try:
            # 查询活跃的缓存
            result = await db.execute(
                select(VoiceCache).where(VoiceCache.is_active == True)
            )
            active_caches = result.scalars().all()

            invalid_count = 0
            for cache in active_caches:
                try:
                    # 检查文件是否存在
                    if not self.gcs_service.check_voice_file_exists(
                        cache.audio_url
                    ):
                        cache.is_active = False
                        invalid_count += 1
                        logger.debug(f"标记无效缓存: {cache.audio_url}")

                except Exception as e:
                    logger.warning(
                        f"检查缓存文件失败: {cache.audio_url}, 错误: {str(e)}"
                    )
                    continue

            await db.commit()

            logger.info(f"清理无效缓存完成，标记 {invalid_count} 个为无效")
            return invalid_count

        except Exception as e:
            logger.error(f"清理无效缓存失败: {str(e)}")
            await db.rollback()
            return 0


# 创建全局实例
voice_cache_service = VoiceCacheService()
