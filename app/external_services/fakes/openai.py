from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import base64
import io
from PIL import Image

# Constants for predictable structure and to avoid magic strings
CHAT_COMPLETION_OBJECT = "chat.completion"
DEFAULT_FINISH_REASON = "stop"
DEFAULT_MODEL_NAME = "fake-model"
IMAGES_GENERATION_OBJECT = "images.response"
DEFAULT_IMAGE_SIZE: Tuple[int, int] = (64, 64)


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


@dataclass
class FakeImageData:
    b64_json: str


@dataclass
class FakeImagesResponse:
    created: int
    model: str
    object: str
    data: List[FakeImageData]


def _normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create a deterministic, comparable representation of messages."""
    normalized: List[Dict[str, Any]] = []
    for m in messages:
        role = (m.get("role") or "").strip()
        content = m.get("content")
        # Content can be list (multimodal), allow pass-through but stringify for keying
        if isinstance(content, list):
            # Ensure deterministic order/stringification
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


def _make_request_key(
    messages: List[Dict[str, Any]], model: Optional[str]
) -> str:
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

    def _build_response(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
    ) -> FakeChatCompletionResponse:
        key = _make_request_key(messages, model)
        if (
            key in self._client._responses_by_request
        ):  # noqa: SLF001 (private access in test fake)
            content = self._client._responses_by_request[key]
        else:
            content = self._client._random_content()

        message = FakeChatMessage(role="assistant", content=content)
        choice = FakeChatChoice(index=0, message=message)

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
        return self._build_response(messages=messages, model=model)

    async def acreate(
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
        return self.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=stream,
            **kwargs,
        )


class _FakeChatAPI:
    def __init__(self, client: "FakeOpenAI") -> None:
        self._client = client
        self.completions = _FakeCompletionsAPI(client)


class _FakeImagesAPI:
    def __init__(self, client: "FakeOpenAI") -> None:
        self._client = client

    def generate(
        self,
        *,
        model: Optional[str] = None,
        prompt: str,
        n: int = 1,
        response_format: str = "b64_json",
        size: Optional[str] = None,
        **kwargs: Any,
    ) -> FakeImagesResponse:
        if response_format != "b64_json":
            raise NotImplementedError(
                "FakeOpenAI only supports response_format='b64_json'."
            )

        width, height = _parse_size(size) if size else DEFAULT_IMAGE_SIZE
        items: List[FakeImageData] = []
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
    """A minimal, test-focused fake of the OpenAI client.

    - Returns random content for unspecified requests
    - Returns user-registered content for specific (model, messages) requests
    - Exposes attribute path: .chat.completions.create(...)
    """

    def __init__(self, *, seed: Optional[int] = None) -> None:
        # Mapping: request_key -> response_content
        self._responses_by_request: Dict[str, str] = {}
        self.chat = _FakeChatAPI(self)
        self.images = _FakeImagesAPI(self)
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

    _image_call_index: int = 0


def _parse_size(size: str) -> Tuple[int, int]:
    if not size:
        return DEFAULT_IMAGE_SIZE
    if "x" not in size:
        raise ValueError(f"Invalid size: {size!r}. Expect '<w>x<h>'.")
    w, h = size.split("x", 1)
    return int(w), int(h)


def _make_png_bytes(*, index: int, size: Tuple[int, int]) -> bytes:
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
    "FakeChatCompletionResponse",
    "FakeChatChoice",
    "FakeChatMessage",
    "FakeChatUsage",
    "FakeImagesResponse",
    "FakeImageData",
]
