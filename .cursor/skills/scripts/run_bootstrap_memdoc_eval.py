#!/usr/bin/env python3
"""L1 Bootstrap MemDoc policy eval driver (#3606).

Report-only: always exit 0. Golden-fact chat recall matrix:
``awake_write`` vs ``dreaming_only_fast``. Requires Ops with
``INTY_CONFIG_YAML=devops/config.yaml.bootstrap_memdoc_eval.yaml``.

Generated entirely by Cursor agent for Bootstrap MemDoc eval slice.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SCENARIOS = (
    _REPO_ROOT / "contracts" / "bootstrap_memdoc_eval" / "scenarios.yaml"
)
_DEFAULT_CONFIG = _REPO_ROOT / "devops" / "config.yaml.bootstrap_memdoc_eval.yaml"
_TAG = "[bootstrap-memdoc-eval]"
_DEFAULT_API_BASE = "http://127.0.0.1:8001"
_DEFAULT_USER_ID = "user-testing"
_DEFAULT_TOKEN_FILE = ".inty_ops_bearer_token"
_BOOTSTRAP_FINISH_TURN = (
    "引导可以结束了。请把 USER、IDENTITY、STYLE 写好，然后调用 "
    "companion_bootstrap_user_interactive_complete 完成引导。"
)
_DREAMING_IDLE_SECONDS = 10

_POLICIES: tuple[str, ...] = (
    "awake_write",
    "dreaming_only",
)

_MATRIX_CELLS: tuple[tuple[str, int], ...] = (
    ("awake_write", _DREAMING_IDLE_SECONDS),
    ("dreaming_only", _DREAMING_IDLE_SECONDS),
)


def _matrix_label(policy: str) -> str:
    if policy == "dreaming_only":
        return "dreaming_only_fast"
    return policy


def _patch_eval_config_yaml(
    config_path: Path,
    *,
    policy: str,
) -> None:
    text = config_path.read_text(encoding="utf-8")
    text = re.sub(
        r"(?m)^(\s+dreaming_idle_seconds: )\d+\s*$",
        rf"\g<1>{_DREAMING_IDLE_SECONDS}",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^(\s+bootstrap_memdoc_policy: )[a-z_]+\s*$",
        rf"\g<1>{policy}",
        text,
        count=1,
    )
    config_path.write_text(text, encoding="utf-8")


def _stop_ops() -> None:
    subprocess.run(
        ["bash", "-c", "lsof -ti:8001 | xargs kill -9 2>/dev/null || true"],
        check=False,
    )
    time.sleep(2.0)


def _wait_ops_health(*, timeout_sec: float, stderr: TextIO) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"{_DEFAULT_API_BASE}/health",
                timeout=3.0,
            ) as response:
                if response.status == 200:
                    print(
                        f"{_TAG} Ops ready at {_DEFAULT_API_BASE}",
                        file=stderr,
                        flush=True,
                    )
                    return
        except Exception:
            time.sleep(2.0)
    raise RuntimeError(f"Ops not healthy within {timeout_sec}s")


def _restart_ops(repo_root: Path, stderr: TextIO) -> None:
    _stop_ops()
    env = {
        **os.environ,
        "INTY_CONFIG_YAML": "devops/config.yaml.bootstrap_memdoc_eval.yaml",
    }
    subprocess.Popen(
        ["./backend/ops/start.sh", "--local", "--no-build-frontend"],
        cwd=repo_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_ops_health(timeout_sec=180.0, stderr=stderr)


def _ensure_import_path(repo_root: Path) -> None:
    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_scenarios(path: Path) -> tuple[Any, ...]:
    _ensure_import_path(_REPO_ROOT)
    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        load_eval_scenarios,
    )

    return load_eval_scenarios(path)


def _plan_matrix(
    *,
    scenarios_path: Path,
    policy_filter: str,
) -> list[dict[str, Any]]:
    scenarios = _load_scenarios(scenarios_path)
    plan: list[dict[str, Any]] = []
    for scenario in scenarios:
        for matrix_policy, idle in _MATRIX_CELLS:
            if policy_filter != "all" and policy_filter != matrix_policy:
                continue
            plan.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "policy": matrix_policy,
                    "dreaming_idle_seconds": idle,
                    "label": _matrix_label(matrix_policy),
                }
            )
    return plan


def _load_regression_module(repo_root: Path) -> Any:
    regression_path = (
        repo_root / ".cursor" / "skills" / "scripts" / "run_inty_repl_regression.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_inty_repl_regression", regression_path
    )
    assert spec is not None and spec.loader is not None
    reg = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reg
    spec.loader.exec_module(reg)
    return reg


def _drive_user_turn(
    reg: Any,
    *,
    bridge: Any,
    report: dict[str, Any],
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    user_text: str,
    label: str,
    stderr: TextIO,
    timeout_sec: float,
    settle_trailing: bool,
) -> str:
    msg_uuid = reg._send_turn(bridge, agent_id, user_text)
    text, meta, err = reg._wait_downlink_for_user_msg_uuid(
        bridge,
        report,
        expected_user_msg_uuid=msg_uuid,
        timeout_sec=timeout_sec,
        label=label,
        trailing_label=f"{label}_mismatch",
    )
    if err is not None:
        print(f"{_TAG} WARNING {label} downlink: {err}", file=stderr, flush=True)
        text = text or ""
        meta = meta or {}
    if settle_trailing:
        trailing = reg._drain_turn_trailing_frames(bridge, report, label=label)
        if trailing:
            text = f"{text}{trailing}"
        if not reg._wait_input_delivered(
            repo_root,
            config_path,
            agent_id=agent_id,
            client_message_id=msg_uuid,
            timeout_sec=timeout_sec,
            label=label,
            stderr=stderr,
            skip_db_checks=False,
        ):
            raise RuntimeError(f"{label}: input not delivered")
    return text


def _write_report(
    *,
    output: Path,
    cells: list[dict[str, Any]],
    stderr: TextIO,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cells": cells,
        "note": (
            "L1 golden chat recall eval (#3606). Matrix: awake_write vs "
            "dreaming_only_fast. Report-only; exit 0 always."
        ),
    }
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{_TAG} wrote {output}", file=stderr)


def _prepare_fresh_agent(
    reg: Any,
    *,
    repo_root: Path,
    config_path: Path,
    api_base: str,
    token_path: str,
    user_id: str,
    stderr: TextIO,
) -> str:
    remaining_bonds = reg._deactivate_active_companion_bonds_for_user(
        repo_root,
        config_path,
        user_id=user_id,
    )
    if remaining_bonds:
        print(
            f"{_TAG} warning: {remaining_bonds} ACTIVE bond(s) for {user_id!r}",
            file=stderr,
            flush=True,
        )
    reg._purge_regression_bootstrap_agents_via_api(
        api_base=api_base,
        token_path=token_path,
        http_timeout=60.0,
        stderr=stderr,
    )
    return reg._create_agent_id(
        repo_root=repo_root,
        api_base=api_base,
        token_path=token_path,
        http_timeout=60.0,
        stderr=stderr,
    )


def _open_bridge(
    reg: Any,
    *,
    repo_root: Path,
    api_base: str,
    token_path: str,
    agent_id: str,
) -> Any:
    from tools.inty_v2_repl.backend_chat_ws import (
        BackendChatWsBridge,
        http_base_to_ws_chat_url,
    )

    bearer = reg._read_bearer(repo_root, token_path)
    ws_url = http_base_to_ws_chat_url(
        api_base,
        agent_id=agent_id,
        ws_conn_id=str(uuid.uuid4()),
    )
    bridge = BackendChatWsBridge(ws_url=ws_url, bearer_token=bearer)
    bridge.start(connect_timeout=45.0)
    return bridge


def _run_bootstrap_script(
    reg: Any,
    *,
    bridge: Any,
    report: dict[str, Any],
    scenario: Any,
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    user_id: str,
    stderr: TextIO,
) -> None:
    from app.core.companion_harness.experience_profile.experience_directives import (
        ExperienceSessionIntent,
        context_mode_for_session_intent,
    )

    print(f"{_TAG} waiting for implicit greeting...", file=stderr, flush=True)
    text, meta, err = reg._wait_implicit_sign_on_greeting(
        bridge,
        timeout_sec=reg._TURN_REPLY_TIMEOUT_SEC,
    )
    if err is not None:
        print(f"{_TAG} WARNING greeting: {err}", file=stderr, flush=True)
    elif text is not None:
        reg._drain_until_quiet(bridge, quiet_sec=2.0, max_sec=15.0)

    for idx, user_text in enumerate(scenario.user_turns, start=1):
        print(
            f"{_TAG} bootstrap turn {idx}: {user_text!r}",
            file=stderr,
            flush=True,
        )
        _drive_user_turn(
            reg,
            bridge=bridge,
            report=report,
            repo_root=repo_root,
            config_path=config_path,
            agent_id=agent_id,
            user_text=user_text,
            label=f"bootstrap-{idx}",
            stderr=stderr,
            timeout_sec=reg._BOOTSTRAP_TURN_SETTLE_MAX_SEC,
            settle_trailing=True,
        )

    if scenario.experience_profile is not None:
        profile = scenario.experience_profile
        intent = ExperienceSessionIntent(scenario.golden_facts.session_intent)
        expected_mode = context_mode_for_session_intent(intent)
        reg._run_experience_profile_phase(
            bridge=bridge,
            report=report,
            repo_root=repo_root,
            config_path=config_path,
            agent_id=agent_id,
            user_id=user_id,
            experience_profile_turn=profile.user_line,
            experience_profile_context_mode=expected_mode,
            stderr=stderr,
            skip_db_checks=False,
        )

    print(
        f"{_TAG} bootstrap finish: {_BOOTSTRAP_FINISH_TURN!r}",
        file=stderr,
        flush=True,
    )
    finish_msg_uuid = reg._send_turn(bridge, agent_id, _BOOTSTRAP_FINISH_TURN)
    _, _, finish_err = reg._wait_downlink_for_user_msg_uuid(
        bridge,
        report,
        expected_user_msg_uuid=finish_msg_uuid,
        timeout_sec=reg._BOOTSTRAP_TURN_SETTLE_MAX_SEC,
        label="bootstrap-finish",
        trailing_label="bootstrap-finish_mismatch",
    )
    if finish_err is not None:
        print(
            f"{_TAG} WARNING bootstrap-finish downlink: {finish_err}",
            file=stderr,
            flush=True,
        )
    reg._drain_turn_trailing_frames(bridge, report, label="bootstrap-finish")
    if not reg._wait_input_delivered(
        repo_root,
        config_path,
        agent_id=agent_id,
        client_message_id=finish_msg_uuid,
        timeout_sec=reg._BOOTSTRAP_TURN_SETTLE_MAX_SEC,
        label="bootstrap-finish",
        stderr=stderr,
        skip_db_checks=False,
    ):
        raise RuntimeError("bootstrap-finish: input not delivered")
    if not reg._wait_bootstrap_complete_flag(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        timeout_sec=reg._BOOTSTRAP_TURN_SETTLE_MAX_SEC,
        stderr=stderr,
        skip_db_checks=False,
    ):
        raise RuntimeError("bootstrap_complete flag still false")


def _run_recall_probes(
    reg: Any,
    *,
    bridge: Any,
    report: dict[str, Any],
    probes: tuple[Any, ...],
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    stderr: TextIO,
) -> tuple[Any, ...]:
    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        ChatTurnRecord,
    )

    records: list[ChatTurnRecord] = []
    for probe in probes:
        label = f"probe-{probe.phase.value}-{probe.probe_id}"
        print(f"{_TAG} {label}: {probe.user_line!r}", file=stderr, flush=True)
        reply = _drive_user_turn(
            reg,
            bridge=bridge,
            report=report,
            repo_root=repo_root,
            config_path=config_path,
            agent_id=agent_id,
            user_text=probe.user_line,
            label=label,
            stderr=stderr,
            timeout_sec=reg._SETTLED_TURN_TIMEOUT_SEC,
            settle_trailing=True,
        )
        records.append(
            ChatTurnRecord(
                probe_id=probe.probe_id,
                phase=probe.phase,
                user_text=probe.user_line,
                assistant_text=reply,
            )
        )
    return tuple(records)


def _probes_for_post_phase(
    scenario: Any,
    *,
    phase: Any,
) -> tuple[Any, ...]:
    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        RecallProbe,
    )

    return tuple(
        RecallProbe(
            probe_id=probe.probe_id,
            user_line=probe.user_line,
            expect_markers=probe.expect_markers,
            phase=phase,
        )
        for probe in scenario.recall_probes
    )


def _run_agent_eval(
    reg: Any,
    *,
    repo_root: Path,
    config_path: Path,
    scenario: Any,
    probes: tuple[Any, ...],
    user_id: str,
    stderr: TextIO,
    after_bootstrap: Any | None,
) -> tuple[tuple[Any, ...], str, list[Any]]:
    from tools.inty_v2_repl.backend_chat_ws import BackendChatWsBridge

    api_base = _DEFAULT_API_BASE
    token_path = str(repo_root / _DEFAULT_TOKEN_FILE)
    agent_id = _prepare_fresh_agent(
        reg,
        repo_root=repo_root,
        config_path=config_path,
        api_base=api_base,
        token_path=token_path,
        user_id=user_id,
        stderr=stderr,
    )
    bridge = _open_bridge(
        reg,
        repo_root=repo_root,
        api_base=api_base,
        token_path=token_path,
        agent_id=agent_id,
    )
    report: dict[str, Any] = {"turns": [], "errors": []}
    try:
        _run_bootstrap_script(
            reg,
            bridge=bridge,
            report=report,
            scenario=scenario,
            repo_root=repo_root,
            config_path=config_path,
            agent_id=agent_id,
            user_id=user_id,
            stderr=stderr,
        )
        if after_bootstrap is not None:
            bridge.stop()
            after_bootstrap(
                reg,
                repo_root=repo_root,
                config_path=config_path,
                user_id=user_id,
                agent_id=agent_id,
                stderr=stderr,
            )
            bridge = _open_bridge(
                reg,
                repo_root=repo_root,
                api_base=api_base,
                token_path=token_path,
                agent_id=agent_id,
            )
        records = _run_recall_probes(
            reg,
            bridge=bridge,
            report=report,
            probes=probes,
            repo_root=repo_root,
            config_path=config_path,
            agent_id=agent_id,
            stderr=stderr,
        )
    finally:
        if isinstance(bridge, BackendChatWsBridge):
            bridge.stop()
    return records, agent_id, report["errors"]


def _score_recall_llm(
    scenario: Any,
    chat_records: tuple[Any, ...],
) -> Any:
    from app.core.companion_harness.eval.bootstrap_memdoc_recall_judge import (
        default_recall_judge_model,
        llm_judge_golden_chat_recall,
        openrouter_judge_client,
    )

    client = openrouter_judge_client()
    model = default_recall_judge_model()
    return llm_judge_golden_chat_recall(
        scenario=scenario,
        chat_records=chat_records,
        client=client,
        model=model,
    )


def _run_live_cell(
    *,
    repo_root: Path,
    config_path: Path,
    scenario_id: str,
    policy: str,
    stderr: TextIO,
) -> dict[str, Any]:
    """Run one eval matrix cell (golden chat recall)."""

    _ensure_import_path(repo_root)
    scenarios = _load_scenarios(_DEFAULT_SCENARIOS)
    scenario = next(
        (s for s in scenarios if s.scenario_id == scenario_id),
        None,
    )
    if scenario is None:
        raise ValueError(f"unknown scenario_id: {scenario_id!r}")

    label = _matrix_label(policy)
    print(
        f"{_TAG} LIVE cell scenario={scenario_id} policy={policy} label={label}",
        file=stderr,
        flush=True,
    )

    from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
        RecallProbePhase,
        expand_pre_dream_probes,
        post_phase_for_awake_policy,
    )

    os.environ["INTY_CONFIG_YAML"] = str(config_path.resolve())
    reg = _load_regression_module(repo_root)
    user_id = _DEFAULT_USER_ID

    chat_records: dict[str, list[Any]] = {}
    pre_recall: float | None = None
    post_recall = 0.0
    overall_recall = 0.0
    per_marker: dict[str, float] = {}
    per_probe: tuple[Any, ...] = ()
    errors: list[Any] = []

    if policy == "awake_write":
        post_phase = post_phase_for_awake_policy()
        probes = _probes_for_post_phase(scenario, phase=post_phase)
        records, agent_id, errors = _run_agent_eval(
            reg,
            repo_root=repo_root,
            config_path=config_path,
            scenario=scenario,
            probes=probes,
            user_id=user_id,
            stderr=stderr,
            after_bootstrap=None,
        )
        chat_records["post_agent"] = list(records)
        score = _score_recall_llm(
            scenario=scenario,
            chat_records=records,
        )
        post_recall = score.post_recall
        overall_recall = score.overall_recall
        per_marker = score.per_marker_recall
        per_probe = score.per_probe
    elif policy == "dreaming_only":
        pre_probes = expand_pre_dream_probes(scenario.recall_probes)
        pre_records, pre_agent_id, pre_errors = _run_agent_eval(
            reg,
            repo_root=repo_root,
            config_path=config_path,
            scenario=scenario,
            probes=pre_probes,
            user_id=user_id,
            stderr=stderr,
            after_bootstrap=None,
        )
        pre_score = _score_recall_llm(
            scenario=scenario,
            chat_records=pre_records,
        )
        pre_recall = pre_score.pre_recall
        chat_records["pre_agent"] = list(pre_records)
        errors.extend(pre_errors)

        def _force_dream_after_bootstrap(
            reg_mod: Any,
            *,
            repo_root: Path,
            config_path: Path,
            user_id: str,
            agent_id: str,
            stderr: TextIO,
        ) -> None:
            ok = reg_mod._force_dream_at_bootstrap_boundary(
                repo_root,
                config_path,
                user_id=user_id,
                agent_id=agent_id,
                stderr=stderr,
                skip_db_checks=False,
            )
            if not ok:
                raise RuntimeError("force dream at bootstrap boundary failed")

        post_probes = _probes_for_post_phase(
            scenario,
            phase=RecallProbePhase.POST_DREAM,
        )
        post_records, post_agent_id, post_errors = _run_agent_eval(
            reg,
            repo_root=repo_root,
            config_path=config_path,
            scenario=scenario,
            probes=post_probes,
            user_id=user_id,
            stderr=stderr,
            after_bootstrap=_force_dream_after_bootstrap,
        )
        post_score = _score_recall_llm(
            scenario=scenario,
            chat_records=post_records,
        )
        post_recall = post_score.post_recall
        chat_records["post_agent"] = list(post_records)
        errors.extend(post_errors)
        all_records = pre_records + post_records
        merged = _score_recall_llm(
            scenario=scenario,
            chat_records=all_records,
        )
        overall_recall = merged.overall_recall
        per_marker = merged.per_marker_recall
        per_probe = merged.per_probe
        agent_id = post_agent_id
    else:
        raise ValueError(f"unsupported policy: {policy!r}")

    return {
        "scenario_id": scenario_id,
        "policy": policy,
        "label": label,
        "agent_id": agent_id,
        "golden_chat_recall": {
            "post_recall": post_recall,
            "pre_recall": pre_recall,
            "overall_recall": overall_recall,
            "per_marker_recall": per_marker,
            "per_probe": [p.model_dump() for p in per_probe],
        },
        "chat_records": {
            key: [r.model_dump() for r in rows]
            for key, rows in chat_records.items()
        },
        "errors": errors,
    }


def _run_live_matrix(
    *,
    repo_root: Path,
    config_path: Path,
    scenarios_path: Path,
    output: Path,
    stderr: TextIO,
) -> list[dict[str, Any]]:
    scenarios = _load_scenarios(scenarios_path)
    cells: list[dict[str, Any]] = []
    total = len(scenarios) * len(_MATRIX_CELLS)
    cell_idx = 0
    for matrix_policy, _idle in _MATRIX_CELLS:
        label = _matrix_label(matrix_policy)
        print(
            f"{_TAG} matrix group {label} — patching config + restarting Ops",
            file=stderr,
            flush=True,
        )
        _patch_eval_config_yaml(config_path, policy=matrix_policy)
        _restart_ops(repo_root, stderr)
        for scenario in scenarios:
            cell_idx += 1
            print(
                f"{_TAG} matrix cell {cell_idx}/{total}: "
                f"{scenario.scenario_id} × {label}",
                file=stderr,
                flush=True,
            )
            try:
                cells.append(
                    _run_live_cell(
                        repo_root=repo_root,
                        config_path=config_path,
                        scenario_id=scenario.scenario_id,
                        policy=matrix_policy,
                        stderr=stderr,
                    )
                )
            except Exception as exc:
                cells.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "policy": matrix_policy,
                        "label": label,
                        "error": repr(exc),
                    }
                )
            _write_report(output=output, cells=cells, stderr=stderr)
    return cells


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap MemDoc L1 eval")
    parser.add_argument(
        "--scenarios-yaml",
        type=Path,
        default=_DEFAULT_SCENARIOS,
    )
    parser.add_argument(
        "--config-yaml",
        type=Path,
        default=_DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--policy",
        choices=[*_POLICIES, "all"],
        default="all",
    )
    parser.add_argument("--scenario-id", default="")
    parser.add_argument("--all-scenarios", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--run-live-matrix", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tmp")
        / f"bootstrap-memdoc-eval-{int(time.time())}.json",
    )
    args = parser.parse_args(argv)

    stderr = sys.stderr
    plan = _plan_matrix(
        scenarios_path=args.scenarios_yaml,
        policy_filter=args.policy,
    )
    if args.scenario_id:
        plan = [c for c in plan if c["scenario_id"] == args.scenario_id]

    if args.dry_run:
        print(f"{_TAG} matrix plan ({len(plan)} cells):", file=stderr)
        for cell in plan:
            print(
                f"  {cell['scenario_id']} × {cell['label']}",
                file=stderr,
            )
        _write_report(output=args.output, cells=plan, stderr=stderr)
        return 0

    cells: list[dict[str, Any]] = []
    if args.run_live_matrix:
        cells = _run_live_matrix(
            repo_root=_REPO_ROOT,
            config_path=args.config_yaml,
            scenarios_path=args.scenarios_yaml,
            output=args.output,
            stderr=stderr,
        )
    elif args.run_live:
        for cell in plan:
            try:
                cells.append(
                    _run_live_cell(
                        repo_root=_REPO_ROOT,
                        config_path=args.config_yaml,
                        scenario_id=cell["scenario_id"],
                        policy=cell["policy"],
                        stderr=stderr,
                    )
                )
            except Exception as exc:
                cells.append({**cell, "error": repr(exc)})
        _write_report(output=args.output, cells=cells, stderr=stderr)
    else:
        cells = plan
        print(
            f"{_TAG} no --run-live: wrote plan only. Use --dry-run or --run-live.",
            file=stderr,
        )
        _write_report(output=args.output, cells=cells, stderr=stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
