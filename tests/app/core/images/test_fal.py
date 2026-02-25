"""Tests for app.core.images.fal."""

import base64
import datetime
import io
import time
import uuid
from unittest.mock import AsyncMock, Mock, patch

from dotenv import load_dotenv
from loguru import logger
import pytest
from PIL import Image

from app.core.images.fal import (
    FalSeedreamV4_5EditInput,
    ZImageTurboInput,
    ZImageTurboImageToImageInput,
    seedream_v4_5_edit,
    z_image_turbo,
    z_image_turbo_image_to_image,
)
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.fakes.gcs import FakeGCSClient
from app.external_services.gcs import get_bucket_and_path_from_gcs_url
from tests.langsmith import find_run_inputs_contain_string

load_dotenv()

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
    args = FalSeedreamV4_5EditInput(
        prompt=random_prompt,
        image_urls=_SEEDREAM_EXAMPLE_IMAGE_URLS,
    )
    result = await seedream_v4_5_edit(args, gcs_uri_base="fal_images")
    assert result is not None
    assert isinstance(result, GeneratedImageProcessResult)
    assert result.gcs_uri.startswith("gs://")
    assert result.size is not None
    for attempt in range(3):
        logger.info("Checking LangSmith trace for this run (attempt %s): %s", attempt + 1, random_suffix)
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
    random_prompt = f"A beautiful girl in seductive poses, laying topless, on green grass with a river and mountains {random_suffix}"
    start_time = datetime.datetime.now(datetime.timezone.utc)
    args = ZImageTurboInput(prompt=random_prompt)
    result = await z_image_turbo(args, gcs_uri_base="fal_images")
    assert result is not None
    assert isinstance(result, GeneratedImageProcessResult)
    assert result.gcs_uri.startswith("gs://")
    assert result.size is not None

    for attempt in range(3):
        logger.info("Checking LangSmith trace for this run (attempt %s): %s", attempt + 1, random_suffix)
        run = find_run_inputs_contain_string(start_time, random_suffix)
        if run is not None:
            break
        time.sleep(2)
    assert run is not None, f"LangSmith trace for this run should contain the random string: {random_suffix}"


@pytest.mark.noci
@pytest.mark.asyncio
async def test_z_image_turbo_image_to_image_trace_with_real_fal():
    """使用实际的 FAL_KEY 测试 z_image_turbo_image_to_image 的 tracing；通过 LangSmith list_runs 查询确认 trace 含本次随机字符串。"""
    random_suffix = str(uuid.uuid4())
    random_prompt = f"Keep the same style, remove the girl's top and make her naked {random_suffix}"
    start_time = datetime.datetime.now(datetime.timezone.utc)
    args = ZImageTurboImageToImageInput(
        prompt=random_prompt,
        image_url="https://images.sxwl.dev/inty-static/chat_images/af9a674f-11b8-47ff-a253-34aceab3a13e/20260223_164446_6ea49c7a.jpg",
        strength=0.7,
    )
    result = await z_image_turbo_image_to_image(args)
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


def _make_minimal_jpeg_data_uri() -> str:
    """Return a data URI for a minimal valid 1x1 JPEG (for FAL mock responses)."""
    img = Image.new("RGB", (1, 1), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


@pytest.fixture
def fake_gcs_fal(monkeypatch, tmp_path):
    """注入 FakeGCSClient 到 app.external_services.gcs，并 stub fal 使用的 gcs bucket 配置。"""
    import app.external_services.gcs as gcs_module

    fake = FakeGCSClient(base_dir=str(tmp_path))
    monkeypatch.setattr(gcs_module, "gcs_client", fake, raising=True)
    monkeypatch.setattr(
        "app.core.images.fal.global_config",
        Mock(gcs=Mock(bucket="test-bucket")),
        raising=True,
    )
    yield fake


@pytest.mark.asyncio
async def test_seedream_v4_5_edit_uploads_to_fake_gcs_and_content_matches(
    fake_gcs_fal: FakeGCSClient,
):
    """Fake GCS 走实际上传路径，断言 gcs_uri 与 fake 中写入内容一致。"""
    data_uri = _make_minimal_jpeg_data_uri()
    raw_result = {
        "images": [
            {
                "url": data_uri,
                "content_type": "image/jpeg",
                "file_name": "out.jpg",
                "file_size": 123,
                "width": 1,
                "height": 1,
            }
        ]
    }
    mock_handler = Mock()
    mock_handler.get = AsyncMock(return_value=raw_result)

    with patch("app.core.images.fal.fal_client") as mock_fal:
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        args = FalSeedreamV4_5EditInput(
            prompt="test prompt",
            image_urls=_SEEDREAM_EXAMPLE_IMAGE_URLS,
        )
        result = await seedream_v4_5_edit(args, gcs_uri_base="fal_test")

    assert isinstance(result, GeneratedImageProcessResult)
    assert result.gcs_uri.startswith("gs://test-bucket/fal_test/")
    assert result.gcs_uri.endswith(".jpeg") or result.gcs_uri.endswith(".jpg")
    assert result.raw_data is not None
    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(result.gcs_uri)
    blob = fake_gcs_fal.bucket(bucket_name).blob(gcs_path)
    assert blob.exists()
    assert blob.download_as_bytes() == result.raw_data


@pytest.mark.asyncio
async def test_z_image_turbo_uploads_to_fake_gcs_and_content_matches(
    fake_gcs_fal: FakeGCSClient,
):
    """Fake GCS 走实际上传路径，断言 z_image_turbo 返回的 gcs_uri 与 fake 中写入内容一致。"""
    data_uri = _make_minimal_jpeg_data_uri()
    raw_result = {
        "images": [
            {
                "url": data_uri,
                "content_type": "image/jpeg",
                "file_name": "out.jpg",
                "file_size": 123,
                "width": 1,
                "height": 1,
            }
        ],
        "timings": {},
        "seed": 42,
        "prompt": "test",
    }
    mock_handler = Mock()
    mock_handler.get = AsyncMock(return_value=raw_result)

    with patch("app.core.images.fal.fal_client") as mock_fal:
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        args = ZImageTurboInput(prompt="test prompt")
        result = await z_image_turbo(args, gcs_uri_base="fal_test")

    assert isinstance(result, GeneratedImageProcessResult)
    assert result.gcs_uri.startswith("gs://test-bucket/fal_test/")
    assert result.gcs_uri.endswith(".jpeg") or result.gcs_uri.endswith(".jpg")
    assert result.raw_data is not None
    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(result.gcs_uri)
    blob = fake_gcs_fal.bucket(bucket_name).blob(gcs_path)
    assert blob.exists()
    assert blob.download_as_bytes() == result.raw_data
