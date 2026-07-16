from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any

import pytest

from app.core.companion_harness.companion.models import ChatMessage
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.dreaming_consolidation import (
    DreamingDocumentKind,
    _DREAMING_DOCUMENT_UPDATE_TOOL_NAME,
    _SOUL_FROZEN_APPEARANCE_MARKER,
    consolidate_memory_during_dreaming,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    COMPANIONSHIP_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    USER_MD_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.utils.config import DreamingCuratorMode
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    UnusedLlmClient,
)

_DAILY_2026_01_02 = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist("2026-01-02")
_DAILY_2026_01_03 = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist("2026-01-03")


def _one_shot_llm_client(response: _FakeResponse) -> Any:
    class _OneShot:
        def chat_completion_unified(
            self,
            *,
            messages: list[dict[str, Any]],
            model: Any,
            tools: list[Any],
            tool_choice: str,
            langsmith_extra: dict[str, Any],
            high_reasoning: bool = False,
        ) -> _FakeResponse:
            assert messages
            assert tools
            assert tool_choice == "required"
            return response

        def resolve_model(self, role: str) -> Any:
            assert role == "memory"
            return object()

    return _OneShot()


def _never_run_complete_fn(messages: list[dict[str, Any]], role: str) -> str:
    raise AssertionError("complete_fn must not be called in one_shot mode")


@dataclass
class _FakeFn:
    name: str
    arguments: str


@dataclass
class _FakeToolCall:
    function: _FakeFn


@dataclass
class _FakeMessage:
    tool_calls: list[_FakeToolCall]


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeResponse:
    choices: list[_FakeChoice]


def _tool_call(name: str, payload: dict[str, object]) -> _FakeToolCall:
    return _FakeToolCall(
        function=_FakeFn(name=name, arguments=json.dumps(payload))
    )


def _one_shot_kind_for_path(rel: str) -> str:
    if rel.startswith("memory/daily/"):
        return DreamingDocumentKind.DAILY_GIST.value
    if rel == MEMORY_MD_REL:
        return DreamingDocumentKind.MEMORY.value
    if rel == USER_MD_REL:
        return DreamingDocumentKind.USER.value
    if rel == STYLE_MD_REL:
        return DreamingDocumentKind.STYLE.value
    if rel == SOUL_MD_REL:
        return DreamingDocumentKind.SOUL.value
    if rel == COMPANIONSHIP_MD_REL:
        return DreamingDocumentKind.COMPANIONSHIP.value
    return DreamingDocumentKind.MEMORY.value


def _one_shot_response_for_paths(
    paths: tuple[str, ...],
    *,
    body_suffix: str = " curated",
    content_changed: bool = True,
) -> _FakeResponse:
    calls: list[_FakeToolCall] = []
    for rel in paths:
        calls.append(
            _tool_call(
                _DREAMING_DOCUMENT_UPDATE_TOOL_NAME,
                {
                    "document_kind": _one_shot_kind_for_path(rel),
                    "relative_path": rel,
                    "content_changed": content_changed,
                    "body": f"{rel}{body_suffix}" if content_changed else "",
                    "changed_reason": "test",
                },
            )
        )
    return _FakeResponse(
        choices=[_FakeChoice(message=_FakeMessage(tool_calls=calls))]
    )


def _one_shot_response_mixed(
    changed_paths: tuple[str, ...],
    no_op_paths: tuple[str, ...],
    *,
    body_suffix: str = " curated",
) -> _FakeResponse:
    calls: list[_FakeToolCall] = []
    for rel in changed_paths:
        calls.append(
            _tool_call(
                _DREAMING_DOCUMENT_UPDATE_TOOL_NAME,
                {
                    "document_kind": _one_shot_kind_for_path(rel),
                    "relative_path": rel,
                    "content_changed": True,
                    "body": f"{rel}{body_suffix}",
                    "changed_reason": "changed",
                },
            )
        )
    for rel in no_op_paths:
        calls.append(
            _tool_call(
                _DREAMING_DOCUMENT_UPDATE_TOOL_NAME,
                {
                    "document_kind": _one_shot_kind_for_path(rel),
                    "relative_path": rel,
                    "content_changed": False,
                    "body": "",
                    "changed_reason": "no relevant signal",
                },
            )
        )
    return _FakeResponse(
        choices=[_FakeChoice(message=_FakeMessage(tool_calls=calls))]
    )


def _seed_memory_docs(store: MemoryStore) -> None:
    for rel in (
        MEMORY_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    ):
        store.write_document(rel, f"{rel} seed\n")


def test_consolidate_memory_during_dreaming_curates_applicable_docs(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-mem", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    rows = [
        ChatMessage(
            role="user",
            content="I like quiet mornings",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
        ChatMessage(
            role="assistant",
            content="I'll remember that gently.",
            ts="2026-01-02T09:01:00+00:00",
            uuid="a",
        ),
    ]
    roles: list[str] = []

    def complete_fn(messages: list[dict[str, object]], role: str) -> str:
        roles.append(role)
        return f"{role} curated"

    tool_bg_idle = Event()
    tool_bg_idle.set()
    assert (
        consolidate_memory_during_dreaming(
            store,
            rows,
            DreamingCuratorMode.SEQUENTIAL,
            complete_fn,
            UnusedLlmClient(),
            langsmith_extra={},
            tool_bg_idle_event=tool_bg_idle,
        )
        is True
    )
    assert roles == [
        "dreaming_day_summary",
        "memory",
        "user",
        "style",
        "soul",
        "companionship",
    ]
    daily = store.read_document(_DAILY_2026_01_02)
    assert daily == "dreaming_day_summary curated\n"
    assert store.read_document_if_exists("memory/2026-01-02.md") is None
    assert store.read_document(MEMORY_MD_REL) == "memory curated\n"
    assert store.read_document(USER_MD_REL) == "user curated\n"
    assert store.read_document(STYLE_MD_REL) == "style curated\n"
    assert store.read_document(SOUL_MD_REL) == "soul curated\n"
    assert store.read_document(COMPANIONSHIP_MD_REL) == "companionship curated\n"


def test_consolidate_memory_one_shot_writes_all_docs(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-one-shot", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    rows = [
        ChatMessage(
            role="user",
            content="hello",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
    ]
    required_paths = (
        _DAILY_2026_01_02,
        MEMORY_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    )
    response = _one_shot_response_for_paths(required_paths)

    tool_bg_idle = Event()
    tool_bg_idle.set()
    assert (
        consolidate_memory_during_dreaming(
            store,
            rows,
            DreamingCuratorMode.ONE_SHOT,
            _never_run_complete_fn,
            _one_shot_llm_client(response),
            langsmith_extra={},
            tool_bg_idle_event=tool_bg_idle,
        )
        is True
    )
    assert (
        store.read_document(_DAILY_2026_01_02)
        == f"{_DAILY_2026_01_02} curated\n"
    )
    assert store.read_document(MEMORY_MD_REL) == "MEMORY.md curated\n"
    assert store.read_document(USER_MD_REL) == "USER.md curated\n"
    assert store.read_document(STYLE_MD_REL) == "STYLE.md curated\n"
    assert store.read_document(SOUL_MD_REL) == "SOUL.md curated\n"
    assert (
        store.read_document(COMPANIONSHIP_MD_REL) == "COMPANIONSHIP.md curated\n"
    )


def test_consolidate_memory_one_shot_missing_tool_call_raises(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-missing", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    rows = [
        ChatMessage(
            role="user",
            content="hello",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
    ]
    response = _one_shot_response_for_paths((MEMORY_MD_REL,))

    tool_bg_idle = Event()
    tool_bg_idle.set()
    with pytest.raises(
        ValueError, match="missing required dreaming document updates"
    ):
        consolidate_memory_during_dreaming(
            store,
            rows,
            DreamingCuratorMode.ONE_SHOT,
            _never_run_complete_fn,
            _one_shot_llm_client(response),
            langsmith_extra={},
            tool_bg_idle_event=tool_bg_idle,
        )
    assert store.read_document(MEMORY_MD_REL) == "MEMORY.md seed\n"


def test_consolidate_memory_one_shot_duplicate_tool_call_raises(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-dup", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    rows = [
        ChatMessage(
            role="user",
            content="hello",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
    ]
    required_paths = (
        _DAILY_2026_01_02,
        MEMORY_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    )
    response = _one_shot_response_for_paths(required_paths + (MEMORY_MD_REL,))

    tool_bg_idle = Event()
    tool_bg_idle.set()
    with pytest.raises(ValueError, match="duplicate dreaming document update"):
        consolidate_memory_during_dreaming(
            store,
            rows,
            DreamingCuratorMode.ONE_SHOT,
            _never_run_complete_fn,
            _one_shot_llm_client(response),
            langsmith_extra={},
            tool_bg_idle_event=tool_bg_idle,
        )
    assert store.read_document(MEMORY_MD_REL) == "MEMORY.md seed\n"


def test_consolidate_memory_one_shot_all_no_op_raises(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-all-noop", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    rows = [
        ChatMessage(
            role="user",
            content="hello",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
    ]
    required_paths = (
        _DAILY_2026_01_02,
        MEMORY_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    )
    response = _one_shot_response_for_paths(
        required_paths,
        content_changed=False,
    )

    tool_bg_idle = Event()
    tool_bg_idle.set()
    with pytest.raises(
        ValueError, match="no content_changed=true dreaming document updates"
    ):
        consolidate_memory_during_dreaming(
            store,
            rows,
            DreamingCuratorMode.ONE_SHOT,
            _never_run_complete_fn,
            _one_shot_llm_client(response),
            langsmith_extra={},
            tool_bg_idle_event=tool_bg_idle,
        )
    assert store.read_document(MEMORY_MD_REL) == "MEMORY.md seed\n"


def test_consolidate_memory_one_shot_explicit_no_op_skips_unchanged_docs(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-noop", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    rows = [
        ChatMessage(
            role="user",
            content="hello",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
    ]
    changed_paths = (
        _DAILY_2026_01_02,
        MEMORY_MD_REL,
        USER_MD_REL,
    )
    no_op_paths = (
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    )
    response = _one_shot_response_mixed(changed_paths, no_op_paths)

    tool_bg_idle = Event()
    tool_bg_idle.set()
    assert (
        consolidate_memory_during_dreaming(
            store,
            rows,
            DreamingCuratorMode.ONE_SHOT,
            _never_run_complete_fn,
            _one_shot_llm_client(response),
            langsmith_extra={},
            tool_bg_idle_event=tool_bg_idle,
        )
        is True
    )
    assert (
        store.read_document(_DAILY_2026_01_02)
        == f"{_DAILY_2026_01_02} curated\n"
    )
    assert store.read_document(MEMORY_MD_REL) == "MEMORY.md curated\n"
    assert store.read_document(USER_MD_REL) == "USER.md curated\n"
    assert store.read_document(STYLE_MD_REL) == "STYLE.md seed\n"
    assert store.read_document(SOUL_MD_REL) == "SOUL.md seed\n"
    assert store.read_document(COMPANIONSHIP_MD_REL) == "COMPANIONSHIP.md seed\n"


def test_consolidate_memory_one_shot_preserves_soul_appearance(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-soul", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    store.write_document(
        SOUL_MD_REL,
        "# soul\n\n## 形象\n\nblue hair\n\n## 底线\n\nseed\n",
    )
    rows = [
        ChatMessage(
            role="user",
            content="boundary talk",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
    ]
    soul_body = (
        "# soul\n\n"
        f"{_SOUL_FROZEN_APPEARANCE_MARKER}\n\n"
        "## 底线\n\nupdated limit\n"
    )
    required_paths = (
        _DAILY_2026_01_02,
        MEMORY_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    )
    calls: list[_FakeToolCall] = []
    for rel in required_paths:
        body = soul_body if rel == SOUL_MD_REL else f"{rel} ok"
        calls.append(
            _tool_call(
                _DREAMING_DOCUMENT_UPDATE_TOOL_NAME,
                {
                    "document_kind": _one_shot_kind_for_path(rel),
                    "relative_path": rel,
                    "content_changed": True,
                    "body": body,
                    "changed_reason": "test",
                },
            )
        )
    response = _FakeResponse(
        choices=[_FakeChoice(message=_FakeMessage(tool_calls=calls))]
    )

    tool_bg_idle = Event()
    tool_bg_idle.set()
    consolidate_memory_during_dreaming(
        store,
        rows,
        DreamingCuratorMode.ONE_SHOT,
        _never_run_complete_fn,
        _one_shot_llm_client(response),
        langsmith_extra={},
        tool_bg_idle_event=tool_bg_idle,
    )
    soul = store.read_document(SOUL_MD_REL)
    assert "## 形象" in soul
    assert "blue hair" in soul
    assert "updated limit" in soul


def test_consolidate_memory_one_shot_multi_day_daily_gists(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-multi-day", "agent", tmp_path.name),
        repository=None,
    )
    _seed_memory_docs(store)
    rows = [
        ChatMessage(
            role="user",
            content="day one",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u1",
        ),
        ChatMessage(
            role="user",
            content="day two",
            ts="2026-01-03T09:00:00+00:00",
            uuid="u2",
        ),
    ]
    required_paths = (
        _DAILY_2026_01_02,
        _DAILY_2026_01_03,
        MEMORY_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        SOUL_MD_REL,
        COMPANIONSHIP_MD_REL,
    )
    response = _one_shot_response_for_paths(required_paths)

    tool_bg_idle = Event()
    tool_bg_idle.set()
    consolidate_memory_during_dreaming(
        store,
        rows,
        DreamingCuratorMode.ONE_SHOT,
        _never_run_complete_fn,
        _one_shot_llm_client(response),
        langsmith_extra={},
        tool_bg_idle_event=tool_bg_idle,
    )
    assert (
        store.read_document_if_exists(_DAILY_2026_01_02) is not None
    )
    assert (
        store.read_document_if_exists(_DAILY_2026_01_03) is not None
    )


def test_rewrite_companionship_md_uses_template_seed_when_missing(
    tmp_path: Path,
) -> None:
    from app.core.companion_harness.memory.dreaming_consolidation import (
        _rewrite_companionship_md,
    )
    from app.core.companion_harness.memory.memory_store_scope import (
        load_template_seed_text,
    )

    store = MemoryStore(
        scope=CompanionScope(
            "dream-companionship-seed", "agent", tmp_path.name
        ),
        repository=None,
    )
    store.write_document(MEMORY_MD_REL, "memory seed\n")
    template_seed = load_template_seed_text(COMPANIONSHIP_MD_REL)
    captured_user_blocks: list[str] = []

    def complete_fn(messages: list[dict[str, object]], role: str) -> str:
        assert role == "companionship"
        captured_user_blocks.append(str(messages[1]["content"]))
        return "companionship curated from template\n"

    _rewrite_companionship_md(
        store,
        user_text="Dreaming transcript slice:\nuser: hello",
        assistant_text="",
        complete_fn=complete_fn,
    )
    assert captured_user_blocks
    assert template_seed.strip() in captured_user_blocks[0]
    assert (
        store.read_document(COMPANIONSHIP_MD_REL)
        == "companionship curated from template\n"
    )
