#!/usr/bin/env python3
"""Run harness trials for every seed under seeds/ and write matrix_summary.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--seeds-root",
        type=Path,
        default=_REPO_ROOT / "experimental/harness_seeding_demo/seeds",
    )
    p.add_argument(
        "--script",
        type=Path,
        default=_REPO_ROOT
        / "experimental/harness_seeding_demo/fixtures/work_stress_script.json",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Passed to run_trial; must be in [0, 1].",
    )
    p.add_argument("--max-turns", type=int, default=50)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--defer-memory-ms", type=float, default=800.0)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if not (0.0 <= args.threshold <= 1.0):
        raise SystemExit("--threshold must be between 0 and 1")
    seeds_root = args.seeds_root.resolve()
    out_root = args.output_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    run_trial = Path(__file__).resolve().parent / "run_trial.py"

    rows: list[dict] = []
    for seed_dir in sorted(d for d in seeds_root.iterdir() if d.is_dir()):
        run_out = out_root / seed_dir.name
        cmd = [
            sys.executable,
            str(run_trial),
            "--seed-dir",
            str(seed_dir),
            "--script",
            str(args.script.resolve()),
            "--threshold",
            str(args.threshold),
            "--max-turns",
            str(args.max_turns),
            "--output-dir",
            str(run_out),
            "--defer-memory-ms",
            str(args.defer_memory_ms),
        ]
        subprocess.run(cmd, check=True, cwd=str(_REPO_ROOT))
        summary_path = run_out / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "seed": seed_dir.name,
                "first_pass_turn": summary.get("first_pass_turn"),
                "turns_executed": summary.get("turns_executed"),
                "workspace_path": summary.get("workspace_path"),
            }
        )

    matrix_path = out_root / "matrix_summary.json"
    matrix_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(matrix_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
