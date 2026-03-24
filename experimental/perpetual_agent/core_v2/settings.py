from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CompanionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COMPANION_",
        extra="ignore",
    )

    database_path: str = Field(
        default="experimental/perpetual_agent/core_v2/companion.sqlite3"
    )
    telegram_bot_token: str = ""
    telegram_poll_timeout_seconds: int = 20
    inbound_idle_sleep_seconds: float = 1.0
    scheduler_idle_sleep_seconds: float = 1.0
    scheduler_batch_size: int = 50
    scheduler_lookahead_seconds: int = 0
    retry_max_attempts: int = 3
    retry_base_delay_seconds: float = 0.25
    lease_ttl_seconds: int = 45
    lease_key_telegram_inbound: str = "telegram_inbound_consumer"
    cursor_key_telegram_update: str = "telegram_last_applied_update_id"
    planner_followup_delay_minutes: int = 1440
    quiet_hours_start_hour_local: int = 23
    quiet_hours_end_hour_local: int = 8
    safety_per_channel_daily_limit: int = 5
    scheduler_default_telegram_chat_id: str = ""
    scheduler_default_sms_recipient: str = "unknown"


@lru_cache(maxsize=1)
def get_settings() -> CompanionSettings:
    load_dotenv()
    return CompanionSettings()
