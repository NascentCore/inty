"""Smoke tests: LivingSphere curator MemDoc paths use MemoryStoreScopePaths (#3413).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.living_sphere_curator import (
    compact_living_sphere_batch,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.living_sphere.models import LivingSphereUpdate


def test_compact_living_sphere_batch_uses_scope_living_sphere_md(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("curator-scope", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel_md = DEFAULT_MEMORY_STORE_SCOPE_PATHS.living_sphere_md
    store.write_document(rel_md, "# LIVING SPHERE\n\n「对用户表达」虚拟家。\n")
    update = LivingSphereUpdate.model_validate(
        {
            "update_id": "u1",
            "change_request": "add a reading nook",
            "source": "chat_tool",
        }
    )

    def _complete(_messages: list, _role: str) -> str:
        return (
            "# LIVING SPHERE\n\n"
            "世界：阅读角与窗边的书架，氛围安静，适合长时间阅读与写作。"
            "锚点：窗景与暖色灯光。\n"
            "「对用户表达」欢迎来虚拟书房坐坐，只存在于 TechnoCore 私人空间，"
            "不会假装在你身边的物理位置。\n"
        )

    compact_living_sphere_batch(store, [update], _complete)
    body = store.read_document(rel_md)
    assert "阅读角" in body
