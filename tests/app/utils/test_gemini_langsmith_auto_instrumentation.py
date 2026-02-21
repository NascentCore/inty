<<<<<<< HEAD
"""Auto-instrumentation test for Gemini + LangSmith: uses wrap_gemini, then queries LangSmith with retries for write delay.

Requires LANGSMITH_PROJECT and GCP credentials (app.gcp_service_account_key) when run locally (noci).

cp devops/config.yaml.local config.yaml
# 拷贝 GCP 凭证到本地
cp ~/Workspace/NascentCore/inty/.secrets/inty-backend-key.json .secrets
"""
=======
"""Auto-instrumentation test for Gemini + LangSmith: uses wrap_gemini, then queries LangSmith with retries for write delay."""
>>>>>>> b46472d7 (减少递进层级)

from __future__ import annotations

import datetime
import os
<<<<<<< HEAD
import time
=======
>>>>>>> b46472d7 (减少递进层级)
import uuid

import langsmith
import pytest
from google import genai
from google.genai import types
from langsmith import Client as LangSmithClient
from langsmith import wrappers

from app.core.config import global_config_loaded_from_config_yaml

# 轮询 LangSmith 时的尝试次数与每页 run 数量（用于写入延迟）
_LANGSMITH_POLL_ATTEMPTS = 10
_LANGSMITH_RUNS_PAGE_SIZE = 10
<<<<<<< HEAD
_LANGSMITH_POLL_SLEEP_SECONDS = 2
=======
>>>>>>> b46472d7 (减少递进层级)


def get_wrapped_genai_client():
    credentials_path = (
        global_config_loaded_from_config_yaml.app.gcp_service_account_key
    )
    # 这是必须的，否则 genai.Client() 会报错
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    location = global_config_loaded_from_config_yaml.agent.vertex_ai_location

    gemini_client = genai.Client(
        vertexai=True,
        # 密钥 json 文件已经包含了 project_id，所以这里不需要再传入
        # project=,
        location=location,
    )

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


<<<<<<< HEAD
def _first_message_content(run: langsmith.schemas.Run) -> str | None:
    """Return the first message content from run.inputs if present, else None."""
    if not isinstance(run.inputs, dict) or "messages" not in run.inputs:
        return None
    messages = run.inputs["messages"]
    if not messages:
        return None
    first = messages[0]
    return first.get("content") if isinstance(first, dict) else None


=======
>>>>>>> b46472d7 (减少递进层级)
def find_run_contains_random_string(
    start_time: datetime.datetime, random_str: str
) -> langsmith.schemas.Run | None:
    """Query LangSmith for a run whose first message content equals random_str; returns None if not found."""
    ls_client = LangSmithClient()

    for attempt in range(_LANGSMITH_POLL_ATTEMPTS):
        print(f"Attempt {attempt} to find the run with the random string: {random_str}")
        runs = ls_client.list_runs(
            project_name=os.environ["LANGSMITH_PROJECT"],
            start_time=start_time,
            limit=_LANGSMITH_RUNS_PAGE_SIZE,
        )
        runs_list = list(runs)
        for run in runs_list:
<<<<<<< HEAD
            if _first_message_content(run) == random_str:
                return run
        if attempt < _LANGSMITH_POLL_ATTEMPTS - 1:
            time.sleep(_LANGSMITH_POLL_SLEEP_SECONDS)
=======
            if not isinstance(run.inputs, dict):
                continue
            if "messages" not in run.inputs:
                continue
            if len(run.inputs["messages"]) == 0:
                continue
            if run.inputs["messages"][0]["content"] == random_str:
                return run
>>>>>>> b46472d7 (减少递进层级)
    return None


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
    start_time, random_str = _make_traced_gemini_call(wrapped_client, use_plain_text=True)
    assert find_run_contains_random_string(start_time, random_str) is not None, (
        f"No run found with the random string: {random_str}"
    )


@pytest.mark.noci
def test_gemini_text_part_contents_langsmith_integration():
    """当前 wrap_gemini 不会把 types.Part 形式的 contents 序列化到 LangSmith run 的 inputs 中，故预期查不到 run。"""
    wrapped_client = get_wrapped_genai_client()
    start_time, random_str = _make_traced_gemini_call(wrapped_client, use_plain_text=False)
    assert find_run_contains_random_string(start_time, random_str) is None, (
        "追踪无法抓取 types.part 结构体的输入"
    )
