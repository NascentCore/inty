from __future__ import annotations

from dataclasses import dataclass

from ...telegram_channel import TelegramBotApi
from ..adapters.sms_adapter import SmsAdapter
from ..adapters.telegram_adapter import TelegramAdapter
from ..repositories.cursor_repo import CursorRepository
from ..repositories.events_repo import EventsRepository
from ..repositories.lease_repo import LeaseRepository
from ..repositories.memory_repo import MemoryRepository
from ..repositories.plan_repo import PlanRepository
from ..repositories.sqlite_db import SQLiteDatabase
from ..repositories.sqlite_schema import init_schema
from ..runtime.orchestrator import Orchestrator
from ..settings import CompanionSettings, get_settings


@dataclass(frozen=True)
class AppContext:
    settings: CompanionSettings
    db: SQLiteDatabase
    events_repo: EventsRepository
    memory_repo: MemoryRepository
    plan_repo: PlanRepository
    lease_repo: LeaseRepository
    cursor_repo: CursorRepository
    telegram_adapter: TelegramAdapter
    sms_adapter: SmsAdapter
    orchestrator: Orchestrator


def build_app_context(settings: CompanionSettings | None = None) -> AppContext:
    cfg = settings or get_settings()
    db = SQLiteDatabase(cfg.database_path)
    init_schema(db)

    events_repo = EventsRepository(db)
    memory_repo = MemoryRepository(db)
    plan_repo = PlanRepository(db)
    lease_repo = LeaseRepository(db)
    cursor_repo = CursorRepository(db)

    bot_api = TelegramBotApi(bot_token=cfg.telegram_bot_token)
    telegram_adapter = TelegramAdapter(
        bot_api=bot_api,
        poll_timeout_seconds=cfg.telegram_poll_timeout_seconds,
    )
    sms_adapter = SmsAdapter.create_default()
    orchestrator = Orchestrator(
        events_repo=events_repo,
        memory_repo=memory_repo,
        plan_repo=plan_repo,
        cursor_repo=cursor_repo,
        sms_adapter=sms_adapter,
        telegram_send_func=telegram_adapter.send_text,
        planner_followup_delay_minutes=cfg.planner_followup_delay_minutes,
        quiet_hours_start_hour_local=cfg.quiet_hours_start_hour_local,
        quiet_hours_end_hour_local=cfg.quiet_hours_end_hour_local,
        scheduler_default_telegram_chat_id=cfg.scheduler_default_telegram_chat_id,
        scheduler_default_sms_recipient=cfg.scheduler_default_sms_recipient,
    )
    return AppContext(
        settings=cfg,
        db=db,
        events_repo=events_repo,
        memory_repo=memory_repo,
        plan_repo=plan_repo,
        lease_repo=lease_repo,
        cursor_repo=cursor_repo,
        telegram_adapter=telegram_adapter,
        sms_adapter=sms_adapter,
        orchestrator=orchestrator,
    )
