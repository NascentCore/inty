"""
Figure placeholder generation for framework stage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def generate_figure_placeholders(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    names: Iterable[str] = (
        "model_distance_heatmap.txt",
        "model_invariance_bar.txt",
        "gemini_family_clustering.txt",
    )
    created: list[Path] = []
    for name in names:
        path = output_dir / name
        path.write_text(
            "Placeholder artifact.\n"
            "Real plotting will be enabled in full experiment phase.\n",
            encoding="utf-8",
        )
        created.append(path)
    return created
