"""LangSmith observability slice for one companion turn's human-facing channel.

Pure harness module: builds parent RunTree fragments and child ``langsmith_extra``
dicts from ``CompanionRuntimeChannel``. Session-level resolution lives in
``app.services.agentic_companion.langsmith_channel_resolve``.


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

from app.core.companion_harness.llm.langsmith_invocation_extra import (
    INTY_RUNTIME_CHANNEL_METADATA_KEY,
    INTY_RUNTIME_CHANNEL_SOURCE_METADATA_KEY,
    dreaming_consolidation_langsmith_extra,
    invocation_extra,
    tool_call_langsmith_extra,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)


class LangsmithChannelSource(StrEnum):
    """How ``runtime_channel`` was chosen for LangSmith metadata."""

    EXPLICIT_TURN = "explicit_turn"
    SCOPE_REGISTRY = "scope_registry"
    USER_REGISTRY = "user_registry"
    DEFAULT_APP = "default_app"


@dataclass(frozen=True)
class CompanionTurnLangsmithSlice:
    """Channel tags for companion LangSmith parent runs and LLM child spans."""

    runtime_channel: CompanionRuntimeChannel
    channel_source: LangsmithChannelSource

    @classmethod
    def from_runtime_context(
        cls, runtime_context: TurnRuntimeContext
    ) -> Self:
        return cls.from_channel(
            runtime_context.channel,
            LangsmithChannelSource.EXPLICIT_TURN,
        )

    @classmethod
    def from_channel(
        cls,
        channel: CompanionRuntimeChannel,
        source: LangsmithChannelSource,
    ) -> Self:
        return cls(runtime_channel=channel, channel_source=source)

    @classmethod
    def app_default(cls) -> Self:
        """Explicit APP slice for tests and callers without ``TurnRuntimeContext``."""
        return cls.from_channel(
            CompanionRuntimeChannel.APP,
            LangsmithChannelSource.DEFAULT_APP,
        )

    def _channel_metadata(self) -> dict[str, Any]:
        return {
            INTY_RUNTIME_CHANNEL_METADATA_KEY: self.runtime_channel.value,
            INTY_RUNTIME_CHANNEL_SOURCE_METADATA_KEY: self.channel_source.value,
        }

    def parent_inputs_fragment(self) -> dict[str, Any]:
        return {"runtime_channel": self.runtime_channel.value}

    def parent_metadata_fragment(self) -> dict[str, Any]:
        return dict(self._channel_metadata())

    def parent_tags(self) -> list[str]:
        return [f"runtime_channel_{self.runtime_channel.value}"]

    def foreground_invocation_extra(
        self,
        *,
        source: str,
        extra_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        merged = dict(self._channel_metadata())
        if extra_metadata:
            merged.update(extra_metadata)
        return invocation_extra(source=source, extra_metadata=merged)

    def tool_call_extra(
        self,
        *,
        phase_suffix: str,
        extra_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        merged = dict(self._channel_metadata())
        if extra_metadata:
            merged.update(extra_metadata)
        return tool_call_langsmith_extra(
            phase_suffix=phase_suffix,
            extra_metadata=merged,
        )

    def dreaming_consolidation_extra(self, *, model_role: str) -> dict[str, Any]:
        base = dreaming_consolidation_langsmith_extra(model_role=model_role)
        meta = dict(base.get("metadata") or {})
        meta.update(self._channel_metadata())
        out = dict(base)
        out["metadata"] = meta
        return out
