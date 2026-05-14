#!/usr/bin/env python3
"""
绘制 google/gemini-2.5-flash-lite 在不同上下文占用率下的指令遵循成功率曲线。

支持两种口径：
- strict: 严格 JSON 解析后的 ia_mean
- semantic: 先剥离 ```json ... ``` 代码块再解析后的 semantic_ia_mean
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="绘制 Gemini 指令遵循成功率-上下文占用率曲线。"
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="例如 research/llms_contextual_instructions_capacity/results/<run_id>",
    )
    parser.add_argument(
        "--output",
        default="gemini_success_rate_vs_u.png",
        help="输出图片文件名（保存到 run-dir/plots 下）",
    )
    parser.add_argument(
        "--mode",
        default="semantic",
        choices=["strict", "semantic"],
        help="成功率口径：strict=严格 JSON，semantic=剥离代码块后的语义口径",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    csv_path = run_dir / "cell_summary.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"未找到文件：{csv_path}")

    xs: list[float] = []
    ys: list[float] = []

    y_key = "ia_mean" if args.mode == "strict" else "semantic_ia_mean"
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = sorted(reader, key=lambda r: float(r["utilization_ratio"]))
        for row in rows:
            xs.append(float(row["utilization_ratio"]))
            ys.append(float(row[y_key]))

    out_dir = run_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.output

    plt.figure(figsize=(8, 5))
    plt.plot(xs, ys, marker="o", linewidth=2)
    title_mode = (
        "strict JSON" if args.mode == "strict" else "semantic (code-fence stripped)"
    )
    plt.title(f"Gemini success rate vs context utilization [{title_mode}]")
    plt.xlabel("Context utilization U")
    plt.ylabel("Success rate (completed instructions / total)")
    plt.ylim(0.0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()

    print(f"图像已保存：{out_path}")


if __name__ == "__main__":
    main()
