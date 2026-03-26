"""
Agentic kernel heartbeat contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HeartbeatPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_interval_seconds: float = Field(gt=0)
    backoff_threshold: int = Field(ge=0)
    backoff_multiplier: float = Field(gt=1.0)
    max_interval_multiplier: float = Field(ge=1.0)
    max_consecutive_silent: int = Field(ge=0)


class HeartbeatState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_user_message_monotonic: float | None = None
    last_heartbeat_monotonic: float | None = None
    consecutive_silent_count: int = Field(default=0, ge=0)
    total_heartbeat_count: int = Field(default=0, ge=0)


class HeartbeatSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elapsed_since_user_seconds: float = Field(ge=0)
    current_time_utc_iso: str
    last_user_message_preview: str | None = None
