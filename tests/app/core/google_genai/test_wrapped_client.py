"""Tests for app.core.google_genai.wrapped_client.WrappedClient."""

import base64
import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.genai import types
from PIL import Image

from app.core.google_genai.predefined_configs import GEN_CONTENT_CONFIG_IMAGE_9_16_1K
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.gcs import get_bucket_and_path_from_gcs_url
from app.external_services.fakes.gcs import FakeGCSClient
from app.utils.gemini import create_google_genai_client
from app.core.google_genai.wrapped_client import (
    LangSmithTraceRunType,
    WrappedClient,
    _extract_image_part_from_gemini_response,
    _langsmith_process_outputs_generate_image,
    _langsmith_process_outputs_generate_images,
)
from app.utils.image import ImageFormat, ImageSize
from app.utils.models_catalog import IMAGEN_4_FAST, NANO_BANANA

# 所有调用 async_generate_images 的测试均需传入 gcs_uri_base（Gemini 路径会解析图片并上传 GCS）。
_GCS_URI_BASE = "test-gcs-uri-base"


def _mock_upload_to_gcs_https_return(
    file_data, content_type, bucket_name, path
):  # noqa: ARG001
    """Patched ``upload_to_gcs`` must return a string URL (production shape in mocked tests)."""
    return f"https://storage.googleapis.com/{bucket_name}/{path}"


def _make_gemini_response_payload_with_inline_data(
    image_bytes: bytes, mime_type: str
) -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inline_data": {
                                "data": image_bytes,
                                "mime_type": mime_type,
                            }
                        }
                    ]
                },
                "finish_reason": "STOP",
                "safety_ratings": [],
            }
        ],
        "prompt_feedback": None,
    }


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
    response.model_dump.return_value = _make_gemini_response_payload_with_inline_data(
        jpeg_bytes,
        "image/jpeg",
    )
    return response


def _make_gemini_image_response_png():
    """与 _make_gemini_image_response 相同结构，但 inline_data 为 PNG 字节。"""
    img = Image.new("RGB", (2, 2), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    inline_data = Mock()
    inline_data.data = png_bytes
    inline_data.mime_type = "image/png"
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
    response.model_dump.return_value = _make_gemini_response_payload_with_inline_data(
        png_bytes,
        "image/png",
    )
    return response


def _make_gemini_image_response_two_candidates():
    """构建含两个候选图片的 mock 响应，用于测试 count=2 时返回两条结果。"""
    img1 = Image.new("RGB", (1, 1), color="red")
    img2 = Image.new("RGB", (1, 1), color="blue")
    buf1, buf2 = io.BytesIO(), io.BytesIO()
    img1.save(buf1, format="JPEG")
    img2.save(buf2, format="JPEG")
    jpeg1, jpeg2 = buf1.getvalue(), buf2.getvalue()

    def _candidate(data: bytes):
        inline_data = Mock()
        inline_data.data = data
        inline_data.mime_type = "image/jpeg"
        part = Mock()
        part.inline_data = inline_data
        content = Mock()
        content.parts = [part]
        candidate = Mock()
        candidate.content = content
        candidate.finish_reason = "STOP"
        candidate.safety_ratings = []
        return candidate

    response = Mock()
    response.candidates = [_candidate(jpeg1), _candidate(jpeg2)]
    response.prompt_feedback = None
    response.model_dump.return_value = {
        "candidates": [
            _make_gemini_response_payload_with_inline_data(jpeg1, "image/jpeg")[
                "candidates"
            ][0],
            _make_gemini_response_payload_with_inline_data(jpeg2, "image/jpeg")[
                "candidates"
            ][0],
        ],
        "prompt_feedback": None,
    }
    return response


@pytest.fixture
def fake_gcs_for_wrapped_client(monkeypatch, tmp_path):
    """注入 FakeGCSClient 到 app.external_services.gcs，并 stub wrapped_client 使用的 gcs.bucket 配置。"""
    import app.external_services.gcs as gcs_module

    fake = FakeGCSClient(base_dir=str(tmp_path))
    monkeypatch.setattr(gcs_module, "gcs_client", fake, raising=True)
    monkeypatch.setattr(
        "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
        Mock(gcs=Mock(bucket="test-bucket")),
        raising=True,
    )
    yield fake


def test_async_client_stores_client():
    client = Mock()
    wrapper = WrappedClient(client=client)
    assert wrapper.client is client


def test_extract_image_part_treats_image_prohibited_content_as_safety_block():
    candidate = Mock()
    candidate.finish_reason = "FinishReason.IMAGE_PROHIBITED_CONTENT"
    candidate.safety_ratings = []
    candidate.content = None
    response = Mock()
    response.prompt_feedback = None
    response.candidates = [candidate]

    with pytest.raises(ValueError, match="blocked by safety filter"):
        _extract_image_part_from_gemini_response(response)


@pytest.mark.asyncio
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_text_only_calls_generate_content_with_text_parts(
    mock_upload,
):
    mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["a cat", "on the beach"],
        gcs_uri_base=_GCS_URI_BASE,
    )

    mock_models.generate_content.assert_called_once()
    call_kw = mock_models.generate_content.call_args.kwargs
    assert call_kw["model"] == "gemini-2.5-flash-image"
    config = call_kw["config"]
    assert config.candidate_count == 1
    assert config.image_config == GEN_CONTENT_CONFIG_IMAGE_9_16_1K.image_config
    contents = call_kw["contents"]
    assert len(contents) == 1
    content = contents[0]
    assert isinstance(content, types.Content)
    assert content.role == "user"
    assert len(content.parts) == 2
    assert content.parts[0].text == "a cat"
    assert content.parts[1].text == "on the beach"


@pytest.mark.asyncio
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_images_count_two_passes_config_and_returns_two_results(
    mock_upload,
):
    """count=2 时传入 config.candidate_count=2，且 mock 返回两候选时得到两条 GeneratedImageProcessResult。"""
    mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(
        return_value=_make_gemini_image_response_two_candidates()
    )
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    results = await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["two cats"],
        gcs_uri_base=_GCS_URI_BASE,
        count=2,
    )

    call_kw = mock_models.generate_content.call_args.kwargs
    assert call_kw["config"].candidate_count == 2
    assert len(results) == 2
    assert all(isinstance(r, GeneratedImageProcessResult) for r in results)
    assert mock_upload.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/photo.jpeg",
        "https://cdn.example.org/image.jpg",
    ],
)
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_jpeg_or_jpg_url_becomes_part_from_uri(mock_upload, url):
    mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_images(
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
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_plain_text_not_treated_as_uri(mock_upload):
    mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["http is a protocol"],
        gcs_uri_base=_GCS_URI_BASE,
    )

    call_kw = mock_models.generate_content.call_args.kwargs
    content = call_kw["contents"][0]
    assert len(content.parts) == 1
    assert content.parts[0].text == "http is a protocol"


@pytest.mark.asyncio
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_mixed_text_and_image_url(mock_upload):
    mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_images(
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
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_with_system_instruction_uses_config_copy(mock_upload):
    """传入 system_instruction 时使用 config 的副本，不污染全局 GEN_CONTENT_CONFIG_IMAGE_9_16_1K。"""
    mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["a cat"],
        gcs_uri_base=_GCS_URI_BASE,
        system_instructions=["you are a director"],
    )

    call_kw = mock_models.generate_content.call_args.kwargs
    config = call_kw["config"]
    assert config is not GEN_CONTENT_CONFIG_IMAGE_9_16_1K
    assert config.system_instruction is not None
    assert len(config.system_instruction) == 1
    assert config.system_instruction[0].text == "you are a director"


@pytest.mark.asyncio
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
@patch("app.core.google_genai.wrapped_client.attach_provider_response_to_langsmith_run")
async def test_generate_image_attaches_sanitized_provider_response_after_gcs_upload(
    mock_attach_provider_response_to_langsmith_run,
    _mock_upload,
):
    _mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["hello"],
        gcs_uri_base=_GCS_URI_BASE,
    )

    mock_attach_provider_response_to_langsmith_run.assert_called_once()
    attached_response = mock_attach_provider_response_to_langsmith_run.call_args.args[0]
    inline_data = attached_response["candidates"][0]["content"]["parts"][0][
        "inline_data"
    ]
    assert "omitted raw image data after GCS upload" in inline_data["data"]
    assert inline_data["mime_type"] == "image/jpeg"


@pytest.mark.asyncio
@patch(
    "app.core.google_genai.wrapped_client.global_config_loaded_from_config_yaml",
    Mock(gcs=Mock(bucket="test-bucket")),
)
@patch("app.core.google_genai.wrapped_client.upload_to_gcs")
async def test_generate_image_returns_generated_image_process_result(mock_upload):
    """Gemini 路径返回 GeneratedImageProcessResult（含 size, format, raw_data, gcs_uri, generated_at）。"""
    mock_upload.side_effect = _mock_upload_to_gcs_https_return
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    results = await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["hello"],
        gcs_uri_base=_GCS_URI_BASE,
    )
    result = results[0]

    assert isinstance(result, GeneratedImageProcessResult)
    assert result.size.width == 1 and result.size.height == 1
    assert result.format == ImageFormat.JPEG
    assert isinstance(result.raw_data, bytes)
    assert result.gcs_uri.startswith("gs://test-bucket/")
    mock_upload.assert_called_once()


@pytest.mark.asyncio
async def test_generate_image_uploads_to_fake_gcs_and_content_matches(
    fake_gcs_for_wrapped_client: FakeGCSClient,
):
    """使用 Fake GCS 走实际上传路径，断言 gcs_uri 与 fake 中写入内容一致。"""
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=_make_gemini_image_response())
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    results = await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["a cat"],
        gcs_uri_base=_GCS_URI_BASE,
    )
    result = results[0]

    assert result.gcs_uri.startswith("gs://test-bucket/")
    assert result.gcs_uri.endswith(".jpg")
    assert result.gcs_uri.find(_GCS_URI_BASE) >= 0

    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(result.gcs_uri)
    blob = fake_gcs_for_wrapped_client.bucket(bucket_name).blob(gcs_path)
    assert blob.exists()
    assert result.gcs_http_url == blob.public_url
    assert blob.download_as_bytes() == result.raw_data


@pytest.mark.asyncio
async def test_generate_image_uploads_png_to_fake_gcs_with_correct_extension(
    fake_gcs_for_wrapped_client: FakeGCSClient,
):
    """PNG 响应时上传到 Fake GCS，路径扩展名为 .png，fake 中内容与 raw_data 一致。"""
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(
        return_value=_make_gemini_image_response_png()
    )
    client = Mock()
    client.aio = Mock()
    client.aio.models = mock_models

    wrapper = WrappedClient(client=client)
    results = await wrapper.async_generate_images(
        model="gemini-2.5-flash-image",
        contents=["blue square"],
        gcs_uri_base=_GCS_URI_BASE,
    )
    result = results[0]

    assert result.format == ImageFormat.PNG
    assert result.gcs_uri.startswith("gs://test-bucket/")
    assert result.gcs_uri.endswith(".png")
    assert result.gcs_uri.find(_GCS_URI_BASE) >= 0

    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(result.gcs_uri)
    blob = fake_gcs_for_wrapped_client.bucket(bucket_name).blob(gcs_path)
    assert blob.exists()
    assert result.gcs_http_url == blob.public_url
    assert blob.download_as_bytes() == result.raw_data


def test_process_outputs_generate_image_truncates_raw_data_to_100_bytes():
    """LangSmith 输出处理器只把 raw_data 前 100 字节写入 trace，并记录总字节数。"""
    raw_500 = b"x" * 500
    now = datetime.now(timezone.utc)
    output = GeneratedImageProcessResult(
        size=ImageSize(width=64, height=64),
        format=ImageFormat.JPEG,
        raw_data=raw_500,
        gcs_uri="gs://bucket/path.jpg",
        gcs_http_url="https://storage.googleapis.com/bucket/path.jpg",
        generated_at=now,
    )
    traced = _langsmith_process_outputs_generate_image(output)
    assert traced is not None
    assert traced.raw_data_total_bytes == 500
    decoded = base64.b64decode(traced.raw_data)
    assert len(decoded) == 100
    assert decoded == raw_500[:100]


def test_process_outputs_generate_image_handles_short_raw_data():
    """raw_data 不足 100 字节时，trace 中为全部字节。"""
    raw_50 = b"y" * 50
    output = GeneratedImageProcessResult(
        size=ImageSize(width=1, height=1),
        format=ImageFormat.PNG,
        raw_data=raw_50,
        gcs_uri="gs://b/p.png",
        gcs_http_url="https://storage.googleapis.com/b/p.png",
        generated_at=datetime.now(timezone.utc),
    )
    traced = _langsmith_process_outputs_generate_image(output)
    assert traced is not None
    assert traced.raw_data_total_bytes == 50
    assert len(base64.b64decode(traced.raw_data)) == 50


def test_process_outputs_generate_image_redacts_inline_data_from_raw_response():
    """上传 GCS 成功时，trace 输出中的 raw_response_from_provider 不保留原始图片数据。"""
    provider_response = _make_gemini_response_payload_with_inline_data(
        image_bytes=b"z" * 120,
        mime_type="image/jpeg",
    )
    output = GeneratedImageProcessResult(
        size=ImageSize(width=1, height=1),
        format=ImageFormat.PNG,
        raw_data=b"a",
        gcs_uri="gs://b/p.png",
        gcs_http_url="https://storage.googleapis.com/b/p.png",
        generated_at=datetime.now(timezone.utc),
        raw_response_from_provider=provider_response,
    )
    traced = _langsmith_process_outputs_generate_image(output)
    assert traced is not None
    trace_inline_data = traced.raw_response_from_provider["candidates"][0]["content"][
        "parts"
    ][0]["inline_data"]["data"]
    assert "omitted raw image data after GCS upload" in trace_inline_data
    # 确保原始返回值中的 provider response 不被就地修改。
    assert (
        provider_response["candidates"][0]["content"]["parts"][0]["inline_data"]["data"]
        == b"z" * 120
    )


def test_process_outputs_generate_images_maps_list():
    """async_generate_images 的 process_outputs 接收 list，逐项 sanitize 后返回 list。"""
    raw_100 = b"a" * 100
    now = datetime.now(timezone.utc)
    one = GeneratedImageProcessResult(
        size=ImageSize(width=1, height=1),
        format=ImageFormat.JPEG,
        raw_data=raw_100,
        gcs_uri="gs://b/1.jpg",
        gcs_http_url="https://storage.googleapis.com/b/1.jpg",
        generated_at=now,
    )
    traced_list = _langsmith_process_outputs_generate_images([one])
    assert traced_list is not None
    assert len(traced_list) == 1
    assert traced_list[0].raw_data_total_bytes == 100
    assert len(base64.b64decode(traced_list[0].raw_data)) == 100


def test_generate_image_has_traceable_decorator_configured():
    """async_generate_images 为 async，且已用 LangSmith @traceable 装饰（run_type=TOOL）。"""
    import inspect

    assert inspect.iscoroutinefunction(WrappedClient.async_generate_images)
    assert LangSmithTraceRunType.TOOL == "tool"


@pytest.mark.asyncio
async def test_generate_image_imagen_raises_unsupported_model():
    """当前仅支持 Gemini（NANO_BANANA*）；Imagen 模型会抛出 ValueError。"""
    client = Mock()
    client.aio = Mock()
    client.aio.models = Mock()

    wrapper = WrappedClient(client=client)
    with pytest.raises(ValueError, match="Unsupported model"):
        await wrapper.async_generate_images(
            model=IMAGEN_4_FAST.id_on_provider,
            contents=["a cat on the beach"],
            gcs_uri_base=_GCS_URI_BASE,
        )


@pytest.mark.noci
@pytest.mark.asyncio
async def test_generate_image_failure_with_nano_banana_trace_with_real_langsmith():
    """使用实际的 LangSmith 项目与 GCP 凭证测试 generate_image 的 tracing。"""
    client = create_google_genai_client()
    wrapper = WrappedClient(client=client)
    results = await wrapper.async_generate_images(
        model=NANO_BANANA.id_on_provider,
        contents=["a delicious puusy and giant tits"],
        gcs_uri_base=_GCS_URI_BASE,
    )
    print(results)
    assert results and results[0] is not None


@pytest.mark.noci
@pytest.mark.asyncio
async def test_generate_image_trace_nano_banana_with_real_langsmith():
    """使用实际的 LangSmith 项目与 GCP 凭证测试 generate_image 的 tracing。"""
    client = create_google_genai_client()
    wrapper = WrappedClient(client=client)
    results = await wrapper.async_generate_images(
        model=NANO_BANANA.id_on_provider,
        gcs_uri_base="test-gcs-uri-base",
        system_instructions=["you are a movie director"],
        contents=["a cat on the beach"],
    )
    assert results and results[0] is not None
