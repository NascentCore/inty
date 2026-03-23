"""
Build cartesian manifest for experiment cells.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .schema import (
    ExperimentManifest,
    GenerationConfig,
    ManifestItem,
    PersonaRecord,
    StimulusRecord,
)


def build_manifest(
    *,
    model_ids: Iterable[str],
    personas: list[PersonaRecord],
    stimuli: list[StimulusRecord],
    repeats_per_cell: int,
    generation: GenerationConfig,
) -> ExperimentManifest:
    model_id_list = list(model_ids)
    run_seed = (
        f"{','.join(model_id_list)}|{len(personas)}|{len(stimuli)}|"
        f"{repeats_per_cell}|{generation.temperature}|{generation.top_p}|{generation.max_tokens}"
    )
    run_id = f"run-{hashlib.sha256(run_seed.encode('utf-8')).hexdigest()[:12]}"
    items: list[ManifestItem] = []
    idx = 1
    for model_id in model_id_list:
        for persona in personas:
            for stimulus in stimuli:
                for repeat_index in range(1, repeats_per_cell + 1):
                    items.append(
                        ManifestItem(
                            run_id=run_id,
                            task_id=f"task-{idx:07d}",
                            model_id=model_id,
                            persona=persona,
                            stimulus=stimulus,
                            persona_id=persona.persona_id,
                            stimulus_id=stimulus.stimulus_id,
                            repeat_index=repeat_index,
                            temperature=generation.temperature,
                            top_p=generation.top_p,
                            max_tokens=generation.max_tokens,
                        )
                    )
                    idx += 1

    return ExperimentManifest(
        run_id=run_id,
        created_at=datetime.now(UTC),
        model_ids=model_id_list,
        personas_count=len(personas),
        stimuli_count=len(stimuli),
        repeats_per_cell=repeats_per_cell,
        generation=generation.model_dump(mode="python"),
        items=items,
        total_cells=len(items),
    )


def save_manifest(path: Path, manifest: ExperimentManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
