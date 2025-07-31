"""
语音文件清理服务
定期清理过期的语音文件和缓存
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict

from loguru import logger

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.voice_cache_service import voice_cache_service


class VoiceCleanupService:
    """语音文件清理服务"""

    def __init__(self):
        self.cleanup_interval = 3600  # 1小时执行一次清理
        self.running = False

    async def start_cleanup_scheduler(self):
        """启动清理调度器"""
        self.running = True
        logger.info("语音文件清理服务已启动")

        while self.running:
            try:
                await self.run_cleanup()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"清理任务执行失败: {str(e)}")
                await asyncio.sleep(60)  # 出错后1分钟再试

    async def stop_cleanup_scheduler(self):
        """停止清理调度器"""
        self.running = False
        logger.info("语音文件清理服务已停止")

    async def run_cleanup(self) -> Dict[str, Any]:
        """
        执行清理任务

        Returns:
            清理结果统计
        """
        logger.info("开始执行语音文件清理任务")

        async with AsyncSessionLocal() as db:
            try:
                # 清理过期缓存
                expired_count = await voice_cache_service.cleanup_old_cache(db)

                # 清理无效缓存
                invalid_count = await voice_cache_service.cleanup_invalid_cache(db)

                # 获取清理后的统计信息
                stats = await voice_cache_service.get_cache_stats(db)

                result = {
                    "timestamp": datetime.now().isoformat(),
                    "cleanup_results": {
                        "expired_removed": expired_count,
                        "invalid_removed": invalid_count,
                        "total_removed": expired_count + invalid_count,
                    },
                    "current_stats": stats,
                }

                logger.info(
                    f"语音文件清理完成: 删除过期文件 {expired_count} 个，无效文件 {invalid_count} 个"
                )
                return result

            except Exception as e:
                logger.error(f"清理任务执行失败: {str(e)}")
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "cleanup_results": {
                        "expired_removed": 0,
                        "invalid_removed": 0,
                        "total_removed": 0,
                    },
                }

    async def manual_cleanup(self, cleanup_type: str = "all") -> Dict[str, Any]:
        """
        手动执行清理任务

        Args:
            cleanup_type: 清理类型 ("expired", "invalid", "all")

        Returns:
            清理结果统计
        """
        logger.info(f"开始手动清理任务: {cleanup_type}")

        async with AsyncSessionLocal() as db:
            try:
                expired_count = 0
                invalid_count = 0

                if cleanup_type in ["expired", "all"]:
                    expired_count = await voice_cache_service.cleanup_old_cache(db)

                if cleanup_type in ["invalid", "all"]:
                    invalid_count = await voice_cache_service.cleanup_invalid_cache(db)

                # 获取清理后的统计信息
                stats = await voice_cache_service.get_cache_stats(db)

                result = {
                    "timestamp": datetime.now().isoformat(),
                    "cleanup_type": cleanup_type,
                    "cleanup_results": {
                        "expired_removed": expired_count,
                        "invalid_removed": invalid_count,
                        "total_removed": expired_count + invalid_count,
                    },
                    "current_stats": stats,
                }

                logger.info(
                    f"手动清理完成: 删除过期文件 {expired_count} 个，无效文件 {invalid_count} 个"
                )
                return result

            except Exception as e:
                logger.error(f"手动清理任务执行失败: {str(e)}")
                return {
                    "timestamp": datetime.now().isoformat(),
                    "cleanup_type": cleanup_type,
                    "error": str(e),
                    "cleanup_results": {
                        "expired_removed": 0,
                        "invalid_removed": 0,
                        "total_removed": 0,
                    },
                }

    async def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        获取清理服务统计信息

        Returns:
            统计信息
        """
        async with AsyncSessionLocal() as db:
            try:
                cache_stats = await voice_cache_service.get_cache_stats(db)

                return {
                    "timestamp": datetime.now().isoformat(),
                    "service_status": "running" if self.running else "stopped",
                    "cleanup_interval_seconds": self.cleanup_interval,
                    "cache_stats": cache_stats,
                }

            except Exception as e:
                logger.error(f"获取清理统计失败: {str(e)}")
                return {
                    "timestamp": datetime.now().isoformat(),
                    "service_status": "error",
                    "error": str(e),
                }


# 创建全局实例
voice_cleanup_service = VoiceCleanupService()
