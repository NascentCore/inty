"""GrillDirector: schedules longitudinal probe objectives across sim days."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from tools.inty_user_sim.types import (
    GrillDirective,
    GrillObjective,
    GrillPhase,
    SimRunCheckpoint,
)


BOOTSTRAP_OBJECTIVES: tuple[GrillObjective, ...] = (
    GrillObjective.BOOTSTRAP_IDENTITY,
    GrillObjective.BOOTSTRAP_RELATIONSHIP,
    GrillObjective.BOOTSTRAP_EXPERIENCE_PROFILE,
    GrillObjective.BOOTSTRAP_FINISH,
)


def absence_schedule(sim_days: int) -> set[int]:
    """Sim days that trigger absence phases."""
    if sim_days < 7:
        return set()
    points = [7, 28, 56]
    return {d for d in points if d < sim_days}


def rupture_schedule(sim_days: int) -> set[int]:
    points = [14, 42]
    return {d for d in points if d < sim_days}


def depth_schedule(sim_days: int) -> set[int]:
    points = [21, 63]
    return {d for d in points if d < sim_days}


@dataclass
class GrillDirector:
    """State machine emitting GrillDirective per sim step."""

    phase: GrillPhase
    director_seed: int
    sim_days: int
    rupture_sent: bool = False
    absence_done_days: list[int] = field(default_factory=list)
    depth_done_days: list[int] = field(default_factory=list)

    def next_directive(
        self,
        sim_day: int,
        checkpoint: SimRunCheckpoint,
        *,
        bootstrap_complete: bool,
    ) -> GrillDirective:
        """Return the next phase/objective pair."""
        match self.phase:
            case GrillPhase.BOOTSTRAP:
                if not bootstrap_complete:
                    idx = min(checkpoint.director_cursor, len(BOOTSTRAP_OBJECTIVES) - 1)
                    return GrillDirective(
                        phase=GrillPhase.BOOTSTRAP,
                        objective=BOOTSTRAP_OBJECTIVES[idx],
                    )
                self.phase = GrillPhase.DAILY_CHAT
                return GrillDirective(
                    phase=GrillPhase.DAILY_CHAT,
                    objective=GrillObjective.CASUAL_CHAT,
                )
            case GrillPhase.DAILY_CHAT:
                if (
                    sim_day in absence_schedule(self.sim_days)
                    and sim_day not in self.absence_done_days
                ):
                    self.phase = GrillPhase.ABSENCE
                    return GrillDirective(
                        phase=GrillPhase.ABSENCE,
                        objective=GrillObjective.WAIT_PROACTIVE,
                    )
                if sim_day in rupture_schedule(self.sim_days):
                    if not self.rupture_sent:
                        self.rupture_sent = True
                        return GrillDirective(
                            phase=GrillPhase.RUPTURE,
                            objective=GrillObjective.RUPTURE,
                        )
                    return GrillDirective(
                        phase=GrillPhase.REPAIR,
                        objective=GrillObjective.REPAIR,
                    )
                if (
                    sim_day in depth_schedule(self.sim_days)
                    and sim_day not in self.depth_done_days
                ):
                    self.depth_done_days.append(sim_day)
                    return GrillDirective(
                        phase=GrillPhase.DEEP_DISCLOSURE,
                        objective=GrillObjective.DEEP_DISCLOSURE,
                    )
                rng = random.Random(self.director_seed + sim_day)
                objective = rng.choice(
                    [
                        GrillObjective.CASUAL_CHAT,
                        GrillObjective.RECALL_PAST,
                        GrillObjective.MISSED_BID,
                        GrillObjective.COMPLAINT,
                    ]
                )
                return GrillDirective(
                    phase=GrillPhase.DAILY_CHAT,
                    objective=objective,
                )
            case GrillPhase.ABSENCE:
                return GrillDirective(
                    phase=GrillPhase.ABSENCE,
                    objective=GrillObjective.WAIT_PROACTIVE,
                )
            case GrillPhase.RETURN_VISIT:
                self.phase = GrillPhase.DAILY_CHAT
                return GrillDirective(
                    phase=GrillPhase.RETURN_VISIT,
                    objective=GrillObjective.RETURN_AFTER_ABSENCE,
                )
            case GrillPhase.RUPTURE:
                self.phase = GrillPhase.DAILY_CHAT
                return GrillDirective(
                    phase=GrillPhase.REPAIR,
                    objective=GrillObjective.REPAIR,
                )
            case GrillPhase.REPAIR:
                self.phase = GrillPhase.DAILY_CHAT
                return GrillDirective(
                    phase=GrillPhase.REPAIR,
                    objective=GrillObjective.REPAIR,
                )
            case GrillPhase.DEEP_DISCLOSURE:
                self.phase = GrillPhase.DAILY_CHAT
                return GrillDirective(
                    phase=GrillPhase.DAILY_CHAT,
                    objective=GrillObjective.CASUAL_CHAT,
                )
            case GrillPhase.DONE:
                return GrillDirective(
                    phase=GrillPhase.DONE,
                    objective=GrillObjective.CASUAL_CHAT,
                )

    def mark_absence_done(self, sim_day: int) -> None:
        if sim_day not in self.absence_done_days:
            self.absence_done_days.append(sim_day)

    def to_checkpoint_fields(self) -> tuple[bool, list[int]]:
        return self.rupture_sent, list(self.absence_done_days)
