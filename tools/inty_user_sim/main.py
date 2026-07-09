"""CLI entry for long-term synthetic user simulator."""

from __future__ import annotations

import sys
from pathlib import Path

from cyclopts import App, Parameter
from typing import Annotated

from tools.inty_v2_repl.sim_transport import (
    RegressionTarget,
    ensure_import_path,
    find_repo_root,
    read_bearer,
    target_presets,
)
from tools.inty_user_sim.run_loop import SimRunConfig, SimRunLoop
from tools.inty_user_sim.types import (
    UserPersona,
    WallClockGapPolicy,
    load_persona_yaml,
)
from tools.inty_user_sim.user_agent import UserAgent

app = App(name="inty-user-sim", help="Long-term synthetic user simulator for companion grill.")


@app.command
def run(
    target: Annotated[
        RegressionTarget,
        Parameter(help="Deployment target preset (local/dev/prod)"),
    ],
    agent_id: Annotated[str, Parameter(help="Companion agent id")] = "",
    sim_days: Annotated[int, Parameter(help="Simulated calendar days")] = 14,
    minutes_per_sim_day: Annotated[
        float, Parameter(help="Wall-clock minutes per sim day")
    ] = 5.0,
    persona_file: Annotated[
        Path, Parameter(help="YAML UserPersona file")
    ] = Path("tools/inty_user_sim/personas/default_zh.yaml"),
    user_agent_model: Annotated[
        str, Parameter(help="OpenAI-compatible model for synthetic user")
    ] = "gpt-4o-mini",
    director_seed: Annotated[int, Parameter(help="Deterministic director seed")] = 42,
    token_file: Annotated[
        str, Parameter(help="Bearer token file path")
    ] = ".inty_ops_bearer_token",
    create_agent: Annotated[
        bool, Parameter(help="Create fresh bootstrap-test agent")
    ] = False,
    resume: Annotated[bool, Parameter(help="Resume from checkpoint if present")] = False,
    absence_wall_sec_per_sim_day: Annotated[
        float, Parameter(help="Wall seconds per sim-day during absence")
    ] = 30.0,
) -> None:
    """Run a longitudinal synthetic user sim over app-ws."""
    repo_root = find_repo_root()
    ensure_import_path(repo_root)
    preset = target_presets(target, repo_root)
    stderr = sys.stderr
    resolved_agent_id = agent_id.strip()
    if create_agent:
        from tools.inty_user_sim.agent_create import create_bootstrap_agent_id

        resolved_agent_id = create_bootstrap_agent_id(
            repo_root=repo_root,
            api_base=preset.api_base,
            token_path=token_file,
            stderr=stderr,
        )
    assert resolved_agent_id != "", "agent_id required (or pass --create-agent)"
    persona = load_persona_yaml(
        persona_file if persona_file.is_absolute() else repo_root / persona_file
    )
    bearer = read_bearer(repo_root, token_file)
    config = SimRunConfig(
        repo_root=repo_root,
        target=target,
        agent_id=resolved_agent_id,
        persona=persona,
        sim_days=sim_days,
        minutes_per_sim_day=minutes_per_sim_day,
        director_seed=director_seed,
        user_agent_model=user_agent_model,
        bearer_token=bearer,
        resume=resume,
        wall_gap=WallClockGapPolicy(
            absence_sim_days_min=3,
            absence_sim_days_max=7,
            wall_seconds_per_sim_day=absence_wall_sec_per_sim_day,
        ),
    )
    user_agent = UserAgent.from_env(user_agent_model)
    loop = SimRunLoop(config, user_agent, stderr)
    raise SystemExit(loop.run())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
