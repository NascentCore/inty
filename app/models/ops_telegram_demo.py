"""ORM for Ops Telegram channel shared-bot poll cursor (``ops_telegram_demo_poll_state``)."""

import sqlalchemy as sa
from sqlalchemy import BigInteger, Column, DateTime, Integer

from app.models.base import Base


class OpsTelegramDemoPollState(Base):
    """Singleton row holding last Telegram getUpdates offset for the shared bot."""

    __tablename__ = "ops_telegram_demo_poll_state"

    id = Column(Integer, primary_key=True, comment="Fixed row id=1")
    last_update_id = Column(
        BigInteger,
        nullable=True,
        comment="Next getUpdates offset (update_id + 1 from last processed)",
    )
