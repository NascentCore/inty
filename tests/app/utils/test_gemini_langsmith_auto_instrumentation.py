"""Auto-instrumentation test for Gemini + LangSmith: uses wrap_gemini, then queries LangSmith with retries for write delay.

Requires LANGSMITH_PROJECT and GCP credentials (app.gcp_service_account_key) when run locally (noci).

cp devops/config.yaml.local config.yaml
# 拷贝 GCP 凭证到本地
cp ~/Workspace/NascentCore/inty/.secrets/inty-backend-key.json .secrets
"""

from __future__ import annotations

import datetime
import os
import time
import uuid

import langsmith
import pytest
from google import genai
from google.genai import types
from langsmith import Client as LangSmithClient
from langsmith import wrappers

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.gemini import create_google_genai_client
from tests.langsmith import find_run_contains_random_string


def get_wrapped_genai_client():
    gemini_client = create_google_genai_client()

    return wrappers.wrap_gemini(
        gemini_client,
        tracing_extra={
            "tags": ["gemini", "python"],
            "metadata": {
                "integration": "google-genai",
                "application": "inty-backend",
                "environment": "local",
            },
        },
    )


def _make_traced_gemini_call(wrapped_client, *, use_plain_text: bool):
    """执行一次带 trace 的 Gemini 调用，返回 (start_time, random_str)。"""
    start_time = datetime.datetime.now(datetime.timezone.utc)
    random_str = str(uuid.uuid4()) + " yes or no?"
    if use_plain_text:
        contents = random_str
    else:
        contents = [types.Part.from_text(text=random_str)]
    wrapped_client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(max_output_tokens=10),
    )
    return start_time, random_str


@pytest.mark.noci
def test_gemini_text_contents_langsmith_integration():
    wrapped_client = get_wrapped_genai_client()
    start_time, random_str = _make_traced_gemini_call(
        wrapped_client, use_plain_text=True
    )
    assert (
        find_run_contains_random_string(start_time, random_str) is not None
    ), f"No run found with the random string: {random_str}"


@pytest.mark.noci
def test_gemini_text_part_contents_langsmith_integration():
    """当前 wrap_gemini 不会把 types.Part 形式的 contents 序列化到 LangSmith run 的 inputs 中，故预期查不到 run。"""
    wrapped_client = get_wrapped_genai_client()
    start_time, random_str = _make_traced_gemini_call(
        wrapped_client, use_plain_text=False
    )
    assert (
        find_run_contains_random_string(start_time, random_str) is None
    ), "追踪无法抓取 types.part 结构体的输入"
