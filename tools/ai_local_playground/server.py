"""
FastAPI application for the local AI playground.

CREATED_BY_AGENT
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tools.ai_local_playground.api_models import (
    PlaygroundCatalogResponse,
    PlaygroundHealthResponse,
    PlaygroundImageRequest,
    PlaygroundImageResponse,
    PlaygroundTextRequest,
    PlaygroundTextResponse,
)
from tools.ai_local_playground.catalog import build_playground_catalog
from tools.ai_local_playground.inference import (
    PlaygroundImageInput,
    PlaygroundTextInput,
    run_playground_image,
    run_playground_text,
)
from tools.ai_local_playground.resolve_model import (
    resolve_playground_image_model_id,
    resolve_playground_text_model_id,
)

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Inty AI Local Playground", version="0.1.0")

    @app.get("/api/health", response_model=PlaygroundHealthResponse)
    def health() -> PlaygroundHealthResponse:
        config_path = (
            os.environ.get("INTY_CONFIG_YAML") or "config.yaml"
        ).strip() or "config.yaml"
        return PlaygroundHealthResponse(
            openrouter_key_set=bool(
                os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
            ),
            fal_key_set=bool(os.getenv("FAL_KEY")),
            config_path=config_path,
        )

    @app.get("/api/models", response_model=PlaygroundCatalogResponse)
    def list_models() -> PlaygroundCatalogResponse:
        entries = build_playground_catalog()
        models = [
            {
                "nickname": e.nickname,
                "id_on_provider": e.id_on_provider,
                "modality": e.modality.value,
                "notes": e.notes,
            }
            for e in entries
        ]
        return PlaygroundCatalogResponse(models=models)

    @app.post("/api/text", response_model=PlaygroundTextResponse)
    def text_chat(body: PlaygroundTextRequest) -> PlaygroundTextResponse:
        model_id = resolve_playground_text_model_id(body.model_id)
        inp = PlaygroundTextInput(
            model_id=model_id,
            user_message=body.user_message,
            system_message=body.system_message,
        )
        try:
            payload = run_playground_text(inp)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return PlaygroundTextResponse(**payload)

    @app.post("/api/image", response_model=PlaygroundImageResponse)
    async def image_generate(
        body: PlaygroundImageRequest,
    ) -> PlaygroundImageResponse:
        model_id = resolve_playground_image_model_id(body.model_id)
        urls = tuple(u for u in body.reference_image_urls if u)
        inp = PlaygroundImageInput(
            model_id=model_id,
            prompt=body.prompt,
            reference_image_urls=urls,
            system_instruction=body.system_instruction,
            num_images=body.num_images,
            input_fidelity=body.input_fidelity,
        )
        try:
            payload = await run_playground_image(inp)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return PlaygroundImageResponse(**payload)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    return app
