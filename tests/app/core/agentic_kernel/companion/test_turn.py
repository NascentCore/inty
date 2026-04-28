from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.core.agentic_kernel.companion.llm_client import (
    LLM_SCENE_INNER_TICK,
    CompanionLLMConfig,
)
from app.core.agentic_kernel.companion.memory_store import MemoryStore
from app.core.agentic_kernel.companion.models import INNER_TICK_SYNTHETIC_USER_TEXT
from app.core.agentic_kernel.companion.turn import run_turn


class _FakeLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.calls: list[dict[str, Any]] = []

    def _resolve_model(self, role: str) -> str:
        return f"test/{role}"

    def chat_completion(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        msg = SimpleNamespace(content="inner reply", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def _seed_workspace(store: MemoryStore) -> None:
    store.write_document("IDENTITY.md", "identity")
    store.write_document("SOUL.md", "soul")
    store.write_document("USER.md", "user")
    store.write_document("MEMORY.md", "memory")


def test_run_turn_inner_tick_persists_synthetic_turn_metadata(tmp_path: Path) -> None:
    store = MemoryStore(workspace_root=tmp_path, repository=None)
    _seed_workspace(store)
    client = _FakeLLMClient()

    out = asyncio.run(
        run_turn(
            tmp_path,
            "caller text should be replaced",
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            inner_tick_turn=True,
        )
    )

    assert out.assistant_text == "inner reply"
    assert client.calls[0]["scene"] == LLM_SCENE_INNER_TICK

    rows = [
        json.loads(line)
        for line in store.read_document("transcript.jsonl").strip().splitlines()
    ]
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == INNER_TICK_SYNTHETIC_USER_TEXT
    assert rows[0]["inner_tick"] is True
    assert rows[1]["role"] == "assistant"
    assert rows[1]["source"] == "inner_tick"
