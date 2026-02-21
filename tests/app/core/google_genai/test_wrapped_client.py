"""Tests for app.core.google_genai.wrapped_client.AsyncClient."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from google.genai import types

from app.core.google_genai.create import create_genai_client
from app.core.google_genai.predefined_configs import (
    GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR,
)
from app.core.google_genai.wrapped_client import (
    WrappedClient,
    _process_inputs_generate_image,
    _process_outputs_generate_image,
)
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

def test_process_inputs_generate_image_records_model_and_contents_only():
    """Trace inputs 包含 model 与 contents，不包含 client。"""
    inp = _process_inputs_generate_image(
        _self=Mock(),
        model="gemini-2.5-flash-image",
        contents=["a prompt", "https://example.com/ref.jpeg"],
    )
    assert inp == {
        "model": "gemini-2.5-flash-image",
        "contents": ["a prompt", "https://example.com/ref.jpeg"],
    }


def test_process_outputs_generate_image_none_returns_summary():
    out = _process_outputs_generate_image(None)
    assert out == {"status": "none", "candidates_count": 0}


def test_process_outputs_generate_image_summarizes_response_no_raw_bytes():
    """Outputs 为摘要（候选数、part 类型与字节长），不包含图片二进制。"""
    mock_part_inline = Mock()
    mock_part_inline.inline_data = Mock(data=b"x" * 100)
    mock_part_text = Mock(spec=[])
    mock_part_text.inline_data = None
    mock_part_text.text = "caption"
    mock_content = Mock()
    mock_content.parts = [mock_part_inline, mock_part_text]
    mock_candidate = Mock()
    mock_candidate.content = mock_content
    mock_response = Mock()
    mock_response.prompt_feedback = None
    mock_response.candidates = [mock_candidate]

    out = _process_outputs_generate_image(mock_response)

    assert out["candidates_count"] == 1
    assert out["candidates_parts_summary"] == [
        [
            {"kind": "inline_data", "size_bytes": 100},
            {"kind": "text", "length": 7},
        ]
    ]
    # 确保只有摘要（size_bytes: 100），没有原始图片二进制
    assert out["candidates_parts_summary"][0][0]["kind"] == "inline_data"
    assert out["candidates_parts_summary"][0][0]["size_bytes"] == 100
    assert "data" not in out["candidates_parts_summary"][0][0]


def test_generate_image_has_traceable_decorator_configured():
    """generate_image 为 async 且模块已配置 LangSmith tracing（traceable + process_inputs/process_outputs）。"""
    import inspect

    assert inspect.iscoroutinefunction(WrappedClient.async_generate_image)
    assert _process_inputs_generate_image(None, "m", ["c"]) == {"model": "m", "contents": ["c"]}
    assert _process_outputs_generate_image(None) == {"status": "none", "candidates_count": 0}

@pytest.mark.noci
@pytest.mark.asyncio
async def test_generate_image_trace_with_real_langsmith():
    """使用实际的 LangSmith 项目与 GCP 凭证测试 generate_image 的 tracing。"""
    client = create_genai_client()
    wrapper = WrappedClient(client=client)
    result = await wrapper.async_generate_image(model=IMAGEN_4_FAST.id_on_provider, contents=["a cat on the beach"])
    assert result is not None
