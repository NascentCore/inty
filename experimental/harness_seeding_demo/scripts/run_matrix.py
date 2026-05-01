#!/usr/bin/env python3
"""Run harness trials for every seed under seeds/ and write matrix_summary.json."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass


_DEFAULT_CONFIG_YAML = _REPO_ROOT / "devops/config.yaml.local"


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
    p.add_argument(
        "--config-yaml",
        type=Path,
        default=_DEFAULT_CONFIG_YAML,
        help="Forwarded to run_trial (agent.api_key -> OPENAI_API_KEY when env unset).",
    )
    p.add_argument(
        "--no-config-yaml",
        action="store_true",
        help="Forwarded to run_trial.",
    )
    return p.parse_args()


def main() -> None:
    os.environ.setdefault("INTY_V2_PROTO_ASYNC_TOOL_BG", "0")
    os.environ.setdefault("INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL", "1")
    args = _parse_args()
    if not (0.0 <= args.threshold <= 1.0):
        raise SystemExit("--threshold must be between 0 and 1")
    seeds_root = args.seeds_root.resolve()
    out_root = args.output_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    run_trial = Path(__file__).resolve().parent / "run_trial.py"

    rows: list[dict] = []
    errors: list[dict] = []

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
        if args.no_config_yaml:
            cmd.append("--no-config-yaml")
        else:
            cmd.extend(["--config-yaml", str(args.config_yaml.resolve())])

        proc = subprocess.run(
            cmd,
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        row_base = {"seed": seed_dir.name}
        if proc.returncode != 0:
            err_tail = (proc.stderr or "")[-8000:]
            errors.append(
                {
                    **row_base,
                    "exit_code": proc.returncode,
                    "stderr_tail": err_tail,
                }
            )
            rows.append(
                {
                    **row_base,
                    "first_pass_turn": None,
                    "turns_executed": None,
                    "workspace_path": None,
                    "error": "run_trial_failed",
                }
            )
            continue

        summary_path = run_out / "summary.json"
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(
                {
                    **row_base,
                    "exit_code": proc.returncode,
                    "stderr_tail": traceback.format_exc(),
                    "detail": repr(exc),
                }
            )
            rows.append(
                {
                    **row_base,
                    "first_pass_turn": None,
                    "turns_executed": None,
                    "workspace_path": None,
                    "error": "summary_read_failed",
                }
            )
            continue

        rows.append(
            {
                **row_base,
                "first_pass_turn": summary.get("first_pass_turn"),
                "turns_executed": summary.get("turns_executed"),
                "workspace_path": summary.get("workspace_path"),
                "llm": summary.get("llm"),
            }
        )

    matrix_path = out_root / "matrix_summary.json"
    matrix_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    err_path = out_root / "matrix_errors.json"
    err_path.write_text(
        json.dumps(errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(matrix_path.read_text(encoding="utf-8"))
    if errors:
        print(f"harness matrix: {len(errors)} seed(s) failed; see {err_path}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
