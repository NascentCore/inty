"""Immutable value types for the long-term user simulator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, Field

from app.schemas.chat import UserTimeContext


class GrillPhase(StrEnum):
    """Director state-machine phase for one longitudinal sim run."""

    BOOTSTRAP = "bootstrap"
    DAILY_CHAT = "daily_chat"
    ABSENCE = "absence"
    RETURN_VISIT = "return_visit"
    RUPTURE = "rupture"
    REPAIR = "repair"
    DEEP_DISCLOSURE = "deep_disclosure"
    DONE = "done"


class GrillObjective(StrEnum):
    """Per-turn probe intent passed to UserAgent."""

    BOOTSTRAP_IDENTITY = "bootstrap_identity"
    BOOTSTRAP_RELATIONSHIP = "bootstrap_relationship"
    BOOTSTRAP_EXPERIENCE_PROFILE = "bootstrap_experience_profile"
    BOOTSTRAP_FINISH = "bootstrap_finish"
    CASUAL_CHAT = "casual_chat"
    RECALL_PAST = "recall_past"
    MISSED_BID = "missed_bid"
    RUPTURE = "rupture"
    REPAIR = "repair"
    BOUNDARY = "boundary"
    COMPLAINT = "complaint"
    DEEP_DISCLOSURE = "deep_disclosure"
    RETURN_AFTER_ABSENCE = "return_after_absence"
    WAIT_PROACTIVE = "wait_proactive"


class AttachmentStyle(StrEnum):
    """Synthetic user attachment flavor for UserAgent prompt (not a clinical scale)."""

    SECURE = "secure"
    ANXIOUS = "anxious"
    AVOIDANT = "avoidant"


class DisclosurePace(StrEnum):
    """How fast the synthetic user deepens self-disclosure."""

    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class GrillSensitivity(StrEnum):
    """How adversarial rupture turns should be."""

    GENTLE = "gentle"
    STANDARD = "standard"
    ADVERSARIAL = "adversarial"


@dataclass(frozen=True)
class GrillDirective:
    """``GrillDirector.next()`` output: phase plus objective."""

    phase: GrillPhase
    objective: GrillObjective


class UserPersona(BaseModel):
    """Frozen synthetic human profile for the whole sim bond."""

    display_name: str = Field(description="User self-name written into USER.md during bootstrap")
    assistant_name: str = Field(description="Desired companion name")
    language: str = Field(description="Primary chat language code, e.g. zh")
    attachment_style: AttachmentStyle = Field(description="UserAgent tone modulation")
    disclosure_pace: DisclosurePace = Field(description="Social penetration pacing")
    grill_sensitivity: GrillSensitivity = Field(description="Rupture intensity")
    backstory_seed: str = Field(description="1-3 sentence life background seed")
    relationship_preference: str = Field(
        description="Bootstrap relationship preference, e.g. emotional_companion"
    )


def load_persona_yaml(path: Path) -> UserPersona:
    """Load and validate a persona YAML file."""
    assert path.is_file()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return UserPersona.model_validate(raw)


def persona_hash(persona: UserPersona) -> str:
    """Stable hash for report reproducibility."""
    payload = persona.model_dump_json()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class SimCalendar:
    """Simulated calendar mapped to injectable UserTimeContext."""

    sim_start: date
    sim_now: date
    minutes_per_sim_day: float
    iana_timezone: str

    def advance_sim_days(self, days: int) -> None:
        assert days > 0
        from datetime import timedelta

        self.sim_now = self.sim_now + timedelta(days=days)

    def sim_day_index(self) -> int:
        return (self.sim_now - self.sim_start).days

    def to_user_time_context(self) -> UserTimeContext:
        """Build UserTimeContext at noon local on sim_now."""
        tz = ZoneInfo(self.iana_timezone)
        local_dt = datetime.combine(self.sim_now, time(12, 0), tzinfo=tz)
        off = local_dt.utcoffset()
        utc_mins = int(off.total_seconds() // 60) if off is not None else None
        return UserTimeContext(
            local_time=local_dt.isoformat(timespec="milliseconds"),
            timezone=self.iana_timezone,
            utc_offset_minutes=utc_mins,
        )


@dataclass
class WallClockGapPolicy:
    """Real wall-clock wait during absence phases."""

    absence_sim_days_min: int
    absence_sim_days_max: int
    wall_seconds_per_sim_day: float

    def sample_gap_sim_days(self, seed: int) -> int:
        span = self.absence_sim_days_max - self.absence_sim_days_min + 1
        return self.absence_sim_days_min + (seed % span)

    def sleep_for_gap(self, sim_days: int) -> None:
        import time

        seconds = self.wall_seconds_per_sim_day * float(sim_days)
        if seconds > 0.0:
            time.sleep(seconds)


@dataclass(frozen=True)
class SimTurnRecord:
    """One observed turn appended to the JSONL run log."""

    sim_day: int
    phase: GrillPhase
    objective: GrillObjective
    user_text: str
    assistant_text: str | None
    user_msg_uuid: str
    langsmith_trace_id: str | None
    input_queue_status: str
    memdoc_user_seq: int | None


class SimRunCheckpoint(BaseModel):
    """Resume checkpoint written under tmp/."""

    run_id: str = Field(description="Unique run identifier")
    agent_id: str = Field(description="Companion agent id")
    sim_day: int = Field(description="Next sim day index to execute")
    phase: GrillPhase = Field(description="Director phase at checkpoint")
    director_cursor: int = Field(description="Bootstrap objective queue index")
    director_seed: int = Field(description="Deterministic director RNG seed")
    persona_hash: str = Field(description="Hash of UserPersona payload")
    turn_count: int = Field(description="User turns completed so far")
    rupture_sent: bool = Field(description="Whether rupture objective already fired")
    absence_done_days: list[int] = Field(
        description="Sim days where absence phase already completed"
    )


class InfraPassGate(BaseModel):
    """L0 infra bits for user sim CLI exit code."""

    bootstrap_complete: bool = Field(description="context.json bootstrap flag true")
    input_queue_delivered: bool = Field(description="No in-flight InputQueue rows")
    output_user_visible_delivered: bool = Field(description="User-visible OutputQueue delivered")
    checkpoint_written: bool = Field(description="Checkpoint file persisted")


class EvalTelemetry(BaseModel):
    """L1/L2 report-only grill signals."""

    gottman_repair_met: str = Field(description="pass/fail/skipped repair within 3 turns")
    social_penetration_depth_signals: list[str] = Field(
        description="Heuristic depth markers from transcript/MemDoc"
    )
    proactive_visible_rounds: int = Field(description="Visible proactive WS downlinks observed")
    dreaming_memory_updated: str = Field(description="pass/fail/skipped MEMORY.md consolidate")
    guardrail_sycophancy_flag: bool = Field(description="Heuristic over-agreement detected")


class SimRunMeta(BaseModel):
    """Run metadata for reproducibility and cost."""

    persona_hash: str = Field(description="UserPersona hash")
    director_seed: int = Field(description="Director RNG seed")
    user_agent_model: str = Field(description="LLM model id for UserAgent")
    sim_days: int = Field(description="Configured sim day budget")
    wall_clock_sec: float = Field(description="Total wall seconds elapsed")
    turn_count: int = Field(description="Completed user turns")


class SimReport(BaseModel):
    """Final JSON report for one sim run."""

    infra_gate: InfraPassGate = Field(description="L0 gate snapshot")
    eval: EvalTelemetry = Field(description="L1/L2 telemetry")
    run_meta: SimRunMeta = Field(description="Repro metadata")
    warnings: list[str] = Field(description="Human-review warnings")

    def to_json(self) -> str:
        return json.dumps(self.model_dump(), indent=2, ensure_ascii=False)
