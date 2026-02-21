"""Tests for app.core.google_genai.wrapped_client.AsyncClient."""

from unittest.mock import Mock

from google.genai import types

from app.core.google_genai.predefined_configs import (
    GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR,
)
from app.core.google_genai.wrapped_client import AsyncClient


def test_async_client_stores_client():
    client = Mock()
    wrapper = AsyncClient(client=client)
    assert wrapper.client is client


def test_generate_image_text_only_calls_generate_content_with_text_parts():
    mock_models = Mock()
    mock_models.generate_content = Mock(return_value=Mock())
    client = Mock()
    client.models = mock_models

    wrapper = AsyncClient(client=client)
    wrapper.generate_image(model="imagen-3", contents=["a cat", "on the beach"])

    mock_models.generate_content.assert_called_once()
    call_kw = mock_models.generate_content.call_args.kwargs
    assert call_kw["model"] == "imagen-3"
    assert call_kw["config"] is GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR
    contents = call_kw["contents"]
    assert len(contents) == 1
    content = contents[0]
    assert isinstance(content, types.Content)
    assert content.role == "user"
    assert len(content.parts) == 2
    assert content.parts[0].text == "a cat"
    assert content.parts[1].text == "on the beach"


def test_generate_image_jpeg_url_becomes_part_from_uri():
    mock_models = Mock()
    mock_models.generate_content = Mock(return_value=Mock())
    client = Mock()
    client.models = mock_models

    wrapper = AsyncClient(client=client)
    url = "https://example.com/photo.jpeg"
    wrapper.generate_image(model="imagen-3", contents=[url])

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    part = content.parts[0]
    assert part.file_data is not None
    assert part.file_data.file_uri == url
    assert part.file_data.mime_type == "image/jpeg"


def test_generate_image_jpg_url_becomes_part_from_uri():
    mock_models = Mock()
    mock_models.generate_content = Mock(return_value=Mock())
    client = Mock()
    client.models = mock_models

    wrapper = AsyncClient(client=client)
    url = "https://cdn.example.org/image.jpg"
    wrapper.generate_image(model="imagen-3", contents=[url])

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    part = content.parts[0]
    assert part.file_data is not None
    assert part.file_data.file_uri == url
    assert part.file_data.mime_type == "image/jpeg"


def test_generate_image_plain_text_not_treated_as_uri():
    mock_models = Mock()
    mock_models.generate_content = Mock(return_value=Mock())
    client = Mock()
    client.models = mock_models

    wrapper = AsyncClient(client=client)
    wrapper.generate_image(model="imagen-3", contents=["http is a protocol"])

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    assert content.parts[0].text == "http is a protocol"


def test_generate_image_mixed_text_and_image_url():
    mock_models = Mock()
    mock_models.generate_content = Mock(return_value=Mock())
    client = Mock()
    client.models = mock_models

    wrapper = AsyncClient(client=client)
    wrapper.generate_image(
        model="imagen-3",
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


def test_generate_image_returns_result_of_generate_content():
    expected_result = Mock()
    mock_models = Mock()
    mock_models.generate_content = Mock(return_value=expected_result)
    client = Mock()
    client.models = mock_models

    wrapper = AsyncClient(client=client)
    result = wrapper.generate_image(model="imagen-3", contents=["hello"])

    assert result is expected_result

def test_langsmith_tracing_image_generation():
    pass
