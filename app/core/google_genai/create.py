"""Compatibility entrypoint for constructing the shared Google GenAI client.

The canonical config adapter lives in ``app.utils.gemini`` and delegates low-level
SDK construction to the agentic kernel Gemini provider cache.
"""

from __future__ import annotations

from typing import Any

from app.utils.gemini import create_google_genai_client


def create_genai_client() -> Any:
    """Return the canonical Vertex-backed Google GenAI client."""
    return create_google_genai_client()
