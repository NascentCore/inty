"""
推送定时任务调度服务

使用 APScheduler 调度 IntelliMate Android 仍依赖的 push worker 任务：
re-engagement FCM、节日记忆抽取与 FCM 通知，以及推送管线维护任务。
"""

import asyncio
import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import or_, select, update

from app.api.types.llm_config import LLMConfig
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal, AsyncSessionLocalReplica
from app.models.memory import FestivalMemoryConfig
from app.services import festival_memory_service
from app.services.push_notification_service import (
    discover_new_users_for_push,
    discover_users_with_updated_tokens,
    initialize_push_system,
    process_festival_memory_push_batch,
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

            # 节日记忆抽取：每 5 分钟扫描，仅执行 run_at 已到且未跑过的配置
            self.scheduler.add_job(
                self._run_festival_memory_extraction,
                trigger=IntervalTrigger(minutes=5),
                id="run_festival_memory_extraction",
                name="节日记忆抽取",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                next_run_time=datetime.datetime.now(),
            )
            logger.info(
                "已添加节日记忆抽取任务: 启动后立即执行，之后每 5 分钟扫描"
            )

            # 节日记忆通知：每 15 分钟扫描未投递且未发过 system notification 的节日记忆并发送 FCM（可选）
            if getattr(config, "festival_memory_enabled", True):
                self.scheduler.add_job(
                    self._run_festival_memory_push,
                    trigger=IntervalTrigger(minutes=15),
                    id="run_festival_memory_push",
                    name="节日记忆通知",
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    next_run_time=datetime.datetime.now(),
                )
                logger.info(
                    "已添加节日记忆通知任务: 启动后立即执行，之后每 15 分钟扫描"
                )

            logger.info("已添加所有推送定时任务")

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
                # wait=False 避免死锁：stop() 与 job 同处一事件循环，wait=True 会阻塞循环导致 job 无法结束
                self.scheduler.shutdown(wait=False)
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

    async def _run_festival_memory_extraction(self) -> None:
        """节日记忆抽取：每 5 分钟扫描，仅执行 run_at 已到且尚未为此执行时刻跑过的配置。"""
        from datetime import timezone as dt_timezone
        from zoneinfo import ZoneInfo

        try:
            logger.info("[节日记忆抽取] 开始...")
            now = datetime.datetime.now(dt_timezone.utc)
            read_session_factory = (
                AsyncSessionLocalReplica
                if AsyncSessionLocalReplica is not None
                else AsyncSessionLocal
            )
            read_source = (
                "replica" if AsyncSessionLocalReplica is not None else "primary"
            )
            logger.info(
                f"[节日记忆抽取] 配置与历史读取将优先使用: {read_source}"
            )

            async with read_session_factory() as db:
                result = await db.execute(
                    select(FestivalMemoryConfig).where(
                        FestivalMemoryConfig.enabled.is_(True),
                        FestivalMemoryConfig.run_at_date.isnot(None),
                        FestivalMemoryConfig.run_at_hour.isnot(None),
                    )
                )
                all_configs = result.scalars().all()
            due_configs = []
            for config in all_configs:
                tz_str = getattr(config, "timezone", "UTC") or "UTC"
                tz = ZoneInfo(tz_str)
                run_at_local = datetime.datetime.combine(
                    config.run_at_date,
                    datetime.time(config.run_at_hour or 0, 0, 0),
                    tzinfo=tz,
                )
                run_at_dt = run_at_local.astimezone(dt_timezone.utc)
                if now < run_at_dt:
                    continue
                if (
                    config.last_run_at is not None
                    and config.last_run_at >= run_at_dt
                ):
                    continue
                due_configs.append(config)
            if not due_configs:
                logger.debug("[节日记忆抽取] 无到点配置，跳过")
                return
            for config in due_configs:
                tz_str = getattr(config, "timezone", "UTC") or "UTC"
                tz = ZoneInfo(tz_str)
                run_at_local = datetime.datetime.combine(
                    config.run_at_date,
                    datetime.time(config.run_at_hour or 0, 0, 0),
                    tzinfo=tz,
                )
                run_at_dt = run_at_local.astimezone(dt_timezone.utc)
                # 占位：只有更新到 1 行的实例才执行 pairs，避免多实例重复执行
                async with AsyncSessionLocal() as db:
                    claim_result = await db.execute(
                        update(FestivalMemoryConfig)
                        .where(FestivalMemoryConfig.id == config.id)
                        .where(
                            or_(
                                FestivalMemoryConfig.last_run_at.is_(None),
                                FestivalMemoryConfig.last_run_at < run_at_dt,
                            )
                        )
                        .values(last_run_at=now)
                    )
                    await db.commit()
                if claim_result.rowcount != 1:
                    logger.debug(
                        f"[节日记忆抽取] config_id={config.id} 已被占位或已执行，跳过"
                    )
                    continue
                min_rounds = (
                    getattr(config, "min_rounds_in_window", None)
                    or festival_memory_service.DEFAULT_MIN_ROUNDS_IN_WINDOW
                )
                read_db_url = festival_memory_service.resolve_sync_read_db_url(
                    prefer_replica_read=True
                )
                pairs = await asyncio.to_thread(
                    festival_memory_service.get_pairs_with_min_rounds_in_window_sync,
                    config.festival_date,
                    read_db_url,
                    min_rounds,
                    tz_str,
                )
                async with AsyncSessionLocal() as db:
                    for user_id, agent_id in pairs:
                        try:
                            raw_llm = getattr(config, "llm_config", None)
                            await festival_memory_service.extract_festival_and_save(
                                db,
                                user_id,
                                agent_id,
                                config.festival_name,
                                config.festival_date,
                                config.prompt,
                                llm_config=(
                                    LLMConfig.model_validate(raw_llm)
                                    if raw_llm is not None
                                    else None
                                ),
                                prefer_replica_read=True,
                            )
                        except Exception as e:
                            await db.rollback()
                            logger.warning(
                                f"[节日记忆抽取] user_id={user_id} agent_id={agent_id} "
                                f"festival={config.festival_name} 失败: {e}"
                            )
            logger.info("[节日记忆抽取] 完成")
        except Exception as e:
            logger.error(f"[节日记忆抽取] 执行失败: {str(e)}")

    async def _run_festival_memory_push(self) -> None:
        """节日记忆通知：扫描未投递且未发过 system notification 的节日记忆并发送 FCM。"""
        try:
            logger.info("[节日记忆通知] 开始...")
            config = global_config_loaded_from_config_yaml.push_notification
            batch_size = getattr(config, "festival_memory_batch_size", 50)
            async with AsyncSessionLocal() as db:
                success_count, fail_count = (
                    await process_festival_memory_push_batch(
                        db, batch_size=batch_size
                    )
                )
            logger.info(
                f"[节日记忆通知] 完成: 成功={success_count}, 失败={fail_count}"
            )
        except Exception as e:
            logger.error(f"[节日记忆通知] 执行失败: {str(e)}")


# 全局调度器实例
push_scheduler_service = PushSchedulerService()
