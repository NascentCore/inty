from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.external_services.telegram_bot import TelegramBotProvisionResult


@dataclass
class FakeTelegramBotService:
    bot_id: int = 1000001
    bot_username: str = "inty_test_bot"

    def provision_agent_bot(
        self,
        *,
        agent_id: str,
    ) -> TelegramBotProvisionResult:
        start_parameter = f"agent_{agent_id}"
        deep_link = f"https://t.me/{self.bot_username}?start={start_parameter}"
        return TelegramBotProvisionResult(
            bot_id=self.bot_id,
            bot_username=self.bot_username,
            start_parameter=start_parameter,
            deep_link=deep_link,
            provisioned_at=datetime.now(timezone.utc).isoformat(),
        )
