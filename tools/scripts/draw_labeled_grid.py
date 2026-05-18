#!/usr/bin/env python3
"""Render a labeled matrix grid from YAML (matplotlib, Agg)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Rectangle


def _normalize_cell(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    return s


def _default_font_family() -> list[str]:
    import platform

    if platform.system() == "Darwin":
        return [
            "PingFang SC",
            "Heiti SC",
            "Songti SC",
            "Arial Unicode MS",
            "DejaVu Sans",
        ]
    return ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "SimHei", "DejaVu Sans"]


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    if "rows" not in data:
        raise ValueError(
            "YAML must contain key 'rows': list of rows (each row is a list of cell strings)"
        )
    rows = data["rows"]
    if not rows or not isinstance(rows, list):
        raise ValueError("'rows' must be a non-empty list")
    ncols = len(rows[0])
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != ncols:
            raise ValueError(f"Row {i} must be a list of length {ncols}")
    data["rows"] = [[_normalize_cell(c) for c in row] for row in rows]
    return data


def draw(data: dict, out_path: Path) -> None:
    layout = data.get("layout") or {}
    style = data.get("style") or {}
    w_in = float(layout.get("fig_width_in", 12))
    h_in = float(layout.get("fig_height_in", 8))
    dpi = int(layout.get("dpi", 150))

    fig_face = style.get("figure_facecolor", "#121212")
    cell_face = style.get("cell_facecolor", "#2a2a2a")
    edge = style.get("edgecolor", "#888888")
    lw = float(style.get("linewidth", 1.0))
    text_c = style.get("text_color", "#eaeaea")
    title_c = style.get("title_color", "#ffffff")
    fs_title = float(style.get("font_size_title", 13))
    fs_head = float(style.get("font_size_header", 11))
    fs_cell = float(style.get("font_size_cell", 9))
    ff = style.get("font_family")
    if ff:
        families = [ff] if isinstance(ff, str) else list(ff)
    else:
        families = _default_font_family()
    plt.rcParams["font.sans-serif"] = families
    plt.rcParams["axes.unicode_minus"] = False

    rows = data["rows"]
    nrows = len(rows)
    ncols = len(rows[0])

    fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=dpi, facecolor=fig_face)
    ax.set_facecolor(fig_face)
    ax.set_xlim(0, ncols)
    ax.set_ylim(0, nrows)
    ax.set_aspect("equal")
    ax.axis("off")

    for r in range(nrows):
        for c in range(ncols):
            x0, y0 = c, nrows - 1 - r
            ax.add_patch(
                Rectangle(
                    (x0, y0),
                    1,
                    1,
                    facecolor=cell_face,
                    edgecolor=edge,
                    linewidth=lw,
                )
            )
            text = rows[r][c]
            fs = fs_head if r == 0 or c == 0 else fs_cell
            ax.text(
                x0 + 0.5,
                y0 + 0.5,
                text,
                ha="center",
                va="center",
                fontsize=fs,
                color=text_c,
                family="sans-serif",
                wrap=False,
            )

    title = data.get("title")
    if title:
        title = _normalize_cell(title)
        fig.subplots_adjust(top=0.88)
        fig.suptitle(
            title,
            fontsize=fs_title + 1,
            color=title_c,
            y=0.96,
            family="sans-serif",
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        out_path, facecolor=fig_face, edgecolor="none", bbox_inches="tight"
    )
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description="Draw labeled grid from YAML.")
    p.add_argument("config", type=Path, help="Path to YAML config")
    p.add_argument(
        "-o", "--output", type=Path, required=True, help="Output PNG path"
    )
    args = p.parse_args()
    try:
        data = load_config(args.config)
        draw(data, args.output)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
