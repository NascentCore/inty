"""Tool return string for Fal image tools: user-facing summary vs index metadata."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools import (
    fal_z_image_tool as fal_z_image_tool_mod,
)
from app.core.companion_harness.tools.image_gate import list_image_asset_records


def _store(ws: Path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("fal-display", "c", str(ws.resolve())),
        repository=None,
    )


@pytest.mark.asyncio
async def test_generate_image_tool_text_lists_prompt_omits_internal_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_item = SimpleNamespace(
        gcs_http_url="https://storage.example.invalid/out.png",
        gcs_uri="gs://bucket/out.png",
        size=SimpleNamespace(width=1024, height=576),
    )
    monkeypatch.setattr(
        fal_z_image_tool_mod,
        "_z_image_turbo_call",
        lambda *_a, **_k: [fake_item],
    )
    ws = tmp_path / "ws"
    ws.mkdir()
    store = _store(ws)
    out = await fal_z_image_tool_mod.run_generate_image_z_image_turbo(
        store,
        prompt="red barn at dusk",
        persona_revision_id="abc123deadbeef01",
    )
    assert "Image prompt:\nred barn at dusk" in out
    assert "SUCCESS: generate_image finished." in out
    assert "Generated 1 image(s)." in out
    assert "persona_revision_id=" not in out
    assert "asset_id=" not in out
    assert "gcs_http_url=" not in out
    rows = list_image_asset_records(store)
    assert len(rows) == 1
    assert rows[0].get("persona_revision_id") == "abc123deadbeef01"
    assert (
        rows[0].get("gcs_http_url") == "https://storage.example.invalid/out.png"
    )
