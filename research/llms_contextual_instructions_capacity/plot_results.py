#!/usr/bin/env python3
"""
Plot benchmark curves from a run directory produced by run_benchmark.py.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot benchmark result curves.")
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Path like research/llms_contextual_instructions_capacity/results/<run_id>",
    )
    return parser.parse_args()


def load_summary_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def float_field(row: dict[str, str], key: str) -> float:
    return float(row[key])


def int_field(row: dict[str, str], key: str) -> int:
    return int(row[key])


def plot_metric_vs_u(
    rows: list[dict[str, str]],
    instruction_count: int,
    metric_key: str,
    metric_label: str,
    out_path: Path,
) -> None:
    selected = [r for r in rows if int_field(r, "instruction_count") == instruction_count]
    profiles = sorted({r["placement_profile"] for r in selected})

    plt.figure(figsize=(8, 5))
    for profile in profiles:
        series = [r for r in selected if r["placement_profile"] == profile]
        series = sorted(series, key=lambda x: float_field(x, "utilization_ratio"))
        xs = [float_field(r, "utilization_ratio") for r in series]
        ys = [float_field(r, metric_key) for r in series]
        plt.plot(xs, ys, marker="o", label=f"profile={profile}")

    plt.title(f"{metric_label} vs U (N={instruction_count})")
    plt.xlabel("Context utilization U")
    plt.ylabel(metric_label)
    plt.ylim(0.0, 1.05 if metric_key != "median_latency_ms" else max(ys) * 1.1 if ys else 1)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_latency_vs_u(
    rows: list[dict[str, str]],
    instruction_count: int,
    out_path: Path,
) -> None:
    selected = [r for r in rows if int_field(r, "instruction_count") == instruction_count]
    profiles = sorted({r["placement_profile"] for r in selected})

    plt.figure(figsize=(8, 5))
    max_y = 1.0
    for profile in profiles:
        series = [r for r in selected if r["placement_profile"] == profile]
        series = sorted(series, key=lambda x: float_field(x, "utilization_ratio"))
        xs = [float_field(r, "utilization_ratio") for r in series]
        ys = [float_field(r, "median_latency_ms") for r in series]
        if ys:
            max_y = max(max_y, max(ys))
        plt.plot(xs, ys, marker="o", label=f"profile={profile}")

    plt.title(f"Median latency vs U (N={instruction_count})")
    plt.xlabel("Context utilization U")
    plt.ylabel("Median latency (ms)")
    plt.ylim(0.0, max_y * 1.15)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_u_hard_overview(rows: list[dict[str, str]], run_dir: Path, out_path: Path) -> None:
    with (run_dir / "summary.json").open("r", encoding="utf-8") as f:
        payload = json.load(f)
    limits: dict[str, dict[str, float | None]] = payload["limit_recommendation"]

    target_ia = float(payload["config"]["target_ia"])
    target_rsr = float(payload["config"]["target_rsr"])
    target_eff = float(payload["config"]["target_effectiveness"])
    target_fer = float(payload["config"]["target_format_error_rate"])

    # Aggregate over profiles by taking the min (more conservative).
    by_n: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        n = int_field(row, "instruction_count")
        by_n.setdefault(n, []).append(row)

    xs_n = sorted(by_n.keys())
    ys_u_hard: list[float] = []
    for n in xs_n:
        if n <= 8:
            bucket = "<=8"
        elif n <= 16:
            bucket = "<=16"
        elif n <= 32:
            bucket = "<=32"
        else:
            bucket = "<=64"
        u_hard = limits.get(bucket, {}).get("hard_limit_utilization")
        ys_u_hard.append(float(u_hard) if u_hard is not None else float("nan"))

    plt.figure(figsize=(8, 5))
    plt.plot(xs_n, ys_u_hard, marker="s", color="tab:red")
    plt.title("Provisional U_hard by instruction count bucket")
    plt.xlabel("Instruction count N")
    plt.ylabel("U_hard")
    plt.ylim(0.0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()

    definition = (
        "U_hard definition: first utilization U where threshold failures appear in 2 "
        "consecutive U levels (under both uniform and edges profiles).\n"
        f"Thresholds: IA_CI_low>={target_ia}, RSR_CI_low>={target_rsr}, "
        f"Effectiveness_CI_low>={target_eff}, FormatErrorRate<={target_fer}."
    )
    with (run_dir / "plots" / "u_hard_definition.txt").open("w", encoding="utf-8") as f:
        f.write(definition + "\n")


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    csv_path = run_dir / "cell_summary.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"cell_summary.csv not found in {run_dir}")

    rows = load_summary_csv(csv_path)
    out_dir = run_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    instruction_counts = sorted({int_field(r, "instruction_count") for r in rows})
    for n in instruction_counts:
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="ia_mean",
            metric_label="Instruction Accuracy (IA)",
            out_path=out_dir / f"ia_vs_u_n{n}.png",
        )
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="rsr",
            metric_label="Response Success Rate (RSR)",
            out_path=out_dir / f"rsr_vs_u_n{n}.png",
        )
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="effectiveness_mean",
            metric_label="Effectiveness",
            out_path=out_dir / f"effectiveness_vs_u_n{n}.png",
        )
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="format_error_rate",
            metric_label="Format Error Rate",
            out_path=out_dir / f"format_error_vs_u_n{n}.png",
        )
        plot_latency_vs_u(
            rows=rows,
            instruction_count=n,
            out_path=out_dir / f"latency_vs_u_n{n}.png",
        )

    plot_u_hard_overview(rows=rows, run_dir=run_dir, out_path=out_dir / "u_hard_by_n.png")

    print(f"Saved plots to: {out_dir}")


if __name__ == "__main__":
    main()
