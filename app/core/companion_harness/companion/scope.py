"""Logical companion session scope (replaces implicit Path semantics for registry keys).

TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout). — #3409
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanionScope:
    user_id: str
    companion_id: str
    chat_id: str

    def registry_key(self) -> str:
        return f"{self.user_id}:{self.companion_id}:{self.chat_id}"
