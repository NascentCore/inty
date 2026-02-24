"""Tests for app.core.images.fal."""

import datetime
import time
import uuid
from dotenv import load_dotenv

load_dotenv()

from loguru import logger
import pytest

from app.core.images.fal import FalSeedreamV4_5EditArgs, ImgGenArgs, seedream_v4_5_edit, z_image_turbo
from tests.langsmith import find_run_inputs_contain_string

# Example prompt and image_urls from app/core/images/fal.py docstring (public fal example).
_SEEDREAM_EXAMPLE_PROMPT = (
    "Replace the product in Figure 1 with that in Figure 2. For the title copy the text in Figure 3 to the top of the screen, the title should have a clear contrast with the background but not be overly eye-catching."
)
_SEEDREAM_EXAMPLE_IMAGE_URLS = [
    "https://storage.googleapis.com/falserverless/example_inputs/seedreamv45/seedream_v45_edit_input_1.png",
    "https://storage.googleapis.com/falserverless/example_inputs/seedreamv45/seedream_v45_edit_input_2.png",
    "https://storage.googleapis.com/falserverless/example_inputs/seedreamv45/seedream_v45_edit_input_3.png",
]


@pytest.mark.noci
@pytest.mark.asyncio
async def test_seedream_v4_5_edit_trace_with_real_fal():
    """使用实际的 FAL_KEY 测试 seedream_v4_5_edit 的 tracing；通过 LangSmith list_runs 查询确认 trace 含本次随机字符串。"""
    random_suffix = str(uuid.uuid4())
    random_prompt = _SEEDREAM_EXAMPLE_PROMPT + "output jpeg format" + f" {random_suffix}"
    start_time = datetime.datetime.now(datetime.timezone.utc)
    args = FalSeedreamV4_5EditArgs(
        prompt=random_prompt,
        image_urls=_SEEDREAM_EXAMPLE_IMAGE_URLS,
    )
    result = await seedream_v4_5_edit(args)
    assert result is not None
    assert result.images is not None
    assert len(result.images) >= 1
    for attempt in range(3):
        logger.info(f"Checking LangSmith trace for this run (attempt {attempt + 1}): {random_suffix}")
        run = find_run_inputs_contain_string(start_time, random_suffix)
        if run is not None:
            break
        time.sleep(2)
    assert run is not None, f"LangSmith trace for this run should contain the random string: {random_suffix}"


@pytest.mark.noci
@pytest.mark.asyncio
async def test_z_image_turbo_trace_with_real_fal():
    """使用实际的 FAL_KEY 测试 z_image_turbo 的 tracing；通过 LangSmith list_runs 查询确认 trace 含本次随机字符串。"""
    random_suffix = str(uuid.uuid4())
    random_prompt = f"A beautiful landscape painting with a river and mountains {random_suffix}"
    start_time = datetime.datetime.now(datetime.timezone.utc)
    args = ImgGenArgs(prompt=random_prompt)
    result = await z_image_turbo(args)
    assert result is not None
    assert result.images is not None
    assert len(result.images) >= 1

    for attempt in range(3):
        logger.info(f"Checking LangSmith trace for this run (attempt {attempt + 1}): {random_suffix}")
        run = find_run_inputs_contain_string(start_time, random_suffix)
        if run is not None:
            break
        time.sleep(2)
    assert run is not None, f"LangSmith trace for this run should contain the random string: {random_suffix}"
