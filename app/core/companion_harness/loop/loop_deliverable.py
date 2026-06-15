"""Loop deliverable value types (no queue or delivery imports)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.tools.tool_background import ToolOutputEvent


class LoopDeliverableKind(StrEnum):
    """Wide loop emission kinds mapped to ``DownlinkKind`` via projection."""

    INTERIM_REPLY = "interim_reply"
    BOOTSTRAP_INTERIM = "bootstrap_interim"
    FOREGROUND_TEXT = "foreground_text"
    TOOL_BACKGROUND = "tool_background"
    USER_REPLY = "user_reply"


@dataclass(frozen=True)
class LoopDeliverable:
    """One user-visible or auditable delivery from an agentic loop."""

    kind: LoopDeliverableKind
    assistant_text: str
    bootstrap_interim: BootstrapInterimOutput | None
    tool_output: ToolOutputEvent | None
    significance_meta: dict[str, Any] | None
    turn_recall: str | None
