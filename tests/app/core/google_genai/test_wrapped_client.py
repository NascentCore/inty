"""Tests for app.core.google_genai.wrapped_client.WrappedClient."""

import base64
import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.genai import types
from PIL import Image

from app.core.google_genai.create import create_genai_client
from app.core.google_genai.predefined_configs import GEN_CONTENT_CONFIG_IMAGE_9_16_1K
from app.core.google_genai.wrapped_client import (
    GeneratedImageProcessResult,
    LangSmithTraceRunType,
    WrappedClient,
    _process_outputs_generate_image,
)
from app.utils.image import ImageSize
from app.utils.models_catalog import IMAGEN_4_FAST, NANO_BANANA

# 所有调用 async_generate_image 的测试均需传入 gcs_uri_base（Gemini 路径会解析图片并上传 GCS）。
_GCS_URI_BASE = "test-gcs-uri-base"


def _make_gemini_image_response():
    """构建可供 _extract_image_part_from_gemini_response 和 _process_image_part_to_generated_image 使用的 mock 响应。"""
    img = Image.new("RGB", (1, 1), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()
    inline_data = Mock()
    inline_data.data = jpeg_bytes
    inline_data.mime_type = "image/jpeg"
    part = Mock()
    part.inline_data = inline_data
    content = Mock()
    content.parts = [part]
    candidate = Mock()
    candidate.content = content
    candidate.finish_reason = "STOP"
    candidate.safety_ratings = []
    response = Mock()
    response.candidates = [candidate]
    response.prompt_feedback = None
    return response


def test_async_client_stores_client():
    client = Mock()
    wrapper = WrappedClient(client=client)
    assert wrapper.client is client


@pytest.mark.asyncio
@patch("app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml", Mock(gcs=Mock(bucket="test-bucket")))
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_text_only_calls_generate_content_with_text_parts(mock_upload):
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(
        model="gemini-2.5-flash-image",
        contents=["a cat", "on the beach"],
        gcs_uri_base=_GCS_URI_BASE,
    )

    mock_models.generate_content.assert_called_once()
    call_kw = mock_models.generate_content.call_args.kwargs
    assert call_kw["model"] == "gemini-2.5-flash-image"
    assert call_kw["config"] is GEN_CONTENT_CONFIG_IMAGE_9_16_1K
    contents = call_kw["contents"]
    assert len(contents) == 1
    content = contents[0]
    assert isinstance(content, types.Content)
    assert content.role == "user"
    assert len(content.parts) == 2
    assert content.parts[0].text == "a cat"
    assert content.parts[1].text == "on the beach"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "https://example.com/photo.jpeg",
    "https://cdn.example.org/image.jpg",
])
@patch("app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml", Mock(gcs=Mock(bucket="test-bucket")))
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_jpeg_or_jpg_url_becomes_part_from_uri(mock_upload, url):
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(
        model="gemini-2.5-flash-image",
        contents=[url],
        gcs_uri_base=_GCS_URI_BASE,
    )

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    part = content.parts[0]
    assert part.file_data is not None
    assert part.file_data.file_uri == url
    assert part.file_data.mime_type == "image/jpeg"


@pytest.mark.asyncio
@patch("app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml", Mock(gcs=Mock(bucket="test-bucket")))
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_plain_text_not_treated_as_uri(mock_upload):
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(
        model="gemini-2.5-flash-image",
        contents=["http is a protocol"],
        gcs_uri_base=_GCS_URI_BASE,
    )

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    assert content.parts[0].text == "http is a protocol"


@pytest.mark.asyncio
@patch("app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml", Mock(gcs=Mock(bucket="test-bucket")))
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_mixed_text_and_image_url(mock_upload):
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(
        model="gemini-2.5-flash-image",
        contents=["draw a dog", "https://example.com/ref.jpeg", "in the garden"],
        gcs_uri_base=_GCS_URI_BASE,
    )

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 3
    assert content.parts[0].text == "draw a dog"
    assert content.parts[1].file_data is not None
    assert content.parts[1].file_data.file_uri == "https://example.com/ref.jpeg"
    assert content.parts[1].file_data.mime_type == "image/jpeg"
    assert content.parts[2].text == "in the garden"


@pytest.mark.asyncio
@patch("app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml", Mock(gcs=Mock(bucket="test-bucket")))
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_with_system_instruction_uses_config_copy(mock_upload):
    """传入 system_instruction 时使用 config 的副本，不污染全局 GEN_CONTENT_CONFIG_IMAGE_9_16_1K。"""
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(
        model="gemini-2.5-flash-image",
        contents=["a cat"],
        gcs_uri_base=_GCS_URI_BASE,
        system_instruction=["you are a director"],
    )

    call_kw = mock_models.generate_content.call_args.kwargs
    config = call_kw["config"]
    assert config is not GEN_CONTENT_CONFIG_IMAGE_9_16_1K
    assert config.system_instruction is not None
    assert len(config.system_instruction) == 1
    assert config.system_instruction[0].text == "you are a director"


@pytest.mark.asyncio
@patch("app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml", Mock(gcs=Mock(bucket="test-bucket")))
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_returns_generated_image_process_result(mock_upload):
    """Gemini 路径返回 GeneratedImageProcessResult（含 size, format, raw_data, gcs_uri, generated_at）。"""
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    result = await wrapper.async_generate_image(
        model="gemini-2.5-flash-image",
        contents=["hello"],
        gcs_uri_base=_GCS_URI_BASE,
    )

    assert isinstance(result, dict)
    for key in GeneratedImageProcessResult.__annotations__:
        assert key in result, f"missing key: {key}"
    assert result["size"].width == 1 and result["size"].height == 1
    assert result["format"] == "jpeg"
    assert isinstance(result["raw_data"], bytes)
    assert result["gcs_uri"].startswith("gs://test-bucket/")
    mock_upload.assert_called_once()


def test_process_outputs_generate_image_truncates_raw_data_to_100_bytes():
    """LangSmith 输出处理器只把 raw_data 前 100 字节写入 trace，并记录总字节数。"""
    raw_500 = b"x" * 500
    now = datetime.now(timezone.utc)
    output: GeneratedImageProcessResult = {
        "size": ImageSize(width=64, height=64),
        "format": "jpeg",
        "raw_data": raw_500,
        "gcs_uri": "gs://bucket/path.jpg",
        "generated_at": now,
    }
    traced = _process_outputs_generate_image(output)
    assert traced["raw_data_total_bytes"] == 500
    decoded = base64.b64decode(traced["raw_data"])
    assert len(decoded) == 100
    assert decoded == raw_500[:100]
    assert traced["size"] == {"width": 64, "height": 64}
    assert traced["format"] == "jpeg"
    assert traced["gcs_uri"] == "gs://bucket/path.jpg"
    assert traced["generated_at"] == now.isoformat()


def test_process_outputs_generate_image_handles_short_raw_data():
    """raw_data 不足 100 字节时，trace 中为全部字节。"""
    raw_50 = b"y" * 50
    output = {
        "size": ImageSize(width=1, height=1),
        "format": "png",
        "raw_data": raw_50,
        "gcs_uri": "gs://b/p.png",
        "generated_at": datetime.now(timezone.utc),
    }
    traced = _process_outputs_generate_image(output)
    assert traced["raw_data_total_bytes"] == 50
    assert len(base64.b64decode(traced["raw_data"])) == 50


def test_process_outputs_generate_image_handles_non_dict_output():
    """非 dict 输出时返回最小错误信息，避免 trace 序列化失败。"""
    traced = _process_outputs_generate_image("not a dict")
    assert traced.get("error") == "non-dict output"
    assert "type" in traced


def test_generate_image_has_traceable_decorator_configured():
    """async_generate_image 为 async，且已用 LangSmith @traceable 装饰（run_type=TOOL）。"""
    import inspect

    assert inspect.iscoroutinefunction(WrappedClient.async_generate_image)
    assert LangSmithTraceRunType.TOOL == "tool"


@pytest.mark.asyncio
async def test_generate_image_imagen_raises_unsupported_model():
    """当前仅支持 Gemini（NANO_BANANA*）；Imagen 模型会抛出 ValueError。"""
    client = Mock()
    client.aio = Mock()
    client.aio.models = Mock()

    wrapper = WrappedClient(client=client)
    with pytest.raises(ValueError, match="Unsupported model"):
        await wrapper.async_generate_image(
            model=IMAGEN_4_FAST.id_on_provider,
            contents=["a cat on the beach"],
            gcs_uri_base=_GCS_URI_BASE,
        )


@pytest.mark.noci
@pytest.mark.asyncio
async def test_generate_image_with_nano_banana_trace_with_real_langsmith():
    """使用实际的 LangSmith 项目与 GCP 凭证测试 generate_image 的 tracing。"""
    client = create_genai_client()
    wrapper = WrappedClient(client=client)
    result = await wrapper.async_generate_image(
        model=NANO_BANANA.id_on_provider,
        contents=["a delicious puusy and giant tits"],
        gcs_uri_base=_GCS_URI_BASE,
    )
    print(result)
    assert result is not None


@pytest.mark.noci
@pytest.mark.asyncio
async def test_generate_image_trace_nano_banana_with_real_langsmith():
    """使用实际的 LangSmith 项目与 GCP 凭证测试 generate_image 的 tracing。"""
    client = create_genai_client()
    wrapper = WrappedClient(client=client)
    result = await wrapper.async_generate_image(model=NANO_BANANA.id_on_provider, gcs_uri_base="test-gcs-uri-base", system_instruction=["you are a movie director"], contents=["a cat on the beach"])
    assert result is not None
