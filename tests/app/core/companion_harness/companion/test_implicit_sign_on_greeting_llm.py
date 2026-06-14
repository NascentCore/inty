"""Implicit sign-on greeting LLM timeout, retry, and WS preemption."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.llm_runtime_events import (
    record_llm_inference_failure,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import (
    run_companion_implicit_sign_on_greeting_turn,
)
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.core.companion_harness.companion.websocket_coordinator import (
    CompanionWebSocketCoordinator,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


class _FakeLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.calls: list[dict[str, Any]] = []

    def sync_client_for_route(self, route: str) -> object:
        return object()

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> Any:
        rec = dict(kwargs)
        if isinstance(rec.get("messages"), list):
            rec["messages"] = list(rec["messages"])
        self.calls.append(rec)
        msg = SimpleNamespace(content="greeting reply", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""

    async def chat_completion_with_retrial(
        self,
        *,
        max_attempts: int,
        per_attempt_timeout_sec: float,
        trace_id: str | None,
        attempt_log_label: str,
        model: GenAIModel | None,
        **kwargs: Any,
    ) -> Any:
        resolved = model or self.resolve_model("chat")
        model_id = resolved.id_on_provider
        resp = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self.chat_completion(model=resolved, **kwargs)
                    ),
                    timeout=per_attempt_timeout_sec,
                )
                break
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                record_llm_inference_failure(
                    model=model_id,
                    exc=exc,
                    foreground_timeout_sec=per_attempt_timeout_sec,
                )
                if attempt >= max_attempts:
                    raise
        assert resp is not None
        return resp


class _FlakyLLMClient(_FakeLLMClient):
    def __init__(self) -> None:
        super().__init__()
        self._failures_remaining = 1
        self.chat_completion_invocations = 0

    def chat_completion(self, **kwargs: Any) -> Any:
        self.chat_completion_invocations += 1
        if self._failures_remaining > 0:
            self._failures_remaining -= 1
            raise RuntimeError("transient provider error")
        return super().chat_completion(**kwargs)


class _SlowLLMClient(_FakeLLMClient):
    def __init__(self, *, block_sec: float) -> None:
        super().__init__()
        self._block_sec = block_sec
        self.chat_completion_invocations = 0

    def chat_completion(self, **kwargs: Any) -> Any:
        self.chat_completion_invocations += 1
        time.sleep(self._block_sec)
        return super().chat_completion(**kwargs)


def _seed_workspace(store: MemoryStore) -> None:
    store.write_document("IDENTITY.md", "identity")
    store.write_document("SOUL.md", "soul")
    store.write_document("USER.md", "user")
    store.write_document("MEMORY.md", "memory")
    store.write_document(
        "context.json",
        json.dumps({"context_mode": "intimate"}, indent=2) + "\n",
    )


def _idle_tool_bg() -> threading.Event:
    ev = threading.Event()
    ev.set()
    return ev


def _implicit_greeting_deps(
    store: MemoryStore,
    client: _FakeLLMClient,
) -> CompanionTurnDeps:
    bundle = ImplicitSignalBundle(user_signed_on=True)
    return CompanionTurnDeps(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        runtime_context=TurnRuntimeContext(
            channel=CompanionRuntimeChannel.APP,
            implicit_signal_bundle=bundle,
        ),
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        memory_bootstrap_type="NONE",
        background_output_sink=None,
        preset_user_msg_uuid=None,
        langsmith_parent_run_enabled=False,
        tool_bg_idle_event=_idle_tool_bg(),
        bootstrap_interim_output_sink=None,
        agentic_loop_channel=None,
    )


def test_implicit_sign_on_greeting_llm_timeout_retries_then_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.companion_harness.companion import turn as turn_mod

    feats = turn_mod.global_config_loaded_from_config_yaml.app.features
    monkeypatch.setattr(
        feats,
        "companion_implicit_sign_on_greeting_llm_timeout_sec",
        0.1,
    )
    monkeypatch.setattr(
        feats,
        "companion_implicit_sign_on_greeting_llm_max_attempts",
        2,
    )
    scope = CompanionScope("turn-t", "a", f"it-greet-timeout-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _SlowLLMClient(block_sec=0.25)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(
            run_companion_implicit_sign_on_greeting_turn(
                "",
                deps=_implicit_greeting_deps(store, client),
            )
        )

    assert client.chat_completion_invocations == 2


def test_implicit_sign_on_greeting_llm_retries_then_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.companion_harness.companion import turn as turn_mod

    monkeypatch.setattr(
        turn_mod.global_config_loaded_from_config_yaml.app.features,
        "companion_implicit_sign_on_greeting_llm_max_attempts",
        2,
    )
    scope = CompanionScope("turn-t", "a", f"it-greet-retry-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FlakyLLMClient()

    out = asyncio.run(
        run_companion_implicit_sign_on_greeting_turn(
            "",
            deps=_implicit_greeting_deps(store, client),
        )
    )

    assert out.assistant_text == "greeting reply"
    assert client.chat_completion_invocations == 2


def test_implicit_sign_on_greeting_llm_cancelled_skips_further_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.companion_harness.companion import turn as turn_mod

    monkeypatch.setattr(
        turn_mod.global_config_loaded_from_config_yaml.app.features,
        "companion_implicit_sign_on_greeting_llm_max_attempts",
        3,
    )
    scope = CompanionScope("turn-t", "a", f"it-greet-cancel-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FlakyLLMClient()
    wait_calls = 0

    async def _counting_wait_for(coro: Any, timeout: float) -> Any:
        nonlocal wait_calls
        wait_calls += 1
        if wait_calls == 2:
            raise asyncio.CancelledError()
        return await coro

    async def _exercise() -> None:
        with patch(
            "app.core.companion_harness.companion.llm_client.asyncio.wait_for",
            side_effect=_counting_wait_for,
        ):
            with pytest.raises(asyncio.CancelledError):
                await run_companion_implicit_sign_on_greeting_turn(
                    "",
                    deps=_implicit_greeting_deps(store, client),
                )

    asyncio.run(_exercise())
    assert wait_calls == 2
    assert client.chat_completion_invocations == 1


@pytest.mark.asyncio
async def test_cancel_implicit_greeting_turn_if_running() -> None:
    started = asyncio.Event()

    async def _slow_greeting() -> None:
        started.set()
        await asyncio.sleep(3600)

    coordinator = CompanionWebSocketCoordinator.for_current_loop()
    task = asyncio.create_task(_slow_greeting())
    coordinator.register_implicit_greeting_turn(task)
    await started.wait()
    cancelled = await coordinator.cancel_implicit_greeting_turn_if_running()
    assert cancelled is True
    assert task.done()
    assert coordinator._implicit_greeting_turn_task is None
