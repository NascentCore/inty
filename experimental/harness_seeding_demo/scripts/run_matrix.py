#!/usr/bin/env python3
"""Run harness trials for every seed under seeds/ and write matrix_summary.json."""

from __future__ import annotations

import argparse
import json
import os
import statistics
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
        / "experimental/harness_seeding_demo/fixtures/work_stress_script_12.json",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Forwarded to run_trial (default rubric only).",
    )
    p.add_argument("--max-turns", type=int, default=50)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--defer-memory-ms", type=float, default=800.0)
    p.add_argument(
        "--config-yaml",
        type=Path,
        default=_DEFAULT_CONFIG_YAML,
        help="Forwarded to run_trial.",
    )
    p.add_argument(
        "--no-config-yaml",
        action="store_true",
        help="Forwarded to run_trial.",
    )
    p.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Repeat full seed matrix this many times (fresh workspace each rep).",
    )
    p.add_argument(
        "--rubrics",
        type=str,
        default="default,strict_emotional,premature_solution,boundary_tone",
        help="Forwarded to run_trial.",
    )
    p.add_argument(
        "--rubric-threshold",
        action="append",
        default=[],
        metavar="ID=FLOAT",
        help="Forwarded to run_trial (repeatable).",
    )
    return p.parse_args()


def main() -> None:
    os.environ.setdefault("INTY_V2_PROTO_ASYNC_TOOL_BG", "0")
    os.environ.setdefault("INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL", "1")
    args = _parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")
    if not (0.0 <= args.threshold <= 1.0):
        raise SystemExit("--threshold must be between 0 and 1")
    seeds_root = args.seeds_root.resolve()
    out_root = args.output_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    run_trial = Path(__file__).resolve().parent / "run_trial.py"

    seed_dirs = sorted(d for d in seeds_root.iterdir() if d.is_dir())
    rubric_ids = [x.strip() for x in args.rubrics.split(",") if x.strip()]
    errors: list[dict] = []

    all_rep_rows: list[dict] = []

    for rep in range(1, args.repetitions + 1):
        rep_dir = out_root / f"rep_{rep}"
        rep_dir.mkdir(parents=True, exist_ok=True)

        for seed_dir in seed_dirs:
            run_out = rep_dir / seed_dir.name
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
                "--rubrics",
                args.rubrics,
            ]
            for rt in args.rubric_threshold:
                cmd.extend(["--rubric-threshold", rt])
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
            row_base = {"repetition": rep, "seed": seed_dir.name}
            if proc.returncode != 0:
                errors.append(
                    {
                        **row_base,
                        "exit_code": proc.returncode,
                        "stderr_tail": (proc.stderr or "")[-8000:],
                    }
                )
                all_rep_rows.append({**row_base, "error": "run_trial_failed"})
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
                all_rep_rows.append({**row_base, "error": "summary_read_failed"})
                continue

            fp = summary.get("first_pass_turn_by_rubric") or {}
            row = {
                **row_base,
                "workspace_path": summary.get("workspace_path"),
                "llm": summary.get("llm"),
                "first_pass_turn_by_rubric": fp,
            }
            for rid in rubric_ids:
                row[f"first_pass_{rid}"] = fp.get(rid)
            all_rep_rows.append(row)

    by_seed: dict[str, list[dict]] = {}
    for row in all_rep_rows:
        if row.get("error"):
            continue
        by_seed.setdefault(row["seed"], []).append(row)

    aggregate: list[dict] = []
    for seed in sorted(by_seed.keys()):
        reps = by_seed[seed]
        agg_row: dict = {"seed": seed, "repetitions_completed": len(reps)}
        for rid in rubric_ids:
            vals = []
            for r in reps:
                fp = (r.get("first_pass_turn_by_rubric") or {}).get(rid)
                if fp is not None:
                    vals.append(fp)
            key_med = f"median_first_pass_{rid}"
            key_all = f"all_passed_turn1_{rid}"
            if vals:
                agg_row[key_med] = float(statistics.median(vals))
                agg_row[key_all] = all(v == 1 for v in vals)
            else:
                agg_row[key_med] = None
                agg_row[key_all] = False
        aggregate.append(agg_row)

    (out_root / "matrix_all_repetitions.json").write_text(
        json.dumps(all_rep_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_root / "matrix_summary.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    err_path = out_root / "matrix_errors.json"
    err_path.write_text(
        json.dumps(errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print((out_root / "matrix_summary.json").read_text(encoding="utf-8"))
    if errors:
        print(
            f"harness matrix: {len(errors)} job(s) failed; see {err_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
