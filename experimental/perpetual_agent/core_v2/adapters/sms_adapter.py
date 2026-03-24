from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SmsAdapter:
    """M1/M0 阶段的最小 SMS 发送器（可替换为 Twilio 实现）。"""

    sent_messages: list[dict[str, str]]

    @classmethod
    def create_default(cls) -> "SmsAdapter":
        return cls(sent_messages=[])

    def send_text(self, *, recipient: str, text: str) -> dict[str, str]:
        payload = {"recipient": recipient, "text": text}
        self.sent_messages.append(payload)
        logger.info("sms_adapter send recipient=%s", recipient)
        return payload
