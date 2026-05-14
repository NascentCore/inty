"""Minimal script to verify a GCP service account JSON can call Vertex AI Gemini for text chat."""

from __future__ import annotations

import json
import os
import sys
from typing import Annotated

import cyclopts
from google import genai
from google.genai import types
from google.genai.errors import ClientError

from app.utils.models_catalog import ALL_GEMINI_MODELS, ModelAPIProvider

PROMPT = "Who are you?"
# Use global so gemini-3-pro-image-preview is available (it only supports global per Vertex AI docs).
LOCATION = "global"


def main(
    credentials: Annotated[
        str,
        cyclopts.Parameter(help="Path to GCP service account JSON key file."),
    ],
    count: Annotated[
        int,
        cyclopts.Parameter(
            name="--count",
            help="Number of generate_content calls per model (repeat to incur more charges).",
        ),
    ] = 1,
) -> None:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials

    with open(credentials) as f:
        project_id = json.load(f)["project_id"]

    vertex_gemini = [
        m for m in ALL_GEMINI_MODELS if m.provider == ModelAPIProvider.GOOGLE_VERTEX_AI
    ]
    if not vertex_gemini:
        print("No Vertex AI Gemini models in catalog.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(vertexai=True, project=project_id, location=LOCATION)
    failed: list[str] = []
    for model in vertex_gemini:
        model_id = model.id_on_provider
        if model_id.startswith("gemini-live-"):
            print(f"--- {model.nickname} ({model_id}) ---")
            print("(Live API model; skipping generate_content test)")
            print()
            continue
        print(f"--- {model.nickname} ({model_id}) ---")
        try:
            for i in range(count):
                response = client.models.generate_content(
                    model=model_id,
                    contents=PROMPT,
                    config=types.GenerateContentConfig(),
                )
                if count > 1:
                    print(f"[{i + 1}/{count}] {response.text}")
                else:
                    print(response.text)
        except ClientError as e:
            print(f"FAILED: {e}", file=sys.stderr)
            failed.append(model_id)
        print()

    if failed:
        print(f"Models that failed: {failed}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cyclopts.run(main)
