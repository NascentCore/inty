"""SimRunLoop: orchestrates GrillDirector, SimSession, and transport."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Generator, TextIO

from tools.inty_v2_repl.backend_chat_ws import BackendChatWsBridge, http_base_to_ws_chat_url
from tools.inty_v2_repl.sim_transport import (
    DEFAULT_USER_ID,
    TURN_REPLY_TIMEOUT_SEC,
    drain_until_quiet,
    ensure_import_path,
    query_bootstrap_complete,
    send_and_drain,
    target_presets,
    wait_implicit_sign_on_greeting,
    wait_downlink,
    RegressionTarget,
)
from tools.inty_user_sim.director import GrillDirector
from tools.inty_user_sim.report import build_report, infra_exit_code, write_report
from tools.inty_user_sim.run_store import SimRunStore
from tools.inty_user_sim.types import (
    GrillObjective,
    GrillPhase,
    SimCalendar,
    SimRunCheckpoint,
    SimTurnRecord,
    UserPersona,
    WallClockGapPolicy,
    persona_hash,
)
from tools.inty_user_sim.user_agent import UserAgent

SIM_TAG = "[inty-user-sim]"
SESSION_TURNS_BUDGET = 3
PROACTIVE_WAIT_SEC = 25.0


@dataclass
class SimRunConfig:
    """Immutable config for one sim run."""

    repo_root: Path
    target: RegressionTarget
    agent_id: str
    persona: UserPersona
    sim_days: int
    minutes_per_sim_day: float
    director_seed: int
    user_agent_model: str
    bearer_token: str
    resume: bool
    wall_gap: WallClockGapPolicy


@contextmanager
def sim_session(
    bridge: BackendChatWsBridge,
    *,
    agent_id: str,
    wait_greeting: bool,
) -> Generator[None, None, None]:
    """One WS connect cycle with signed_on/out semantics."""
    bridge.start()
    try:
        if wait_greeting:
            wait_implicit_sign_on_greeting(bridge, timeout_sec=120.0)
        yield
    finally:
        bridge.stop()


class SimRunLoop:
    """Main longitudinal sim orchestrator."""

    def __init__(
        self,
        config: SimRunConfig,
        user_agent: UserAgent,
        stderr: TextIO,
    ) -> None:
        self._config = config
        self._user_agent = user_agent
        self._stderr = stderr
        preset = target_presets(config.target, config.repo_root)
        self._preset = preset
        self._config_path = config.repo_root / preset.config_path
        self._run_id = str(uuid.uuid4())
        self._store = SimRunStore(self._run_id, config.repo_root / "tmp")
        self._t0 = time.monotonic()
        self._transcript: list[tuple[str, str]] = []
        self._proactive_visible = 0

    def run(self) -> int:
        """Execute the sim loop; return CLI exit code."""
        cfg = self._config
        ensure_import_path(cfg.repo_root)
        ws_url = http_base_to_ws_chat_url(
            self._preset.api_base,
            agent_id=cfg.agent_id,
        )
        bridge = BackendChatWsBridge(
            ws_url,
            bearer_token=cfg.bearer_token,
        )
        calendar = SimCalendar(
            sim_start=date.today(),
            sim_now=date.today(),
            minutes_per_sim_day=cfg.minutes_per_sim_day,
            iana_timezone="Asia/Shanghai",
        )
        checkpoint = self._load_or_init_checkpoint(cfg)
        director = GrillDirector(
            phase=checkpoint.phase,
            director_seed=cfg.director_seed,
            sim_days=cfg.sim_days,
            rupture_sent=checkpoint.rupture_sent,
            absence_done_days=list(checkpoint.absence_done_days),
        )
        from datetime import timedelta

        start_day = checkpoint.sim_day
        for day_offset in range(start_day, cfg.sim_days):
            calendar.sim_now = calendar.sim_start + timedelta(days=day_offset)
            sim_day = day_offset
            wait_greeting = day_offset == start_day and checkpoint.turn_count == 0
            with sim_session(bridge, agent_id=cfg.agent_id, wait_greeting=wait_greeting):
                turns_this_session = 0
                while turns_this_session < SESSION_TURNS_BUDGET:
                    bootstrap_complete = query_bootstrap_complete(
                        cfg.repo_root,
                        self._config_path,
                        user_id=DEFAULT_USER_ID,
                        agent_id=cfg.agent_id,
                    ) or self._preset.skip_db_checks
                    directive = director.next_directive(
                        sim_day,
                        checkpoint,
                        bootstrap_complete=bootstrap_complete,
                    )
                    if directive.phase == GrillPhase.DONE:
                        break
                    if directive.objective == GrillObjective.WAIT_PROACTIVE:
                        text, meta, err = wait_downlink(
                            bridge,
                            timeout_sec=PROACTIVE_WAIT_SEC,
                            label="proactive",
                        )
                        if text:
                            self._proactive_visible += 1
                            self._transcript.append(("assistant", text))
                        record = SimTurnRecord(
                            sim_day=sim_day,
                            phase=directive.phase,
                            objective=directive.objective,
                            user_text="",
                            assistant_text=text,
                            user_msg_uuid="",
                            langsmith_trace_id=str(meta.get("langsmith_trace_id") or "") or None,
                            input_queue_status="",
                            memdoc_user_seq=None,
                        )
                        self._store.append(record)
                        if directive.phase == GrillPhase.ABSENCE:
                            break
                        turns_this_session += 1
                        continue
                    last_assistant = self._last_assistant_text()
                    user_text = self._user_agent.compose_turn(
                        cfg.persona,
                        directive.objective,
                        self._transcript,
                        last_assistant,
                    )
                    result = send_and_drain(
                        bridge,
                        cfg.repo_root,
                        self._config_path,
                        agent_id=cfg.agent_id,
                        user_id=DEFAULT_USER_ID,
                        text=user_text,
                        label=f"sim-day-{sim_day}-{directive.objective.value}",
                        stderr=self._stderr,
                        skip_db_checks=self._preset.skip_db_checks,
                        user_time_context=calendar.to_user_time_context(),
                        turn_timeout_sec=TURN_REPLY_TIMEOUT_SEC,
                    )
                    if result.error is not None:
                        print(
                            f"{SIM_TAG} ERROR turn failed: {result.error}",
                            file=self._stderr,
                            flush=True,
                        )
                        return 2
                    self._transcript.append(("user", user_text))
                    if result.assistant_text:
                        self._transcript.append(("assistant", result.assistant_text))
                    record = SimTurnRecord(
                        sim_day=sim_day,
                        phase=directive.phase,
                        objective=directive.objective,
                        user_text=user_text,
                        assistant_text=result.assistant_text,
                        user_msg_uuid=result.user_msg_uuid,
                        langsmith_trace_id=str(result.meta.get("langsmith_trace_id") or "") or None,
                        input_queue_status=result.input_queue_status,
                        memdoc_user_seq=result.memdoc_user_seq,
                    )
                    self._store.append(record)
                    checkpoint.turn_count += 1
                    if directive.objective in (
                        GrillObjective.BOOTSTRAP_IDENTITY,
                        GrillObjective.BOOTSTRAP_RELATIONSHIP,
                        GrillObjective.BOOTSTRAP_EXPERIENCE_PROFILE,
                    ):
                        checkpoint.director_cursor += 1
                    turns_this_session += 1
                    if directive.phase == GrillPhase.ABSENCE:
                        break
                    drain_until_quiet(
                        bridge,
                        quiet_sec=2.0,
                        max_sec=10.0,
                    )
            if director.phase == GrillPhase.ABSENCE:
                gap_days = cfg.wall_gap.sample_gap_sim_days(cfg.director_seed + sim_day)
                print(
                    f"{SIM_TAG} absence wall-sleep sim_days={gap_days}",
                    flush=True,
                )
                cfg.wall_gap.sleep_for_gap(gap_days)
                calendar.advance_sim_days(gap_days)
                director.mark_absence_done(sim_day)
                director.phase = GrillPhase.RETURN_VISIT
            checkpoint.sim_day = day_offset + 1
            checkpoint.phase = director.phase
            rupture_sent, absence_days = director.to_checkpoint_fields()
            checkpoint.rupture_sent = rupture_sent
            checkpoint.absence_done_days = absence_days
            self._store.write_checkpoint(checkpoint)
            wall_sleep = cfg.minutes_per_sim_day * 60.0 / max(SESSION_TURNS_BUDGET, 1)
            if wall_sleep > 0 and director.phase != GrillPhase.ABSENCE:
                time.sleep(min(wall_sleep, 30.0))
        director.phase = GrillPhase.DONE
        checkpoint.phase = GrillPhase.DONE
        self._store.write_checkpoint(checkpoint)
        turns = self._store.load_turns()
        report = build_report(
            repo_root=cfg.repo_root,
            config_path=self._config_path,
            agent_id=cfg.agent_id,
            user_id=DEFAULT_USER_ID,
            turns=turns,
            persona_hash=persona_hash(cfg.persona),
            director_seed=cfg.director_seed,
            user_agent_model=cfg.user_agent_model,
            sim_days=cfg.sim_days,
            wall_clock_sec=time.monotonic() - self._t0,
            checkpoint_written=True,
            skip_db_checks=self._preset.skip_db_checks,
        )
        report_path = cfg.repo_root / "tmp" / f"user-sim-{cfg.agent_id}.json"
        write_report(report_path, report)
        print(f"{SIM_TAG} report={report_path}", flush=True)
        return infra_exit_code(report)

    def _load_or_init_checkpoint(self, cfg: SimRunConfig) -> SimRunCheckpoint:
        if cfg.resume:
            loaded = self._store.load_checkpoint()
            if loaded is not None:
                return loaded
        return SimRunCheckpoint(
            run_id=self._run_id,
            agent_id=cfg.agent_id,
            sim_day=0,
            phase=GrillPhase.BOOTSTRAP,
            director_cursor=0,
            director_seed=cfg.director_seed,
            persona_hash=persona_hash(cfg.persona),
            turn_count=0,
            rupture_sent=False,
            absence_done_days=[],
        )

    def _last_assistant_text(self) -> str | None:
        for role, text in reversed(self._transcript):
            if role == "assistant":
                return text
        return None
