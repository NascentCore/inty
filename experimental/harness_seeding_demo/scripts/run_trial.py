#!/usr/bin/env python3
"""Run one harness trial: seed workspace, drive companion kernel turns, score replies."""

from __future__ import annotations

import argparse
import asyncio
import json
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

from app.core.agentic_kernel.companion.manager import CompanionConfig, CompanionManager
from app.core.agentic_kernel.companion.llm_client import CompanionLLMConfig
from app.core.agentic_kernel.companion.memory_pipeline import MemoryPipelineConfig

from experimental.harness_seeding_demo.scorer.emotional_rubric import (
    score_emotional_understanding_reply,
)
from experimental.harness_seeding_demo.user_script import load_user_script
from experimental.harness_seeding_demo.workspace_setup import seed_memory_store_from_directory


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed-dir", type=Path, required=True)
    p.add_argument("--script", type=Path, required=True)
    p.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Score threshold in [0, 1] for emotional_rubric passing.",
    )
    p.add_argument("--max-turns", type=int, default=50)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--workspaces-base", type=Path, default=None)
    p.add_argument("--defer-memory-ms", type=float, default=800.0)
    return p.parse_args()


async def _run(args: argparse.Namespace) -> dict:
    if not (0.0 <= args.threshold <= 1.0):
        raise SystemExit("--threshold must be between 0 and 1")
    script_lines = load_user_script(args.script)
    if not script_lines:
        raise SystemExit("user script is empty")

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
        user_update_every_n_turns=99999,
        soul_update_every_n_turns=99999,
    )

    cfg = CompanionConfig(
        workspaces_base_dir=str(base.resolve()),
        llm=CompanionLLMConfig.from_openrouter_env(),
        memory=mem_cfg,
        memory_pg_dsn="",
    )
    manager = CompanionManager(cfg)
    session = manager.get_or_create_session(user_id, companion_id, chat_id)

    turns_out: list[dict] = []
    first_pass_turn: int | None = None

    try:
        for i, user_text in enumerate(script_lines[: args.max_turns], start=1):
            result = await manager.run_turn(
                session,
                user_text,
                defer_memory_update=True,
            )
            if args.defer_memory_ms > 0:
                time.sleep(args.defer_memory_ms / 1000.0)

            sr = score_emotional_understanding_reply(
                result.assistant_text,
                threshold=args.threshold,
                user_message_text=user_text,
            )
            row = {
                "turn_index": i,
                "user_text": user_text,
                "assistant_text": result.assistant_text,
                "score": sr.score,
                "passed": sr.passed,
                "checks": sr.checks,
            }
            turns_out.append(row)
            if sr.passed and first_pass_turn is None:
                first_pass_turn = i
    finally:
        manager.shutdown_session(user_id, companion_id, chat_id)

    summary = {
        "run_id": run_id,
        "seed_dir": str(args.seed_dir.resolve()),
        "script": str(args.script.resolve()),
        "threshold": args.threshold,
        "first_pass_turn": first_pass_turn,
        "total_script_lines": len(script_lines),
        "turns_executed": len(turns_out),
        "workspace_path": str(ws_path.resolve()),
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
    summary = asyncio.run(_run(args))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
