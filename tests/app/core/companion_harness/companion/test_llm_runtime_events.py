from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.companion_harness.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.core.companion_harness.companion.llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
    exc_chain_includes_llm_inference_failure_root_causes,
    record_llm_inference_failure,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.runtime_events import read_runtime_events
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.llm.chat_completions import (
    OpenRouterInvalidJsonError,
    create_chat_completion_sync,
)


def test_record_llm_inference_failure_skips_without_bind(tmp_path) -> None:
    scope = CompanionScope("lr", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    record_llm_inference_failure(
        model="m/a",
        exc=CompanionLLMInferenceBackendError(
            client_message_en="x", provider_http_status=503
        ),
    )
    assert read_runtime_events(store, kinds={"llm_inference_failure"}, limit=5) == []


def test_create_chat_completion_sync_writes_llm_inference_failure(tmp_path) -> None:
    scope = CompanionScope("lr", "a", f"{tmp_path.name}-ev")
    store = MemoryStore(scope=scope, repository=None)
    bind = LlmRuntimeEventBind(
        memory_store=store,
        trace_id="tr-ev-1",
        user_msg_uuid="um-ev-1",
        phase="foreground_chat",
    )
    tok = companion_llm_runtime_event_bind_ctx.set(bind)
    try:

        class _ChatCompletions:
            @staticmethod
            def create(**kw):
                raise RuntimeError("simulated transport failure")

        client = SimpleNamespace(chat=SimpleNamespace(completions=_ChatCompletions))
        with pytest.raises(CompanionLLMInferenceBackendError):
            create_chat_completion_sync(
                client,
                model="model/ev-test",
                messages_payload=[{"role": "user", "content": "hi"}],
                tools=[],
            )
    finally:
        companion_llm_runtime_event_bind_ctx.reset(tok)

    rows = read_runtime_events(store, kinds={"llm_inference_failure"}, limit=5)
    assert len(rows) == 1
    assert rows[0]["kind"] == "llm_inference_failure"
    assert rows[0]["trace_id"] == "tr-ev-1"
    assert rows[0]["user_msg_uuid"] == "um-ev-1"
    assert rows[0]["phase"] == "foreground_chat"
    assert rows[0]["model"] == "model/ev-test"
    assert rows[0]["error_type"] == "CompanionLLMInferenceBackendError"


def test_exc_chain_detects_inference_errors() -> None:
    root = CompanionLLMInferenceBackendError(
        client_message_en="e", provider_http_status=502
    )
    assert exc_chain_includes_llm_inference_failure_root_causes(root) is True

    wrapped = RuntimeError("outer")
    wrapped.__cause__ = root
    assert exc_chain_includes_llm_inference_failure_root_causes(wrapped) is True

    oj = OpenRouterInvalidJsonError("bad json body")
    assert exc_chain_includes_llm_inference_failure_root_causes(oj) is True

    assert exc_chain_includes_llm_inference_failure_root_causes(RuntimeError("x")) is False
