from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ..adapters.sms_adapter import SmsAdapter
from ..adapters.telegram_adapter import TelegramInboundEnvelope
from ..contracts import ChannelType, EventDirection, InteractionEvent
from ..repositories.cursor_repo import CursorRepository
from ..repositories.events_repo import EventsRepository
from ..repositories.memory_repo import MemoryRepository
from ..repositories.plan_repo import PlanRepository
from ..services import (
    memory_service,
    planner_service,
    reply_service,
    safety_policy,
)
from ..services.identity_resolver import resolve_user_id


@dataclass(frozen=True)
class ProcessResult:
    processed: bool
    should_advance_cursor: bool
    reason: str
    event_id: str | None = None


class Orchestrator:
    def __init__(
        self,
        *,
        events_repo: EventsRepository,
        memory_repo: MemoryRepository,
        plan_repo: PlanRepository,
        cursor_repo: CursorRepository,
        sms_adapter: SmsAdapter,
        telegram_send_func,
        planner_followup_delay_minutes: int,
        quiet_hours_start_hour_local: int,
        quiet_hours_end_hour_local: int,
        scheduler_default_telegram_chat_id: str,
        scheduler_default_sms_recipient: str,
    ) -> None:
        self._events_repo = events_repo
        self._memory_repo = memory_repo
        self._plan_repo = plan_repo
        self._cursor_repo = cursor_repo
        self._sms_adapter = sms_adapter
        self._telegram_send_func = telegram_send_func
        self._planner_followup_delay_minutes = planner_followup_delay_minutes
        self._quiet_hours_start_hour_local = quiet_hours_start_hour_local
        self._quiet_hours_end_hour_local = quiet_hours_end_hour_local
        self._scheduler_default_telegram_chat_id = (
            scheduler_default_telegram_chat_id
        )
        self._scheduler_default_sms_recipient = scheduler_default_sms_recipient

    def process_inbound_telegram(
        self,
        *,
        envelope: TelegramInboundEnvelope,
    ) -> ProcessResult:
        user_id = resolve_user_id(
            channel=ChannelType.TELEGRAM,
            channel_user_id=envelope.chat_id,
        )
        inbound_event = InteractionEvent(
            event_id=f"telegram_update_{envelope.update_id}",
            user_id=user_id,
            channel=ChannelType.TELEGRAM,
            direction=EventDirection.INBOUND,
            content=envelope.text,
            timestamp=self._resolve_timestamp(envelope=envelope),
            channel_message_id=str(envelope.update_id),
            metadata={
                "chat_id": envelope.chat_id,
                "update_id": envelope.update_id,
            },
        )
        inserted = self._events_repo.save_event_idempotent(inbound_event)
        if not inserted:
            return ProcessResult(
                processed=False,
                should_advance_cursor=True,
                reason="duplicate_inbound",
                event_id=inbound_event.event_id,
            )

        now = datetime.now(timezone.utc)
        candidate_memory_item = (
            memory_service.build_preference_memory_from_event(
                user_id=user_id,
                event_id=inbound_event.event_id,
                event_content=inbound_event.content,
                now=now,
            )
        )
        preferred_channel = (
            planner_service.pick_preferred_channel_from_memories(
                self._memory_repo.list_memories_by_user(
                    user_id=user_id, limit=20
                )
            )
        )
        if (
            candidate_memory_item is not None
            and candidate_memory_item.key == "preferred_channel"
        ):
            if candidate_memory_item.value == ChannelType.SMS.value:
                preferred_channel = ChannelType.SMS
            if candidate_memory_item.value == ChannelType.TELEGRAM.value:
                preferred_channel = ChannelType.TELEGRAM
        followup_action = planner_service.build_followup_action(
            user_id=user_id,
            trigger_event_id=inbound_event.event_id,
            now=now,
            followup_delay_minutes=self._planner_followup_delay_minutes,
            preferred_channel_from_memory=preferred_channel,
        )

        reply_text = reply_service.compose_reactive_reply(
            channel=ChannelType.TELEGRAM,
            inbound_content=inbound_event.content,
        )
        try:
            self._telegram_send_func(chat_id=envelope.chat_id, text=reply_text)
        except Exception:
            # 保证“处理失败不推进 cursor”：删除本轮入站事件，允许后续重试完整链路。
            self._events_repo.delete_event(event_id=inbound_event.event_id)
            raise

        if candidate_memory_item is not None:
            self._memory_repo.upsert_memory(candidate_memory_item)
        self._plan_repo.save_action_idempotent(followup_action)

        outbound_event = InteractionEvent(
            event_id=f"{inbound_event.event_id}_reply",
            user_id=user_id,
            channel=ChannelType.TELEGRAM,
            direction=EventDirection.OUTBOUND,
            content=reply_text,
            timestamp=datetime.now(timezone.utc),
            channel_message_id=None,
            metadata={
                "reply_to_event_id": inbound_event.event_id,
                "chat_id": envelope.chat_id,
            },
        )
        self._events_repo.save_event_idempotent(outbound_event)
        return ProcessResult(
            processed=True,
            should_advance_cursor=True,
            reason="ok",
            event_id=inbound_event.event_id,
        )

    def run_scheduler_once(self, *, now: datetime) -> int:
        due_actions = self._plan_repo.list_due_actions(
            now=now,
            limit=50,
        )
        executed = 0
        for action in due_actions:
            claimed = self._plan_repo.claim_action_running(
                action_id=action.action_id
            )
            if not claimed:
                continue
            is_quiet = safety_policy.is_quiet_hours(
                now_local=now.astimezone(),
                start_hour_local=self._quiet_hours_start_hour_local,
                end_hour_local=self._quiet_hours_end_hour_local,
            )
            if is_quiet and not safety_policy.allow_send_in_quiet_hours(
                channel=action.preferred_channel
            ):
                self._plan_repo.mark_failed(action_id=action.action_id)
                continue

            content = reply_service.compose_followup_reply(
                channel=action.preferred_channel,
                user_id=action.user_id,
            )
            outbound_event = InteractionEvent(
                event_id=f"action_{action.action_id}_result",
                user_id=action.user_id,
                channel=action.preferred_channel,
                direction=EventDirection.OUTBOUND,
                content=content,
                timestamp=now,
                channel_message_id=None,
                metadata={"action_id": action.action_id},
            )
            try:
                already_dispatched = self._events_repo.event_exists(
                    outbound_event.event_id
                )
                if not already_dispatched:
                    self._dispatch_scheduled_message(
                        channel=action.preferred_channel,
                        content=content,
                    )
                    self._events_repo.save_event_idempotent(outbound_event)
                self._plan_repo.mark_done(
                    action_id=action.action_id,
                    result_event_id=outbound_event.event_id,
                )
                executed += 1
            except Exception:
                self._plan_repo.mark_failed(action_id=action.action_id)
                raise
        return executed

    def get_last_applied_update_id(self, *, cursor_key: str) -> int | None:
        value = self._cursor_repo.get_cursor(cursor_key=cursor_key)
        if value is None:
            return None
        return int(value)

    def advance_applied_update_id(
        self, *, cursor_key: str, update_id: int
    ) -> None:
        self._cursor_repo.set_cursor(
            cursor_key=cursor_key,
            cursor_value=str(update_id),
        )

    def _dispatch_scheduled_message(
        self, *, channel: ChannelType, content: str
    ) -> None:
        if channel is ChannelType.TELEGRAM:
            chat_id = self._scheduler_default_telegram_chat_id.strip()
            if not chat_id:
                raise ValueError(
                    "COMPANION_SCHEDULER_DEFAULT_TELEGRAM_CHAT_ID is required for telegram scheduler dispatch"
                )
            self._telegram_send_func(chat_id=chat_id, text=content)
            return
        if channel is ChannelType.SMS:
            recipient = self._scheduler_default_sms_recipient.strip()
            self._sms_adapter.send_text(recipient=recipient, text=content)
            return
        raise ValueError("voice_call dispatch not implemented in M0/M1")

    @staticmethod
    def _resolve_timestamp(*, envelope: TelegramInboundEnvelope) -> datetime:
        if envelope.message_date_unix is None:
            return datetime.now(timezone.utc)
        return datetime.fromtimestamp(
            envelope.message_date_unix,
            tz=timezone.utc,
        )
