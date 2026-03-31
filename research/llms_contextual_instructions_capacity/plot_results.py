#!/usr/bin/env python3
"""
从 run_benchmark.py 产出的运行目录中绘制基准曲线。
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="绘制基准测试结果曲线。")
    parser.add_argument(
        "--run-dir",
        required=True,
        help="例如 research/llms_contextual_instructions_capacity/results/<run_id>",
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
        plt.plot(xs, ys, marker="o", label=f"分布={profile}")

    plt.title(f"{metric_label} 随 U 变化 (N={instruction_count})")
    plt.xlabel("上下文利用率 U")
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
        plt.plot(xs, ys, marker="o", label=f"分布={profile}")

    plt.title(f"中位延迟随 U 变化 (N={instruction_count})")
    plt.xlabel("上下文利用率 U")
    plt.ylabel("中位延迟 (ms)")
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

    # 在不同分布间取更保守的结果做汇总。
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
    plt.title("各指令桶的暂定 U_hard")
    plt.xlabel("指令数量 N")
    plt.ylabel("U_hard")
    plt.ylim(0.0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()

    definition = (
        "U_hard 定义：在同一指令桶内，同时检查 uniform 与 edges 两种分布时，"
        "阈值失败连续出现在两个相邻 U 点的第一个 U。\n"
        f"阈值条件：IA_CI_low>={target_ia}，RSR_CI_low>={target_rsr}，"
        f"有效性_CI_low>={target_eff}，格式错误率<={target_fer}。"
    )
    with (run_dir / "plots" / "u_hard_definition.txt").open("w", encoding="utf-8") as f:
        f.write(definition + "\n")


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    csv_path = run_dir / "cell_summary.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"在 {run_dir} 中未找到 cell_summary.csv")

    rows = load_summary_csv(csv_path)
    out_dir = run_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    instruction_counts = sorted({int_field(r, "instruction_count") for r in rows})
    for n in instruction_counts:
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="ia_mean",
            metric_label="指令准确率（IA）",
            out_path=out_dir / f"ia_vs_u_n{n}.png",
        )
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="rsr",
            metric_label="整响应成功率（RSR）",
            out_path=out_dir / f"rsr_vs_u_n{n}.png",
        )
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="effectiveness_mean",
            metric_label="有效性（Effectiveness）",
            out_path=out_dir / f"effectiveness_vs_u_n{n}.png",
        )
        plot_metric_vs_u(
            rows=rows,
            instruction_count=n,
            metric_key="format_error_rate",
            metric_label="格式错误率",
            out_path=out_dir / f"format_error_vs_u_n{n}.png",
        )
        plot_latency_vs_u(
            rows=rows,
            instruction_count=n,
            out_path=out_dir / f"latency_vs_u_n{n}.png",
        )

    plot_u_hard_overview(rows=rows, run_dir=run_dir, out_path=out_dir / "u_hard_by_n.png")

    print(f"图表已保存到: {out_dir}")


if __name__ == "__main__":
    main()
