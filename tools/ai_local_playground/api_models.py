"""
HTTP request/response models for the local playground API.

CREATED_BY_AGENT
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlaygroundCatalogResponse(BaseModel):
    models: list[dict[str, str]] = Field(description="Selectable models for the UI.")


class PlaygroundTextRequest(BaseModel):
    model_id: str = Field(description="OpenRouter model id or catalog nickname.")
    user_message: str = Field(description="User turn content.")
    system_message: str = Field(description="Optional system prompt.", default="")


class PlaygroundTextResponse(BaseModel):
    model: str
    nickname: str
    content: str
    usage: dict[str, Any] | None
    elapsed_ms: float


class PlaygroundImageRequest(BaseModel):
    model_id: str = Field(description="Provider model id or nickname.")
    prompt: str = Field(description="Image generation prompt.")
    reference_image_urls: list[str] = Field(
        description="HTTP(S) reference image URLs (edit / i2i).",
        default_factory=list,
    )
    system_instruction: str = Field(
        description="Gemini system instruction (Nano Banana).",
        default="",
    )
    num_images: int = Field(description="Number of images to generate.", ge=1, le=4)
    input_fidelity: str = Field(
        description="gpt-image-1.5/edit only: high or low.",
        default="low",
    )


class PlaygroundImageResponse(BaseModel):
    model: str
    backend: str
    images: list[dict[str, Any]]
    elapsed_ms: float


class PlaygroundHealthResponse(BaseModel):
    ok: bool = True
    openrouter_key_set: bool
    fal_key_set: bool
    config_path: str
