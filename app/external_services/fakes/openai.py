"""Minimal OpenAI-compatible client fake for tests and scripted harness orchestration."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from PIL import Image

CHAT_COMPLETION_OBJECT = "chat.completion"
DEFAULT_FINISH_REASON = "stop"
DEFAULT_MODEL_NAME = "fake-model"
IMAGES_GENERATION_OBJECT = "images.response"
DEFAULT_IMAGE_SIZE: tuple[int, int] = (64, 64)
FINISH_REASON_TOOL_CALLS = "tool_calls"


class FakeOpenAIScriptExhaustedError(RuntimeError):
    """Raised when a scripted FakeOpenAI receives more create() calls than script steps."""


@dataclass(frozen=True)
class FakeToolCall:
    """One OpenAI-style function tool_call for a scripted step."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class FakeCompletionStep:
    """One programmed chat.completion response."""

    content: str = ""
    tool_calls: tuple[FakeToolCall, ...] = ()


def fake_step_text(text: str) -> FakeCompletionStep:
    """Build a scripted assistant text-only completion step."""
    return FakeCompletionStep(content=text)


def fake_step_tool_call(
    name: str,
    arguments: str,
    *,
    tool_call_id: str,
    content: str = "",
) -> FakeCompletionStep:
    """Build a scripted assistant step that returns one function tool_call."""
    return FakeCompletionStep(
        content=content,
        tool_calls=(
            FakeToolCall(id=tool_call_id, name=name, arguments=arguments),
        ),
    )


def fake_step_tool_calls(
    *calls: tuple[str, str, str],
) -> FakeCompletionStep:
    """Build a scripted step with multiple function tool_calls.

    Each call is ``(name, arguments, tool_call_id)``.
    """
    tool_calls = tuple(
        FakeToolCall(id=tool_call_id, name=name, arguments=arguments)
        for name, arguments, tool_call_id in calls
    )
    return FakeCompletionStep(tool_calls=tool_calls)


def fake_step_proactive_chat_envelope(
    *,
    output_to_user: bool,
    message: str,
) -> FakeCompletionStep:
    """Build a scripted step whose content is valid ``ProactiveChatEnvelope`` JSON."""
    payload = {
        "output_to_user": output_to_user,
        "message": message,
    }
    return FakeCompletionStep(content=json.dumps(payload))


def fake_step_dual_llm_envelope(
    *,
    user_facing_reply: str,
    output_to_user: bool,
    importance_round: int,
    importance_user_message: int,
    importance_assistant_message: int,
    turn_recall: str,
) -> FakeCompletionStep:
    """Build a scripted step whose content is valid ``DualLlmChatBranchEnvelope`` JSON."""
    payload = {
        "user_facing_reply": user_facing_reply,
        "output_to_user": output_to_user,
        "importance_round": importance_round,
        "importance_user_message": importance_user_message,
        "importance_assistant_message": importance_assistant_message,
        "turn_recall": turn_recall,
    }
    return FakeCompletionStep(content=json.dumps(payload))


@dataclass
class FakeChatMessage:
    role: str
    content: str
    tool_calls: list[Any] = field(default_factory=list)


@dataclass
class FakeChatChoice:
    index: int
    message: FakeChatMessage
    finish_reason: str = DEFAULT_FINISH_REASON


@dataclass
class FakeChatUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class FakeChatCompletionResponse:
    id: str
    created: int
    model: str
    object: str
    choices: list[FakeChatChoice]
    usage: FakeChatUsage


@dataclass
class FakeImageData:
    b64_json: str


@dataclass
class FakeImagesResponse:
    created: int
    model: str
    object: str
    data: list[FakeImageData]


def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create a deterministic, comparable representation of messages."""
    normalized: list[dict[str, Any]] = []
    for m in messages:
        role = (m.get("role") or "").strip()
        content = m.get("content")
        if isinstance(content, list):
            content_str = json.dumps(
                content, ensure_ascii=False, sort_keys=True
            )
        else:
            content_str = (content or "").strip()
        name = m.get("name")
        if name is not None:
            name = str(name).strip()
        normalized.append({"role": role, "content": content_str, "name": name})
    return normalized


def _make_request_key(messages: list[dict[str, Any]], model: str | None) -> str:
    normalized = _normalize_messages(messages)
    key = {
        "model": model or DEFAULT_MODEL_NAME,
        "messages": normalized,
    }
    return json.dumps(key, ensure_ascii=False, sort_keys=True)


def _tool_call_objects(tool_calls: tuple[FakeToolCall, ...]) -> list[Any]:
    return [
        SimpleNamespace(
            id=tc.id,
            type="function",
            function=SimpleNamespace(name=tc.name, arguments=tc.arguments),
        )
        for tc in tool_calls
    ]


def _completion_from_step(
    *,
    step: FakeCompletionStep,
    messages: list[dict[str, Any]],
    model: str | None,
) -> FakeChatCompletionResponse:
    tool_call_objs = _tool_call_objects(step.tool_calls)
    finish_reason = (
        FINISH_REASON_TOOL_CALLS if tool_call_objs else DEFAULT_FINISH_REASON
    )
    message = FakeChatMessage(
        role="assistant",
        content=step.content,
        tool_calls=tool_call_objs,
    )
    choice = FakeChatChoice(
        index=0, message=message, finish_reason=finish_reason
    )
    prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)
    completion_chars = len(step.content) + sum(
        len(tc.arguments) + len(tc.name) for tc in step.tool_calls
    )
    usage = FakeChatUsage(
        prompt_tokens=prompt_chars,
        completion_tokens=completion_chars,
        total_tokens=prompt_chars + completion_chars,
    )
    return FakeChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=model or DEFAULT_MODEL_NAME,
        object=CHAT_COMPLETION_OBJECT,
        choices=[choice],
        usage=usage,
    )


class _FakeCompletionsAPI:
    def __init__(self, client: FakeOpenAI) -> None:
        self._client = client

    def _resolve_step_or_content(
        self, messages: list[dict[str, Any]], model: str | None
    ) -> FakeCompletionStep | str:
        client = self._client
        if client._script:
            with client._script_lock:
                index = client._script_index
                if index >= len(client._script):
                    raise FakeOpenAIScriptExhaustedError(
                        f"FakeOpenAI script exhausted after {index} steps "
                        f"(script length={len(client._script)})"
                    )
                step = client._script[index]
                client._script_index = index + 1
            return step

        key = _make_request_key(messages, model)
        if key in client._responses_by_request:
            return client._responses_by_request[key]
        return client._random_content()

    def _build_response(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None,
        resolved: FakeCompletionStep | str,
    ) -> FakeChatCompletionResponse:
        if isinstance(resolved, FakeCompletionStep):
            return _completion_from_step(
                step=resolved, messages=messages, model=model
            )

        message = FakeChatMessage(role="assistant", content=resolved)
        choice = FakeChatChoice(index=0, message=message)
        prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)
        completion_chars = len(resolved)
        usage = FakeChatUsage(
            prompt_tokens=prompt_chars,
            completion_tokens=completion_chars,
            total_tokens=prompt_chars + completion_chars,
        )
        return FakeChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=model or DEFAULT_MODEL_NAME,
            object=CHAT_COMPLETION_OBJECT,
            choices=[choice],
            usage=usage,
        )

    def create(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> FakeChatCompletionResponse:
        if stream:
            raise NotImplementedError("FakeOpenAI does not support streaming.")

        resolved = self._resolve_step_or_content(messages, model)
        return self._build_response(
            messages=messages, model=model, resolved=resolved
        )


class _FakeAsyncCompletionsAPI:
    """Async ``create`` for ``AsyncLlmClient``; shares script index with sync API."""

    def __init__(self, sync_api: _FakeCompletionsAPI) -> None:
        self._sync_api = sync_api

    async def create(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> FakeChatCompletionResponse:
        if stream:
            raise NotImplementedError("FakeOpenAI does not support streaming.")

        return await asyncio.to_thread(
            self._sync_api.create,
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=stream,
            **kwargs,
        )


class _FakeAsyncChatAPI:
    def __init__(self, sync_api: _FakeCompletionsAPI) -> None:
        self.completions = _FakeAsyncCompletionsAPI(sync_api)


class _FakeAsyncOpenAIView:
    """Thin async surface over one ``FakeOpenAI`` (same script, shared index)."""

    def __init__(self, fake: FakeOpenAI) -> None:
        sync_completions = fake.chat.completions
        assert isinstance(sync_completions, _FakeCompletionsAPI)
        self.chat = _FakeAsyncChatAPI(sync_completions)


class _FakeChatAPI:
    def __init__(self, client: FakeOpenAI) -> None:
        self._client = client
        self.completions = _FakeCompletionsAPI(client)


class _FakeImagesAPI:
    def __init__(self, client: FakeOpenAI) -> None:
        self._client = client

    def generate(
        self,
        *,
        model: str | None = None,
        prompt: str,
        n: int = 1,
        response_format: str = "b64_json",
        size: str | None = None,
        **kwargs: Any,
    ) -> FakeImagesResponse:
        if response_format != "b64_json":
            raise NotImplementedError(
                "FakeOpenAI only supports response_format='b64_json'."
            )

        width, height = _parse_size(size) if size else DEFAULT_IMAGE_SIZE
        items: list[FakeImageData] = []
        count = int(n or 1)
        for i in range(count):
            img_bytes = _make_png_bytes(
                index=self._client._image_call_index + i,
                size=(width, height),
            )
            items.append(
                FakeImageData(
                    b64_json=base64.b64encode(img_bytes).decode("ascii")
                )
            )

        self._client._image_call_index += count
        return FakeImagesResponse(
            created=int(time.time()),
            model=model or DEFAULT_MODEL_NAME,
            object=IMAGES_GENERATION_OBJECT,
            data=items,
        )


class FakeOpenAI:
    """Test-focused OpenAI client fake with optional ordered completion script.

    - ``script``: pop one ``FakeCompletionStep`` per ``create()`` (thread-safe)
    - ``register_response``: legacy per-(model, messages) lookup when script is empty
    - Random content fallback when neither script nor registration matches
    """

    def __init__(
        self,
        *,
        seed: int | None = None,
        script: tuple[FakeCompletionStep, ...] = (),
    ) -> None:
        self._responses_by_request: dict[str, str] = {}
        self._script: tuple[FakeCompletionStep, ...] = script
        self._script_index: int = 0
        self._script_lock = threading.Lock()
        self._async_view: _FakeAsyncOpenAIView | None = None
        self.chat = _FakeChatAPI(self)
        self.images = _FakeImagesAPI(self)
        self._seed = seed
        if seed is not None:
            self._seed_prefix = f"{seed}-"
        else:
            self._seed_prefix = ""
        self._image_call_index = 0

    @property
    def script_index(self) -> int:
        """Number of script steps consumed so far."""
        return self._script_index

    @property
    def script_length(self) -> int:
        return len(self._script)

    @property
    def async_client(self) -> _FakeAsyncOpenAIView:
        """Async OpenAI-compatible view sharing this fake's script."""
        if self._async_view is None:
            self._async_view = _FakeAsyncOpenAIView(self)
        return self._async_view

    def register_response(
        self,
        *,
        messages: list[dict[str, Any]],
        content: str,
        model: str | None = None,
    ) -> None:
        """Register a deterministic text response for a given (model, messages)."""
        key = _make_request_key(messages, model)
        self._responses_by_request[key] = content

    def _random_content(self) -> str:
        return f"fake-response-{self._seed_prefix}{uuid.uuid4().hex}"


def _parse_size(size: str) -> tuple[int, int]:
    if not size:
        return DEFAULT_IMAGE_SIZE
    if "x" not in size:
        raise ValueError(f"Invalid size: {size!r}. Expect '<w>x<h>'.")
    w, h = size.split("x", 1)
    return int(w), int(h)


def _make_png_bytes(*, index: int, size: tuple[int, int]) -> bytes:
    width, height = size
    image = Image.new(
        "RGB",
        (width, height),
        color=((index * 40) % 255, (index * 70) % 255, (index * 110) % 255),
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


__all__ = [
    "FakeOpenAI",
    "FakeOpenAIScriptExhaustedError",
    "FakeCompletionStep",
    "FakeToolCall",
    "fake_step_text",
    "fake_step_tool_call",
    "fake_step_dual_llm_envelope",
    "fake_step_proactive_chat_envelope",
    "FakeChatCompletionResponse",
    "FakeChatChoice",
    "FakeChatMessage",
    "FakeChatUsage",
    "FakeImagesResponse",
    "FakeImageData",
]
