from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# Constants for predictable structure and to avoid magic strings
CHAT_COMPLETION_OBJECT = "chat.completion"
DEFAULT_FINISH_REASON = "stop"
DEFAULT_MODEL_NAME = "fake-model"


@dataclass
class FakeChatMessage:
    role: str
    content: str


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
    choices: List[FakeChatChoice]
    usage: FakeChatUsage


def _normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create a deterministic, comparable representation of messages."""
    normalized: List[Dict[str, Any]] = []
    for m in messages:
        role = (m.get("role") or "").strip()
        content = m.get("content")
        # Content can be list (multimodal), allow pass-through but stringify for keying
        if isinstance(content, list):
            # Ensure deterministic order/stringification
            content_str = json.dumps(content, ensure_ascii=False, sort_keys=True)
        else:
            content_str = (content or "").strip()
        name = m.get("name")
        if name is not None:
            name = str(name).strip()
        normalized.append({"role": role, "content": content_str, "name": name})
    return normalized


def _make_request_key(messages: List[Dict[str, Any]], model: Optional[str]) -> str:
    normalized = _normalize_messages(messages)
    key = {
        "model": model or DEFAULT_MODEL_NAME,
        "messages": normalized,
    }
    # Stable JSON representation used as a dict key
    return json.dumps(key, ensure_ascii=False, sort_keys=True)


class _FakeCompletionsAPI:
    def __init__(self, client: "FakeOpenAI") -> None:
        self._client = client

    def create(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> FakeChatCompletionResponse:
        if stream:
            raise NotImplementedError("FakeOpenAI does not support streaming.")

        # Lookup specific response or fall back to random
        key = _make_request_key(messages, model)
        if key in self._client._responses_by_request:  # noqa: SLF001 (private access in test fake)
            content = self._client._responses_by_request[key]
        else:
            content = self._client._random_content()

        # Minimal yet OpenAI-like response structure
        message = FakeChatMessage(role="assistant", content=content)
        choice = FakeChatChoice(index=0, message=message)

        # Naive token accounting based on character length (sufficient for tests)
        prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)
        completion_chars = len(content)
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


class _FakeChatAPI:
    def __init__(self, client: "FakeOpenAI") -> None:
        self._client = client
        self.completions = _FakeCompletionsAPI(client)


class FakeOpenAI:
    """A minimal, test-focused fake of the OpenAI client.

    - Returns random content for unspecified requests
    - Returns user-registered content for specific (model, messages) requests
    - Exposes attribute path: .chat.completions.create(...)
    """

    def __init__(self, *, seed: Optional[int] = None) -> None:
        # Mapping: request_key -> response_content
        self._responses_by_request: Dict[str, str] = {}
        self.chat = _FakeChatAPI(self)
        # Optional seed can be used by caller to stabilize randomness if desired
        self._seed = seed
        if seed is not None:
            # Use UUID namespace variation based on seed to keep it simple
            self._seed_prefix = f"{seed}-"
        else:
            self._seed_prefix = ""

    def register_response(
        self,
        *,
        messages: List[Dict[str, Any]],
        content: str,
        model: Optional[str] = None,
    ) -> None:
        """Register a deterministic response for a given (model, messages)."""
        key = _make_request_key(messages, model)
        self._responses_by_request[key] = content

    # Helpers
    def _random_content(self) -> str:
        # Make it obviously fake while practically unique per call
        return f"fake-response-{self._seed_prefix}{uuid.uuid4().hex}"


__all__ = [
    "FakeOpenAI",
    "FakeChatCompletionResponse",
    "FakeChatChoice",
    "FakeChatMessage",
    "FakeChatUsage",
] 
