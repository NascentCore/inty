# CREATED_BY_AGENT
"""
用户数据分析预计算报告服务

compute_and_save_* 将全部用户聚合写入 user_analytics_report，供评测页只读展示。

调度入口（互斥注意生产日报勿双开）：
- 生产 IntelliMate 日报：GitHub Actions + run_user_analytics_report.py
- push worker：push_scheduler_service，默认 user_analytics_report 四项开关均为 false
- 手动/回填：tools/scripts/run_user_analytics_report.py、backfill_missing_reports
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal, AsyncSessionLocalReplica
from app.models.user_analytics_report import UserAnalyticsReport
from app.services.user_analytics_service import UserAnalyticsService

BACKFILL_DAILY_DAYS = 30
POPULAR_AGENTS_QUERY_LIMIT = 2000
DAILY_TOP_AGENTS_LIMIT = 10

REPLICA_READ_MAX_ATTEMPTS = 3  # 含首次共 3 次，用于 conflict with recovery 重试
REPLICA_READ_RETRY_SLEEP_SEC = 3


async def _ensure_statement_timeout(db: AsyncSession) -> None:
    uar_cfg = getattr(
        global_config_loaded_from_config_yaml,
        "user_analytics_report",
        None,
    )
    timeout_sec = getattr(uar_cfg, "statement_timeout_sec", 600)
    await db.execute(
        text(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}'")
    )


ALL_USERS_REGISTER_START = datetime(2020, 1, 1, tzinfo=timezone.utc)


def _safe_to_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_daily_top_agents_by_rounds(
    popular_agents: list[dict],
    limit: int,
) -> list[dict]:
    # 关键步骤：按总聊天轮数排序，补齐 rank 便于前端做“同角色跨日期连线”展示。
    sorted_agents = sorted(
        popular_agents,
        key=lambda item: (
            _safe_to_int(item.get("total_rounds")),
            _safe_to_int(item.get("user_count")),
        ),
        reverse=True,
    )
    top_agents: list[dict] = []
    for rank, item in enumerate(sorted_agents[:limit], start=1):
        agent_name = item.get("agent_name")
        if not agent_name:
            continue
        top_agents.append(
            {
                "rank": rank,
                "agent_name": agent_name,
                "total_rounds": _safe_to_int(item.get("total_rounds")),
                "user_count": _safe_to_int(item.get("user_count")),
                "total_sessions": _safe_to_int(item.get("total_sessions")),
                "active_sessions": _safe_to_int(item.get("active_sessions")),
            }
        )
    return top_agents


def _build_daily_charts(
    new_users: list,
    conversation_rounds: list,
    user_rounds_distribution: list,
    users_hitting_limit: list,
    popular_agents: list,
    generated_images: list,
    daily_top_agents_by_rounds: list,
    daily_most_discussed_agent: dict | None,
) -> dict:
    return {
        "new_users": [
            {
                "date": d["date"],
                "auth_type": d["auth_type"],
                "count": d["count"],
            }
            for d in new_users
        ],
        "conversation_rounds": [
            {
                "chat_id": d["chat_id"],
                "message_count": d["message_count"],
                "message_count_excluding_opening": d[
                    "message_count_excluding_opening"
                ],
            }
            for d in conversation_rounds
        ],
        "user_rounds_distribution": [
            {"user_id": d["user_id"], "total_rounds": d["total_rounds"]}
            for d in user_rounds_distribution
        ],
        "users_hitting_limit": [
            {
                "date": d["date"],
                "user_id": d["user_id"],
                "auth_type": d["auth_type"],
                "nickname": d.get("nickname"),
                "email": d.get("email"),
                "chat_count_24h": d["chat_count_24h"],
                "limit_value": d["limit_value"],
            }
            for d in users_hitting_limit
        ],
        "popular_agents": popular_agents,
        "generated_images": generated_images,
        "daily_top_agents_by_rounds": daily_top_agents_by_rounds,
        "daily_most_discussed_agent": daily_most_discussed_agent,
    }


async def _read_daily_report_from_replica(
    reg_start: datetime,
    reg_end: datetime,
    act_start: datetime,
    act_end: datetime,
) -> tuple[dict, dict]:
    """从副本读取日报所需统计与图表数据。调用方需保证 AsyncSessionLocalReplica 非空。

    先取当日有活动的 session 集合，仅对这些 session 做批量聚合以减轻副本负载。
    """
    async with AsyncSessionLocalReplica() as read_db:
        await _ensure_statement_timeout(read_db)
        service = UserAnalyticsService(read_db)
        active_session_ids = await service.get_active_session_ids_on_date(
            act_start, act_end
        )
        logger.info(
            f"[用户数据分析日报] 当日有活动的 session 数: {len(active_session_ids)}，"
            "仅对上述 session 做聚合"
        )
        stats = await service.get_analytics_stats(
            register_start_date=reg_start,
            register_end_date=reg_end,
            activity_start_date=act_start,
            activity_end_date=act_end,
            active_session_ids=active_session_ids,
        )
        new_users = await service.get_new_users(reg_start, reg_end)
        conversation_rounds = await service.get_conversation_rounds(
            reg_start,
            reg_end,
            act_start,
            act_end,
            active_session_ids=active_session_ids,
        )
        user_rounds_distribution = await service.get_user_rounds_distribution(
            reg_start,
            reg_end,
            act_start,
            act_end,
            active_session_ids=active_session_ids,
        )
        users_hitting_limit = await service.get_users_hitting_chat_limit(
            act_start, act_end
        )
        popular_agents_ranked = await service.get_popular_agents(
            reg_start,
            reg_end,
            act_start,
            act_end,
            limit=POPULAR_AGENTS_QUERY_LIMIT,
            active_session_ids=active_session_ids,
        )
        popular_agents = popular_agents_ranked[:20]
        daily_top_agents_by_rounds = _build_daily_top_agents_by_rounds(
            popular_agents_ranked, DAILY_TOP_AGENTS_LIMIT
        )
        daily_most_discussed_agent = (
            daily_top_agents_by_rounds[0]
            if daily_top_agents_by_rounds
            else None
        )
        generated_images = await service.get_generated_images_on_date(
            act_start, act_end
        )
        charts = _build_daily_charts(
            new_users,
            conversation_rounds,
            user_rounds_distribution,
            users_hitting_limit,
            popular_agents,
            generated_images,
            daily_top_agents_by_rounds,
            daily_most_discussed_agent,
        )
    return stats, charts


async def _read_daily_report_from_primary(
    db: AsyncSession,
    reg_start: datetime,
    reg_end: datetime,
    act_start: datetime,
    act_end: datetime,
) -> tuple[dict, dict]:
    """从主库读取日报所需统计与图表数据。"""
    await _ensure_statement_timeout(db)
    service = UserAnalyticsService(db)
    active_session_ids = await service.get_active_session_ids_on_date(
        act_start, act_end
    )
    logger.info(
        f"[用户数据分析日报] 当日有活动的 session 数: {len(active_session_ids)}，"
        "仅对上述 session 做聚合"
    )
    stats = await service.get_analytics_stats(
        register_start_date=reg_start,
        register_end_date=reg_end,
        activity_start_date=act_start,
        activity_end_date=act_end,
        active_session_ids=active_session_ids,
    )
    new_users = await service.get_new_users(reg_start, reg_end)
    conversation_rounds = await service.get_conversation_rounds(
        reg_start,
        reg_end,
        act_start,
        act_end,
        active_session_ids=active_session_ids,
    )
    user_rounds_distribution = await service.get_user_rounds_distribution(
        reg_start,
        reg_end,
        act_start,
        act_end,
        active_session_ids=active_session_ids,
    )
    users_hitting_limit = await service.get_users_hitting_chat_limit(
        act_start, act_end
    )
    popular_agents_ranked = await service.get_popular_agents(
        reg_start,
        reg_end,
        act_start,
        act_end,
        limit=POPULAR_AGENTS_QUERY_LIMIT,
        active_session_ids=active_session_ids,
    )
    popular_agents = popular_agents_ranked[:20]
    daily_top_agents_by_rounds = _build_daily_top_agents_by_rounds(
        popular_agents_ranked, DAILY_TOP_AGENTS_LIMIT
    )
    daily_most_discussed_agent = (
        daily_top_agents_by_rounds[0] if daily_top_agents_by_rounds else None
    )
    generated_images = await service.get_generated_images_on_date(
        act_start, act_end
    )
    charts = _build_daily_charts(
        new_users,
        conversation_rounds,
        user_rounds_distribution,
        users_hitting_limit,
        popular_agents,
        generated_images,
        daily_top_agents_by_rounds,
        daily_most_discussed_agent,
    )
    return stats, charts


def _is_conflict_with_recovery(exc: BaseException) -> bool:
    """是否为 PostgreSQL standby conflict with recovery 导致的错误。"""
    return "conflict with recovery" in str(exc)


async def compute_and_save_daily_report(
    db: AsyncSession, report_date: date
) -> UserAnalyticsReport | None:
    """计算并保存日报

    统计 report_date 当天的全部用户活跃数据。
    用户范围：register_start=2020-01-01, register_end=report_date+1
    活跃范围：activity_start=report_date, activity_end=report_date+1
    读请求走副本（若已配置），写请求走主库 db。
    """
    reg_start = ALL_USERS_REGISTER_START
    reg_end = datetime.combine(
        report_date + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    act_start = datetime.combine(
        report_date, datetime.min.time(), tzinfo=timezone.utc
    )
    act_end = reg_end

    if AsyncSessionLocalReplica is not None:
        replica_read_succeeded = False
        for attempt in range(REPLICA_READ_MAX_ATTEMPTS):
            try:
                stats, charts = await _read_daily_report_from_replica(
                    reg_start, reg_end, act_start, act_end
                )
                replica_read_succeeded = True
                break
            except OperationalError as e:
                if not _is_conflict_with_recovery(e):
                    raise
                if attempt < REPLICA_READ_MAX_ATTEMPTS - 1:
                    logger.warning(
                        f"日报副本读 conflict with recovery，{REPLICA_READ_RETRY_SLEEP_SEC}s 后重试 "
                        f"（第 {attempt + 1}/{REPLICA_READ_MAX_ATTEMPTS} 次）"
                    )
                    await asyncio.sleep(REPLICA_READ_RETRY_SLEEP_SEC)
                else:
                    logger.warning(
                        "日报副本读多次 conflict with recovery，回退主库读取以避免缺失日报"
                    )
        if not replica_read_succeeded:
            stats, charts = await _read_daily_report_from_primary(
                db, reg_start, reg_end, act_start, act_end
            )
    else:
        stats, charts = await _read_daily_report_from_primary(
            db, reg_start, reg_end, act_start, act_end
        )

    existing = await db.execute(
        select(UserAnalyticsReport).where(
            UserAnalyticsReport.report_type == "daily",
            UserAnalyticsReport.report_date == report_date,
        )
    )
    if existing.scalar_one_or_none():
        logger.info(f"日报 {report_date} 已存在，跳过")
        return None

    report = UserAnalyticsReport(
        report_type="daily",
        report_date=report_date,
        stats=stats,
        charts=charts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    logger.info(f"日报 {report_date} 已保存")
    return report


def _build_weekly_charts(
    new_users: list,
    conversation_rounds: list,
    user_rounds_distribution: list,
    users_hitting_limit: list,
    popular_agents: list,
) -> dict:
    return {
        "new_users": [
            {
                "date": d["date"],
                "auth_type": d["auth_type"],
                "count": d["count"],
            }
            for d in new_users
        ],
        "conversation_rounds": [
            {
                "chat_id": d["chat_id"],
                "message_count": d["message_count"],
                "message_count_excluding_opening": d[
                    "message_count_excluding_opening"
                ],
            }
            for d in conversation_rounds
        ],
        "user_rounds_distribution": [
            {"user_id": d["user_id"], "total_rounds": d["total_rounds"]}
            for d in user_rounds_distribution
        ],
        "users_hitting_limit": [
            {
                "date": d["date"],
                "user_id": d["user_id"],
                "auth_type": d["auth_type"],
                "nickname": d.get("nickname"),
                "email": d.get("email"),
                "chat_count_24h": d["chat_count_24h"],
                "limit_value": d["limit_value"],
            }
            for d in users_hitting_limit
        ],
        "popular_agents": popular_agents,
    }


async def compute_and_save_weekly_report(
    db: AsyncSession, week_start_date: date
) -> UserAnalyticsReport | None:
    """计算并保存周报

    统计 week_start_date（周一）至周日共 7 天的全部用户活跃数据。
    用户范围：register_start=2020-01-01, register_end=week_start_date+7
    活跃范围：activity_start=week_start_date, activity_end=week_start_date+7
    读请求走副本（若已配置），写请求走主库 db。
    """
    reg_start = ALL_USERS_REGISTER_START
    week_end = week_start_date + timedelta(days=7)
    reg_end = datetime.combine(
        week_end, datetime.min.time(), tzinfo=timezone.utc
    )
    act_start = datetime.combine(
        week_start_date, datetime.min.time(), tzinfo=timezone.utc
    )
    act_end = reg_end

    async def _read_weekly_report_with_service(
        service: UserAnalyticsService,
    ) -> tuple[dict, dict]:
        stats = await service.get_analytics_stats(
            register_start_date=reg_start,
            register_end_date=reg_end,
            activity_start_date=act_start,
            activity_end_date=act_end,
        )
        new_users = await service.get_new_users(reg_start, reg_end)
        conversation_rounds = await service.get_conversation_rounds(
            reg_start, reg_end, act_start, act_end
        )
        user_rounds_distribution = await service.get_user_rounds_distribution(
            reg_start, reg_end, act_start, act_end
        )
        users_hitting_limit = await service.get_users_hitting_chat_limit(
            act_start, act_end
        )
        popular_agents = await service.get_popular_agents(
            reg_start, reg_end, act_start, act_end, limit=20
        )
        charts = _build_weekly_charts(
            new_users,
            conversation_rounds,
            user_rounds_distribution,
            users_hitting_limit,
            popular_agents,
        )
        return stats, charts

    async def _read_weekly_report_from_primary() -> tuple[dict, dict]:
        await _ensure_statement_timeout(db)
        service = UserAnalyticsService(db)
        return await _read_weekly_report_with_service(service)

    async def _read_weekly_report_from_replica() -> tuple[dict, dict]:
        async with AsyncSessionLocalReplica() as read_db:
            await _ensure_statement_timeout(read_db)
            service = UserAnalyticsService(read_db)
            return await _read_weekly_report_with_service(service)

    if AsyncSessionLocalReplica is not None:
        replica_read_succeeded = False
        for attempt in range(REPLICA_READ_MAX_ATTEMPTS):
            try:
                stats, charts = await _read_weekly_report_from_replica()
                replica_read_succeeded = True
                break
            except OperationalError as e:
                if not _is_conflict_with_recovery(e):
                    raise
                if attempt < REPLICA_READ_MAX_ATTEMPTS - 1:
                    logger.warning(
                        f"周报副本读 conflict with recovery，{REPLICA_READ_RETRY_SLEEP_SEC}s 后重试 "
                        f"（第 {attempt + 1}/{REPLICA_READ_MAX_ATTEMPTS} 次）"
                    )
                    await asyncio.sleep(REPLICA_READ_RETRY_SLEEP_SEC)
                else:
                    logger.warning(
                        "周报副本读多次 conflict with recovery，回退主库读取以避免缺失周报"
                    )
        if not replica_read_succeeded:
            stats, charts = await _read_weekly_report_from_primary()
    else:
        stats, charts = await _read_weekly_report_from_primary()

    existing = await db.execute(
        select(UserAnalyticsReport).where(
            UserAnalyticsReport.report_type == "weekly",
            UserAnalyticsReport.report_date == week_start_date,
        )
    )
    if existing.scalar_one_or_none():
        logger.info(f"周报 {week_start_date} 已存在，跳过")
        return None

    report = UserAnalyticsReport(
        report_type="weekly",
        report_date=week_start_date,
        stats=stats,
        charts=charts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    logger.info(f"周报 {week_start_date} 已保存")
    return report


def _first_monday_of_year(year: int) -> date:
    d = date(year, 1, 1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def _mondays_in_first_half(year: int) -> list[date]:
    d = _first_monday_of_year(year)
    result: list[date] = []
    while d.month <= 6:
        result.append(d)
        d += timedelta(days=7)
    return result


async def get_missing_daily_report_dates(
    db: AsyncSession, days: int = BACKFILL_DAILY_DAYS
) -> list[date]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days)
    end = today - timedelta(days=1)
    expected_dates = [
        start + timedelta(days=i) for i in range((end - start).days + 1)
    ]
    if not expected_dates:
        return []

    result = await db.execute(
        select(UserAnalyticsReport.report_date).where(
            UserAnalyticsReport.report_type == "daily",
            UserAnalyticsReport.report_date.in_(expected_dates),
        )
    )
    existing = set(result.scalars().all())
    return [d for d in expected_dates if d not in existing]


async def get_missing_weekly_report_dates_first_half(
    db: AsyncSession, year: int
) -> list[date]:
    expected_dates = _mondays_in_first_half(year)
    if not expected_dates:
        return []

    result = await db.execute(
        select(UserAnalyticsReport.report_date).where(
            UserAnalyticsReport.report_type == "weekly",
            UserAnalyticsReport.report_date.in_(expected_dates),
        )
    )
    existing = set(result.scalars().all())
    return [d for d in expected_dates if d not in existing]


async def get_missing_weekly_report_dates_past_weeks(
    db: AsyncSession, weeks: int = 7
) -> list[date]:
    today = datetime.now(timezone.utc).date()
    base = today - timedelta(days=today.weekday() + 7)
    expected_dates = [base - timedelta(days=i * 7) for i in range(weeks)]
    if not expected_dates:
        return []

    result = await db.execute(
        select(UserAnalyticsReport.report_date).where(
            UserAnalyticsReport.report_type == "weekly",
            UserAnalyticsReport.report_date.in_(expected_dates),
        )
    )
    existing = set(result.scalars().all())
    return [d for d in expected_dates if d not in existing]


async def backfill_missing_reports(
    db: AsyncSession,
    days: int = BACKFILL_DAILY_DAYS,
    year: int | None = None,
    include_daily: bool = True,
    include_weekly: bool = True,
) -> tuple[int, int]:
    """补算缺失日报/周报。push worker 仅在 backfill_enabled 且对应 daily/weekly 开关为 true 时调用。"""
    missing_daily: list[date] = []
    if include_daily:
        missing_daily = await get_missing_daily_report_dates(db, days=days)
    missing_weekly: list[date] = []
    if include_weekly:
        if year is not None:
            missing_weekly = await get_missing_weekly_report_dates_first_half(
                db, year
            )
        else:
            missing_weekly = await get_missing_weekly_report_dates_past_weeks(
                db, weeks=7
            )
    scope_parts: list[str] = []
    if include_daily:
        scope_parts.append(f"日报最近 {days} 天")
    if include_weekly:
        if year is not None:
            scope_parts.append("周报当年上半年")
        else:
            scope_parts.append("周报过去 7 周")
    scope_desc = "、".join(scope_parts) if scope_parts else "无"

    logger.info(
        f"[用户数据分析补算] 补算范围: {scope_desc}; "
        f"缺失日报 {len(missing_daily)} 天, 缺失周报 {len(missing_weekly)} 周"
    )
    if missing_daily:
        logger.info(
            f"[用户数据分析补算] 缺失日报日期: {sorted(missing_daily)[:10]}{'...' if len(missing_daily) > 10 else ''}"
        )
    if missing_weekly:
        logger.info(
            f"[用户数据分析补算] 缺失周报日期(周一): {sorted(missing_weekly)[:10]}{'...' if len(missing_weekly) > 10 else ''}"
        )

    daily_count = 0
    for d in missing_daily:
        try:
            logger.info(f"[用户数据分析补算] 正在补算日报 {d}")
            async with AsyncSessionLocal() as report_db:
                r = await compute_and_save_daily_report(report_db, d)
                if r is not None:
                    daily_count += 1
        except Exception as e:
            logger.warning(f"日报 {d} 补算失败: {e}")

    weekly_count = 0
    for d in missing_weekly:
        try:
            logger.info(f"[用户数据分析补算] 正在补算周报 {d}（当周周一）")
            async with AsyncSessionLocal() as report_db:
                r = await compute_and_save_weekly_report(report_db, d)
                if r is not None:
                    weekly_count += 1
        except Exception as e:
            logger.warning(f"周报 {d} 补算失败: {e}")

    return (daily_count, weekly_count)
