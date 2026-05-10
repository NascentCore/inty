#!/usr/bin/env python3
"""Run one harness trial: seed workspace, drive companion kernel turns, score replies."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

from experimental.harness_seeding_demo.config_yaml_env import (
    apply_llm_env_from_config_yaml,
)

_DEFAULT_CONFIG_YAML = _REPO_ROOT / "devops/config.yaml.local"


def _maybe_load_config_yaml(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    p = path.resolve()
    if not p.is_file():
        print(f"harness: skip config yaml (not found): {p}", file=sys.stderr)
        return {}
    return apply_llm_env_from_config_yaml(p)


from app.core.agentic_kernel.companion.manager import CompanionConfig, CompanionManager
from app.core.agentic_kernel.companion.llm_client import CompanionLLMConfig
from app.core.agentic_kernel.companion.memory_pipeline import MemoryPipelineConfig

from experimental.harness_seeding_demo.scorer.rubrics import (
    DEFAULT_RUBRIC_THRESHOLDS,
    RUBRIC_FN,
    score_all_rubrics,
)
from experimental.harness_seeding_demo.user_script import load_user_script
from experimental.harness_seeding_demo.workspace_setup import (
    seed_memory_store_from_directory,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed-dir", type=Path, required=True)
    p.add_argument("--script", type=Path, required=True)
    p.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Default threshold for rubric 'default' only; others use built-ins unless --rubric-threshold.",
    )
    p.add_argument(
        "--rubrics",
        type=str,
        default="default,strict_emotional,premature_solution,boundary_tone",
        help="Comma-separated rubric ids (see scorer/rubrics.py).",
    )
    p.add_argument(
        "--rubric-threshold",
        action="append",
        default=[],
        metavar="ID=FLOAT",
        help="Override threshold for one rubric, e.g. default=0.9 (repeatable).",
    )
    p.add_argument("--max-turns", type=int, default=50)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--workspaces-base", type=Path, default=None)
    p.add_argument(
        "--config-yaml",
        type=Path,
        default=_DEFAULT_CONFIG_YAML,
        help=(
            "YAML with agent.api_key (used as OPENAI_API_KEY when env unset). "
            f"Default {_DEFAULT_CONFIG_YAML.relative_to(_REPO_ROOT)}; file missing is skipped."
        ),
    )
    p.add_argument(
        "--no-config-yaml",
        action="store_true",
        help="Do not load agent.api_key from YAML (require OPENROUTER_API_KEY / OPENAI_API_KEY).",
    )
    p.add_argument("--defer-memory-ms", type=float, default=800.0)
    return p.parse_args()


def _parse_rubric_threshold_overrides(raw: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in raw:
        if "=" not in item:
            raise SystemExit(f"invalid --rubric-threshold {item!r}, expected id=float")
        k, v = item.split("=", 1)
        k = k.strip()
        try:
            fv = float(v.strip())
        except ValueError as e:
            raise SystemExit(f"invalid float in --rubric-threshold {item!r}") from e
        if not (0.0 <= fv <= 1.0):
            raise SystemExit(f"threshold for {k} must be in [0, 1]")
        out[k] = fv
    return out


async def _run(args: argparse.Namespace) -> dict:
    if not (0.0 <= args.threshold <= 1.0):
        raise SystemExit("--threshold must be between 0 and 1")
    rubric_ids = [x.strip() for x in args.rubrics.split(",") if x.strip()]
    if not rubric_ids:
        raise SystemExit("--rubrics must list at least one id")
    unknown = [r for r in rubric_ids if r not in RUBRIC_FN]
    if unknown:
        raise SystemExit(
            f"unknown rubric ids: {unknown}; known: {sorted(RUBRIC_FN.keys())}"
        )
    th_map = dict(DEFAULT_RUBRIC_THRESHOLDS)
    th_map["default"] = args.threshold
    th_map.update(_parse_rubric_threshold_overrides(list(args.rubric_threshold)))

    script_lines = load_user_script(args.script)
    if not script_lines:
        raise SystemExit("user script is empty")

    llm_cfg = CompanionLLMConfig.from_openrouter_env()
    yaml_applied = getattr(args, "_harness_config_yaml_applied", {})
    from_yaml_key = "OPENAI_API_KEY" in yaml_applied
    openrouter_set = bool((os.getenv("OPENROUTER_API_KEY") or "").strip())
    openai_set = bool((os.getenv("OPENAI_API_KEY") or "").strip())
    if openrouter_set:
        api_key_source = "env_OPENROUTER_API_KEY"
    elif from_yaml_key:
        api_key_source = "yaml_agent_api_key"
    elif openai_set:
        api_key_source = "env_OPENAI_API_KEY"
    else:
        api_key_source = "unset"

    run_id = uuid.uuid4().hex[:12]
    out_dir = args.output_dir
    if out_dir is None:
        out_dir = Path(tempfile.mkdtemp(prefix=f"harness_{run_id}_"))
    else:
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

    base = args.workspaces_base
    if base is None:
        base = out_dir / "_ws_base"
    base.mkdir(parents=True, exist_ok=True)

    user_id = f"harness_user_{run_id}"
    companion_id = "demo_companion"
    chat_id = "demo_chat"

    ws_path = base / user_id / companion_id / chat_id
    if ws_path.exists():
        shutil.rmtree(ws_path)
    seed_memory_store_from_directory(args.seed_dir.resolve(), ws_path)

    mem_cfg = MemoryPipelineConfig(
        day_summary_disabled=True,
        user_update_disabled=True,
        soul_update_disabled=True,
        memory_update_every_n_turns=99999,
        soul_update_every_n_turns=99999,
    )

    cfg = CompanionConfig(
        memory_store_scope_base_dir=str(base.resolve()),
        llm=llm_cfg,
        memory=mem_cfg,
        memory_pg_dsn="",
    )
    manager = CompanionManager(cfg)
    session = manager.get_or_create_session(user_id, companion_id, chat_id)

    turns_out: list[dict] = []
    first_pass_turn_by_rubric: dict[str, int | None] = {rid: None for rid in rubric_ids}

    try:
        for i, user_text in enumerate(script_lines[: args.max_turns], start=1):
            result = await manager.run_turn(
                session,
                user_text,
                defer_memory_update=True,
            )
            if args.defer_memory_ms > 0:
                time.sleep(args.defer_memory_ms / 1000.0)

            rubric_results = score_all_rubrics(
                result.assistant_text,
                user_message_text=user_text,
                thresholds=th_map,
                rubric_ids=rubric_ids,
            )
            rubric_payload = {
                rid: {
                    "score": rr.score,
                    "passed": rr.passed,
                    "checks": rr.checks,
                }
                for rid, rr in rubric_results.items()
            }
            row = {
                "turn_index": i,
                "user_text": user_text,
                "assistant_text": result.assistant_text,
                "rubrics": rubric_payload,
            }
            turns_out.append(row)
            for rid, rr in rubric_results.items():
                if rr.passed and first_pass_turn_by_rubric[rid] is None:
                    first_pass_turn_by_rubric[rid] = i
    finally:
        manager.shutdown_session(user_id, companion_id, chat_id)

    summary = {
        "run_id": run_id,
        "seed_dir": str(args.seed_dir.resolve()),
        "script": str(args.script.resolve()),
        "rubrics": rubric_ids,
        "thresholds_by_rubric": {rid: th_map[rid] for rid in rubric_ids},
        "first_pass_turn_by_rubric": first_pass_turn_by_rubric,
        "first_pass_turn": first_pass_turn_by_rubric.get("default"),
        "threshold": args.threshold,
        "total_script_lines": len(script_lines),
        "turns_executed": len(turns_out),
        "workspace_path": str(ws_path.resolve()),
        "llm": {
            "api_base": llm_cfg.api_base,
            "default_model": llm_cfg.default_model,
            "chat_model": (llm_cfg.chat_model or "").strip() or llm_cfg.default_model,
            "tool_model": (llm_cfg.tool_model or "").strip() or llm_cfg.default_model,
            "api_key_source": api_key_source,
        },
    }

    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with (out_dir / "turns.jsonl").open("w", encoding="utf-8") as f:
        for row in turns_out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return summary


def main() -> None:
    args = _parse_args()
    os.environ.setdefault("INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL", "1")
    applied_yaml: dict[str, str] = {}
    if not args.no_config_yaml:
        applied_yaml = _maybe_load_config_yaml(args.config_yaml)
    setattr(args, "_harness_config_yaml_applied", applied_yaml)
    summary = asyncio.run(_run(args))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
