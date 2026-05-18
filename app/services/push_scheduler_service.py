"""
推送定时任务调度服务

使用 APScheduler 实现三个阶段的推送检查任务。
"""

import asyncio
import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import or_, select, update

from app.api.types.llm_config import LLMConfig
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal, AsyncSessionLocalReplica
from app.models.memory import FestivalMemoryConfig
from app.services import festival_memory_service
from app.services.memory_extraction_service import (
    extract_and_save as memory_extract_and_save,
)
from app.services.memory_extraction_service import (
    extract_and_save_incremental_daily as memory_extract_and_save_incremental_daily,
)
from app.services.memory_extraction_service import (
    get_users_to_extract as memory_get_users_to_extract,
)
from app.services.memory_extraction_service import (
    get_users_with_messages_in_utc_day as memory_get_users_with_messages_in_utc_day,
)
from app.services.push_notification_service import (
    discover_new_users_for_push,
    discover_users_with_updated_tokens,
    initialize_push_system,
    process_festival_memory_push_batch,
    process_push_batch,
)
from app.services.user_analytics_report_service import (
    compute_and_save_daily_report as user_analytics_compute_daily,
)
from app.services.user_analytics_report_service import (
    compute_and_save_weekly_report as user_analytics_compute_weekly,
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

            # 记忆抽取：每日 UTC cron_hour 点执行（若启用）
            mem_cfg = getattr(
                global_config_loaded_from_config_yaml,
                "memory_extraction",
                None,
            )
            if mem_cfg and getattr(mem_cfg, "enabled", False):
                self.scheduler.add_job(
                    self._run_memory_extraction,
                    trigger=CronTrigger(hour=mem_cfg.cron_hour, minute=0),
                    id="run_memory_extraction",
                    name="记忆抽取",
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                )
                logger.info(
                    f"已添加记忆抽取任务: 每日 UTC {mem_cfg.cron_hour}:00 执行"
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

            # 用户分析预计算：默认全关（user_analytics_report.* 见 config 与 FR_USER_ANALYTICS_REPORTS.md）。
            # 生产日报由 GitHub Actions 跑；此处仅在有显式配置时注册 cron / 启动补算。
            uar_cfg = getattr(
                global_config_loaded_from_config_yaml,
                "user_analytics_report",
                None,
            )
            if uar_cfg and getattr(uar_cfg, "enabled", False):
                daily_enabled = getattr(uar_cfg, "daily_enabled", False)
                weekly_enabled = getattr(uar_cfg, "weekly_enabled", False)
                backfill_enabled = getattr(uar_cfg, "backfill_enabled", False)
                if daily_enabled:
                    self.scheduler.add_job(
                        self._run_user_analytics_daily_report,
                        trigger=CronTrigger(
                            hour=uar_cfg.daily_cron_hour, minute=0
                        ),
                        id="run_user_analytics_daily_report",
                        name="用户数据分析日报",
                        replace_existing=True,
                        coalesce=True,
                        max_instances=1,
                        next_run_time=datetime.datetime.now(),
                    )
                if weekly_enabled:
                    self.scheduler.add_job(
                        self._run_user_analytics_weekly_report,
                        trigger=CronTrigger(
                            day_of_week="mon",
                            hour=uar_cfg.weekly_cron_hour,
                            minute=0,
                        ),
                        id="run_user_analytics_weekly_report",
                        name="用户数据分析周报",
                        replace_existing=True,
                        coalesce=True,
                        max_instances=1,
                        next_run_time=datetime.datetime.now(),
                    )
                scheduled_parts: list[str] = []
                if daily_enabled:
                    scheduled_parts.append(
                        f"日报每日 UTC {uar_cfg.daily_cron_hour}:00"
                    )
                if weekly_enabled:
                    scheduled_parts.append(
                        f"周报每周一 UTC {uar_cfg.weekly_cron_hour}:00"
                    )
                if scheduled_parts:
                    logger.info(
                        f"已添加用户数据分析任务: {', '.join(scheduled_parts)}"
                    )
                elif not backfill_enabled:
                    logger.info(
                        "用户数据分析日报/周报/补算均未启用（push worker 默认关闭；日报由 GitHub Actions 承担）"
                    )

                if backfill_enabled:

                    async def backfill_user_analytics_reports():
                        from app.services.user_analytics_report_service import (
                            backfill_missing_reports,
                        )

                        scope_parts: list[str] = []
                        if daily_enabled:
                            scope_parts.append("日报")
                        if weekly_enabled:
                            scope_parts.append("周报")
                        backfill_scope = (
                            "与".join(scope_parts) if scope_parts else "无"
                        )
                        logger.info(
                            f"[用户数据分析补算] 开始检查并补算缺失的{backfill_scope}"
                        )
                        try:
                            async with AsyncSessionLocal() as db:
                                daily_count, weekly_count = (
                                    await backfill_missing_reports(
                                        db,
                                        include_daily=daily_enabled,
                                        include_weekly=weekly_enabled,
                                    )
                                )
                                logger.info(
                                    f"[用户数据分析补算] 完成: 日报 {daily_count} 条, 周报 {weekly_count} 条"
                                )
                        except Exception as e:
                            logger.error(
                                f"[用户数据分析补算] 执行失败: {str(e)}"
                            )

                    asyncio.create_task(backfill_user_analytics_reports())

            logger.info("已添加所有推送检查任务（记忆抽取除外，按 cron 执行）")

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

    async def _run_memory_extraction(self) -> None:
        """每日记忆抽取：筛选待抽取用户并逐个 extract_and_save。"""
        try:
            logger.info("[记忆抽取] 开始...")
            mem_cfg = getattr(
                global_config_loaded_from_config_yaml,
                "memory_extraction",
                None,
            )
            workflow_mode = (
                getattr(mem_cfg, "workflow_mode", None).value
                if getattr(mem_cfg, "workflow_mode", None) is not None
                and hasattr(getattr(mem_cfg, "workflow_mode", None), "value")
                else getattr(
                    mem_cfg,
                    "workflow_mode",
                    "always_summarize_full_chat_messages_history",
                )
            )
            read_session_factory = (
                AsyncSessionLocalReplica
                if AsyncSessionLocalReplica is not None
                else AsyncSessionLocal
            )
            read_source = (
                "replica" if AsyncSessionLocalReplica is not None else "primary"
            )
            logger.info(
                f"[记忆抽取] 用户筛选与历史读取将优先使用: {read_source}"
            )

            async with read_session_factory() as read_db:
                if workflow_mode == "daily_incremental_summarization":
                    target_date_utc = datetime.datetime.now(
                        datetime.timezone.utc
                    ).date() - datetime.timedelta(days=1)
                    logger.info(
                        "[记忆抽取] 模式=daily_incremental_summarization "
                        f"target_date_utc={target_date_utc}"
                    )
                    user_ids = await memory_get_users_with_messages_in_utc_day(
                        read_db,
                        target_date_utc=target_date_utc,
                        prefer_replica_read=True,
                    )
                else:
                    logger.info(
                        "[记忆抽取] 模式=always_summarize_full_chat_messages_history"
                    )
                    user_ids = await memory_get_users_to_extract(
                        read_db, prefer_replica_read=True
                    )

            logger.info(f"[记忆抽取] 待处理用户数: {len(user_ids)}")
            async with AsyncSessionLocal() as write_db:
                for uid in user_ids:
                    try:
                        if workflow_mode == "daily_incremental_summarization":
                            await memory_extract_and_save_incremental_daily(
                                write_db,
                                uid,
                                target_date_utc=target_date_utc,
                                prefer_replica_read=True,
                            )
                        else:
                            await memory_extract_and_save(
                                write_db, uid, prefer_replica_read=True
                            )
                    except Exception as e:
                        await write_db.rollback()
                        logger.warning(f"[记忆抽取] user_id={uid} 失败: {e}")
            logger.info("[记忆抽取] 完成")
        except Exception as e:
            logger.error(f"[记忆抽取] 执行失败: {str(e)}")

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

    async def _run_user_analytics_daily_report(self) -> None:
        """每日用户数据分析日报（T-1 UTC）；仅 daily_enabled 时由 scheduler 调用。"""
        try:
            from datetime import timedelta, timezone

            logger.info("[用户数据分析日报] 开始...")
            today_utc = datetime.datetime.now(timezone.utc).date()
            report_date = today_utc - timedelta(days=1)
            async with AsyncSessionLocal() as db:
                await user_analytics_compute_daily(db, report_date)
            logger.info("[用户数据分析日报] 完成")
        except Exception:
            logger.exception("[用户数据分析日报] 执行失败")

    async def _run_user_analytics_weekly_report(self) -> None:
        """每周用户数据分析周报；仅 weekly_enabled 时由 scheduler 调用。"""
        try:
            from datetime import timedelta, timezone

            logger.info("[用户数据分析周报] 开始...")
            today = datetime.datetime.now(timezone.utc).date()
            week_start = today - timedelta(days=today.weekday() + 7)
            async with AsyncSessionLocal() as db:
                await user_analytics_compute_weekly(db, week_start)
            logger.info("[用户数据分析周报] 完成")
        except Exception:
            logger.exception("[用户数据分析周报] 执行失败")


# 全局调度器实例
push_scheduler_service = PushSchedulerService()
