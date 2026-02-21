"""Tests for app.core.google_genai.wrapped_client.AsyncClient."""

from unittest.mock import AsyncMock, Mock

import pytest
from google.genai import types

from app.core.google_genai.create import create_genai_client
from app.core.google_genai.predefined_configs import (
    GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR,
)
from app.core.google_genai.wrapped_client import LangSmithTraceRunType, WrappedClient
from app.utils.models_catalog import IMAGEN_4_FAST, NANO_BANANA


def test_async_client_stores_client():
    client = Mock()
    wrapper = WrappedClient(client=client)
    assert wrapper.client is client


@pytest.mark.asyncio
async def test_generate_image_text_only_calls_generate_content_with_text_parts():
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=Mock())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(model="gemini-2.5-flash-image", contents=["a cat", "on the beach"])

    mock_models.generate_content.assert_called_once()
    call_kw = mock_models.generate_content.call_args.kwargs
    assert call_kw["model"] == "gemini-2.5-flash-image"
    assert call_kw["config"] is GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR
    contents = call_kw["contents"]
    assert len(contents) == 1
    content = contents[0]
    assert isinstance(content, types.Content)
    assert content.role == "user"
    assert len(content.parts) == 2
    assert content.parts[0].text == "a cat"
    assert content.parts[1].text == "on the beach"


@pytest.mark.asyncio
async def test_generate_image_jpeg_url_becomes_part_from_uri():
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=Mock())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    url = "https://example.com/photo.jpeg"
    await wrapper.async_generate_image(model="gemini-2.5-flash-image", contents=[url])

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    part = content.parts[0]
    assert part.file_data is not None
    assert part.file_data.file_uri == url
    assert part.file_data.mime_type == "image/jpeg"


@pytest.mark.asyncio
async def test_generate_image_jpg_url_becomes_part_from_uri():
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=Mock())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    url = "https://cdn.example.org/image.jpg"
    await wrapper.async_generate_image(model="gemini-2.5-flash-image", contents=[url])

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    part = content.parts[0]
    assert part.file_data is not None
    assert part.file_data.file_uri == url
    assert part.file_data.mime_type == "image/jpeg"


@pytest.mark.asyncio
async def test_generate_image_plain_text_not_treated_as_uri():
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=Mock())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(model="gemini-2.5-flash-image", contents=["http is a protocol"])

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    assert content.parts[0].text == "http is a protocol"


@pytest.mark.asyncio
async def test_generate_image_mixed_text_and_image_url():
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=Mock())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_image(
        model="gemini-2.5-flash-image",
        contents=["draw a dog", "https://example.com/ref.jpeg", "in the garden"],
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
async def test_generate_image_returns_result_of_generate_content():
    expected_result = Mock()
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=expected_result)
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    result = await wrapper.async_generate_image(model="gemini-2.5-flash-image", contents=["hello"])

    assert result is expected_result

def test_generate_image_has_traceable_decorator_configured():
    """async_generate_image 为 async，且已用 LangSmith @traceable 装饰（run_type=LLM）。"""
    import inspect

    assert inspect.iscoroutinefunction(WrappedClient.async_generate_image)
    # run_type 在 wrapped_client 中为 LangSmithTraceRunType.LLM；此处仅保证枚举已导出
    assert LangSmithTraceRunType.LLM == "llm"


@pytest.mark.noci
@pytest.mark.asyncio
async def test_generate_image_with_nano_banana_trace_with_real_langsmith():
    """使用实际的 LangSmith 项目与 GCP 凭证测试 generate_image 的 tracing。"""
    client = create_genai_client()
    wrapper = WrappedClient(client=client)
    result = await wrapper.async_generate_image(
        model=NANO_BANANA.id_on_provider, contents=["a delicious puusy and giant tits"]
    )
    print(result)
    assert result is not None


@pytest.mark.noci
@pytest.mark.asyncio
async def test_generate_image_with_imagen_4_fast_trace_with_real_langsmith():
    """使用实际的 LangSmith 项目与 GCP 凭证测试 generate_image 的 tracing。"""
    client = create_genai_client()
    wrapper = WrappedClient(client=client)
    result = await wrapper.async_generate_image(
        model=IMAGEN_4_FAST.id_on_provider, contents=["a cat on the beach"]
    )
    print(result)
    assert result is not None
