"""Sleeping-state companion dreaming scheduler, separate from inner tick."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import select, text

from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.companion_memory_documents import (
    CompanionMemoryDocumentVersion,
)
from app.models.user import User
from app.services import companion_chat_service
from app.services.global_services import subscription_service

_DREAMING_SCAN_INTERVAL_SECONDS = 300


@dataclass(frozen=True)
class DreamingScope:
    """A companion MemoryStore scope with a persisted main transcript."""

    user_id: str
    companion_id: str
    chat_id: str

    @property
    def lock_key(self) -> str:
        return f"companion-dreaming:{self.user_id}:{self.companion_id}:{self.chat_id}"


class CompanionDreamingScheduler:
    """Process sleeping companion scopes without using WebSocket inner tick."""

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        """Start the process-local scheduler."""
        if self._scheduler is not None and self._scheduler.running:
            return
        scheduler = AsyncIOScheduler()
        self._add_scan_job(scheduler)
        scheduler.start()
        self._scheduler = scheduler
        logger.info("companion_dreaming_scheduler started")

    def _add_scan_job(self, scheduler: AsyncIOScheduler) -> None:
        scheduler.add_job(
            self.run_once,
            trigger=IntervalTrigger(seconds=_DREAMING_SCAN_INTERVAL_SECONDS),
            id="companion_dreaming_scan",
            name="companion sleeping-state dreaming scan",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            next_run_time=datetime.now(timezone.utc),
        )

    def stop(self) -> None:
        """Stop the process-local scheduler."""
        scheduler = self._scheduler
        if scheduler is None:
            return
        scheduler.shutdown(wait=False)
        self._scheduler = None
        logger.info("companion_dreaming_scheduler stopped")

    async def run_once(self) -> None:
        """Scan transcript scopes and process due sleeping-state dreams."""
        scopes = await self._transcript_scopes()
        logger.debug("companion_dreaming_scheduler scan scopes={}", len(scopes))
        for scope in scopes:
            try:
                await self._run_scope(scope)
            except Exception:
                logger.exception(
                    "companion_dreaming_scheduler scope_failed scope={}",
                    scope.lock_key,
                )

    async def _transcript_scopes(self) -> list[DreamingScope]:
        stmt = (
            select(
                CompanionMemoryDocumentVersion.user_id,
                CompanionMemoryDocumentVersion.companion_id,
                CompanionMemoryDocumentVersion.chat_id,
            )
            .where(
                CompanionMemoryDocumentVersion.document_kind == "transcript"
            )
            .distinct()
            .order_by(
                CompanionMemoryDocumentVersion.user_id,
                CompanionMemoryDocumentVersion.companion_id,
                CompanionMemoryDocumentVersion.chat_id,
            )
        )
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(stmt)).all()
        return [
            DreamingScope(
                user_id=str(user_id),
                companion_id=str(companion_id),
                chat_id=str(chat_id),
            )
            for user_id, companion_id, chat_id in rows
        ]

    async def _run_scope(self, scope: DreamingScope) -> None:
        async with AsyncSessionLocal() as db:
            if not await _try_advisory_lock(db, scope.lock_key):
                return
            try:
                user = await db.scalar(
                    select(User).where(User.id == scope.user_id)
                )
                if user is None:
                    return
                subscription = (
                    await subscription_service.get_user_current_subscription(
                        db, scope.user_id
                    )
                )
                model = select_chat_model(
                    user=user, is_subscribed=bool(subscription)
                )
                idle_seconds = (
                    global_config_loaded_from_config_yaml.app.features.companion_harness.dreaming_idle_seconds
                )
                processed = await asyncio.to_thread(
                    companion_chat_service.run_companion_dreaming_for_api,
                    user_id=scope.user_id,
                    agent_id=scope.companion_id,
                    chat_id=scope.chat_id,
                    resolved_chat_model=model,
                    dreaming_idle_seconds=idle_seconds,
                )
                if processed:
                    logger.info(
                        "companion_dreaming_scheduler processed scope={}",
                        scope.lock_key,
                    )
            finally:
                await _advisory_unlock(db, scope.lock_key)


async def _try_advisory_lock(db: object, lock_key: str) -> bool:
    result = await db.execute(
        text("SELECT pg_try_advisory_lock(hashtextextended(:lock_key, 0))"),
        {"lock_key": lock_key},
    )
    return bool(result.scalar())


async def _advisory_unlock(db: object, lock_key: str) -> None:
    await db.execute(
        text("SELECT pg_advisory_unlock(hashtextextended(:lock_key, 0))"),
        {"lock_key": lock_key},
    )


companion_dreaming_scheduler = CompanionDreamingScheduler()
