"""
Playground model catalog entries exposed to the web UI.

CREATED_BY_AGENT
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.utils.models_catalog import (
    CHAT_IMAGE_GEN_MODELS,
    CHAT_TEXT_MODELS,
    GPT_IMAGE_1_5,
    NANO_BANANA,
    NANO_BANANA_2,
    NANO_BANANA_PRO,
    NEWAPI_NANO_BANANA_2,
    Z_IMAGE_TURBO,
)


class PlaygroundModality(StrEnum):
    TEXT = "text"
    IMAGE = "image"


class PlaygroundModelEntry(BaseModel):
    """One selectable model in the aggregator UI."""

    nickname: str = Field(description="Human label in the dropdown.")
    id_on_provider: str = Field(description="Provider model id sent to APIs.")
    modality: PlaygroundModality = Field(description="text or image tab.")
    notes: str = Field(description="Short hint for required inputs.", default="")


# Fal-hosted GPT Image edit (catalog GPT_IMAGE_1_5 id is OpenRouter-oriented).
FAL_GPT_IMAGE_1_5_EDIT_ID = "fal-ai/gpt-image-1.5/edit"


def build_playground_catalog() -> list[PlaygroundModelEntry]:
    text_entries = [
        PlaygroundModelEntry(
            nickname=m.nickname,
            id_on_provider=m.id_on_provider,
            modality=PlaygroundModality.TEXT,
            notes=m.notes or "",
        )
        for m in CHAT_TEXT_MODELS
    ]
    image_entries = [
        PlaygroundModelEntry(
            nickname=m.nickname,
            id_on_provider=m.id_on_provider,
            modality=PlaygroundModality.IMAGE,
            notes=m.notes or "",
        )
        for m in CHAT_IMAGE_GEN_MODELS
    ]
    image_entries.append(
        PlaygroundModelEntry(
            nickname="GPT Image 1.5 Edit (fal)",
            id_on_provider=FAL_GPT_IMAGE_1_5_EDIT_ID,
            modality=PlaygroundModality.IMAGE,
            notes=GPT_IMAGE_1_5.notes or "image_urls required for edit",
        )
    )
    image_entries.append(
        PlaygroundModelEntry(
            nickname=Z_IMAGE_TURBO.nickname,
            id_on_provider=Z_IMAGE_TURBO.id_on_provider,
            modality=PlaygroundModality.IMAGE,
            notes="text-to-image via fal",
        )
    )
    return text_entries + image_entries


WRAPPED_GEMINI_IMAGE_IDS = frozenset(
    {
        NANO_BANANA.id_on_provider,
        NANO_BANANA_PRO.id_on_provider,
        NEWAPI_NANO_BANANA_2.id_on_provider,
    }
)

GEMINI_IMAGE_IDS = WRAPPED_GEMINI_IMAGE_IDS | frozenset({NANO_BANANA_2.id_on_provider})
