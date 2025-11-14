"""
推送定时任务调度服务

使用 APScheduler 实现三个阶段的推送检查任务。
"""

import asyncio
import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.services.push_notification_service import (
    discover_new_users_for_push,
    discover_users_with_updated_tokens,
    initialize_push_system,
    process_push_batch,
)


class PushSchedulerService:
    """推送定时任务调度服务"""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False

    def start(self) -> None:
        """启动定时任务调度器"""
        if self.is_running:
            logger.warning("推送调度器已在运行")
            return

        try:
            # 创建调度器
            self.scheduler = AsyncIOScheduler()

            # 获取配置
            config = global_config_loaded_from_config_yaml.push_notification

            if not config.enabled:
                logger.info("推送服务未启用")
                return

            # 启动调度器（必须在添加任务之前启动）
            self.scheduler.start()
            self.is_running = True

            # 初始化推送系统（在后台异步执行，不阻塞启动）
            async def init_push_system():
                async with AsyncSessionLocal() as db:
                    await initialize_push_system(db)

            # 在后台执行初始化任务
            asyncio.create_task(init_push_system())

            # 添加五个定时任务（统一使用相同的阶段策略）
            # 10分钟推送：每5分钟检查一次，启动后立即执行一次
            self.scheduler.add_job(
                self._check_push_stage,
                trigger=IntervalTrigger(minutes=5),
                id="check_10min_push",
                name="检查10分钟推送",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
                args=["10min"],
            )

            # 30分钟推送：每10分钟检查一次，启动后立即执行一次
            self.scheduler.add_job(
                self._check_push_stage,
                trigger=IntervalTrigger(minutes=10),
                id="check_30min_push",
                name="检查30分钟推送",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
                args=["30min"],
            )

            # 2小时推送：每30分钟检查一次，启动后立即执行一次
            self.scheduler.add_job(
                self._check_push_stage,
                trigger=IntervalTrigger(minutes=30),
                id="check_2h_push",
                name="检查2小时推送",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
                args=["2h"],
            )

            # 24小时推送：每6小时检查一次，启动后立即执行一次
            self.scheduler.add_job(
                self._check_push_stage,
                trigger=IntervalTrigger(hours=6),
                id="check_24h_push",
                name="检查24小时推送",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
                args=["24h"],
            )

            # 48小时推送：每12小时检查一次，启动后立即执行一次
            self.scheduler.add_job(
                self._check_push_stage,
                trigger=IntervalTrigger(hours=12),
                id="check_48h_push",
                name="检查48小时推送",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
                args=["48h"],
            )

            # 发现新用户：每小时扫描一次，启动后立即执行一次
            self.scheduler.add_job(
                self._discover_new_users,
                trigger=IntervalTrigger(hours=1),
                id="discover_new_users",
                name="发现新用户",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
            )

            # 扫描已更新 token 的用户：每小时扫描一次，启动后立即执行一次
            self.scheduler.add_job(
                self._discover_users_with_updated_tokens,
                trigger=IntervalTrigger(hours=1),
                id="discover_users_with_updated_tokens",
                name="扫描已更新 token 的用户",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
            )

            logger.info("已添加所有推送检查任务，将在启动后立即执行一次")

            logger.info("推送调度器启动成功")

        except Exception as e:
            logger.error(f"启动推送调度器失败: {str(e)}")
            raise

    def stop(self) -> None:
        """停止定时任务调度器"""
        if not self.is_running:
            return

        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("推送调度器已停止")

        except Exception as e:
            logger.error(f"停止推送调度器失败: {str(e)}")

    async def _check_push_stage(self, stage: str) -> None:
        """
        统一处理推送阶段（所有阶段统一处理）

        Args:
            stage: 推送阶段 (10min, 30min, 2h, 24h, 48h)
        """
        try:
            logger.info(f"开始处理推送阶段 {stage}")

            # 获取配置
            config = global_config_loaded_from_config_yaml.push_notification
            batch_size = config.batch_size

            # 创建数据库会话
            async with AsyncSessionLocal() as db:
                try:
                    # 使用统一的批次处理函数
                    success_count, fail_count = await process_push_batch(
                        db=db,
                        stage=stage,
                        batch_size=batch_size,
                    )

                    logger.info(
                        f"推送阶段 {stage} 处理完成: 成功={success_count}, 失败={fail_count}"
                    )

                except Exception as e:
                    logger.error(f"处理推送阶段 {stage} 失败: {str(e)}")

        except Exception as e:
            logger.error(f"推送阶段 {stage} 执行失败: {str(e)}")

    async def _discover_new_users(self) -> None:
        """
        定期扫描新用户（没有推送记录的用户）

        这个任务每小时执行一次，确保新用户能够被推送系统发现。
        """
        try:
            logger.info("[新用户发现] 开始扫描新用户...")

            # 获取配置
            config = global_config_loaded_from_config_yaml.push_notification
            batch_size = config.batch_size

            # 创建数据库会话
            async with AsyncSessionLocal() as db:
                try:
                    # 发现新用户
                    new_users_count = await discover_new_users_for_push(
                        db, batch_size=batch_size
                    )

                    logger.info(
                        f"[新用户发现] 扫描完成: 发现 {new_users_count} 个新用户"
                    )

                except Exception as e:
                    logger.error(f"扫描新用户失败: {str(e)}")

        except Exception as e:
            logger.error(f"新用户发现任务执行失败: {str(e)}")

    async def _discover_users_with_updated_tokens(self) -> None:
        """
        定期扫描已更新 token 的用户（之前被标记为无效 token，但现在有新的 token）

        这个任务每小时执行一次，检查被标记为无效 token 的用户是否更新了 token。
        """
        try:
            logger.info("[token 更新扫描] 开始扫描已更新 token 的用户...")

            # 获取配置
            config = global_config_loaded_from_config_yaml.push_notification
            batch_size = config.batch_size

            # 创建数据库会话
            async with AsyncSessionLocal() as db:
                try:
                    # 扫描已更新 token 的用户
                    cleared_count = await discover_users_with_updated_tokens(
                        db, batch_size=batch_size
                    )

                    logger.info(
                        f"[token 更新扫描] 扫描完成: 清除 {cleared_count} 个用户的无效 token 标记"
                    )

                except Exception as e:
                    logger.error(f"扫描已更新 token 的用户失败: {str(e)}")

        except Exception as e:
            logger.error(f"token 更新扫描任务执行失败: {str(e)}")


# 全局调度器实例
push_scheduler_service = PushSchedulerService()
