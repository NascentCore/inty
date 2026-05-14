import base64
import json

import pytest

from tools.upscaler.vertex_imagen import (
    UpscaleError,
    VertexUpscaleRequest,
    append_api_key,
    build_upscale_payload,
    build_vertex_predict_endpoint,
    normalize_upscale_factor,
    parse_upscale_response,
    upscale_image_with_vertex,
)


def test_build_vertex_predict_endpoint_uses_vertex_predict_path() -> None:
    endpoint = build_vertex_predict_endpoint(
        project_id="demo-project",
        region="us-central1",
        model_id="imagen-4.0-upscale-preview",
    )
    assert endpoint == (
        "https://us-central1-aiplatform.googleapis.com/v1/projects/demo-project/"
        "locations/us-central1/publishers/google/models/imagen-4.0-upscale-preview:predict"
    )


def test_normalize_upscale_factor_accepts_int_and_string() -> None:
    assert normalize_upscale_factor(2) == "x2"
    assert normalize_upscale_factor("x4") == "x4"


def test_normalize_upscale_factor_rejects_invalid_value() -> None:
    with pytest.raises(UpscaleError):
        normalize_upscale_factor("x8")


def test_build_upscale_payload_contains_base64_image_bytes() -> None:
    payload = build_upscale_payload(
        image_bytes=b"abc",
        prompt="Upscale the image",
        upscale_factor="x2",
        output_mime_type="image/png",
        compression_quality=75,
    )
    encoded = payload["instances"][0]["image"]["bytesBase64Encoded"]
    assert encoded == base64.b64encode(b"abc").decode("ascii")


def test_build_upscale_payload_omits_compression_quality_for_png() -> None:
    payload = build_upscale_payload(
        image_bytes=b"abc",
        prompt="Upscale",
        upscale_factor="x2",
        output_mime_type="image/png",
        compression_quality=75,
    )
    output_options = payload["parameters"]["outputOptions"]
    assert "compressionQuality" not in output_options
    assert output_options["mimeType"] == "image/png"


def test_build_upscale_payload_includes_compression_quality_for_jpeg_and_webp() -> None:
    for mime_type in ("image/jpeg", "image/webp"):
        payload = build_upscale_payload(
            image_bytes=b"abc",
            prompt="Upscale",
            upscale_factor="x2",
            output_mime_type=mime_type,
            compression_quality=90,
        )
        output_options = payload["parameters"]["outputOptions"]
        assert output_options["compressionQuality"] == 90
        assert output_options["mimeType"] == mime_type


def test_parse_upscale_response_returns_image_and_mime_type() -> None:
    response_json = {
        "predictions": [
            {
                "mimeType": "image/png",
                "bytesBase64Encoded": base64.b64encode(b"image-bytes").decode("ascii"),
            }
        ]
    }
    image_bytes, mime_type = parse_upscale_response(response_json)
    assert image_bytes == b"image-bytes"
    assert mime_type == "image/png"


def test_parse_upscale_response_rejects_invalid_base64() -> None:
    response_json = {"predictions": [{"bytesBase64Encoded": "!!!"}]}
    with pytest.raises(UpscaleError):
        parse_upscale_response(response_json)


def test_append_api_key_keeps_existing_query() -> None:
    url = "https://example.com/path?foo=bar"
    assert append_api_key(url, "abc123").endswith("foo=bar&key=abc123")


def test_upscale_image_with_vertex_uses_api_key_and_decodes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response_payload = {
        "predictions": [
            {
                "mimeType": "image/jpeg",
                "bytesBase64Encoded": base64.b64encode(b"upscaled").decode("ascii"),
            }
        ]
    }
    captured: dict[str, object] = {}

    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return json.dumps(response_payload).encode("utf-8")

    def fake_urlopen(http_request, timeout):  # noqa: ANN001
        captured["request"] = http_request
        captured["timeout"] = timeout
        return FakeHTTPResponse()

    monkeypatch.setattr("tools.upscaler.vertex_imagen.request.urlopen", fake_urlopen)
    request_data = VertexUpscaleRequest(
        project_id="demo-project",
        image_bytes=b"input-image",
        api_key="test-api-key",
        region="us-central1",
        model_id="imagen-4.0-upscale-preview",
        upscale_factor="x2",
    )
    result = upscale_image_with_vertex(request_data)

    assert result.image_bytes == b"upscaled"
    assert result.mime_type == "image/jpeg"
    assert "key=test-api-key" in result.request_url

    request_obj = captured["request"]
    assert request_obj is not None
    request_headers = {
        key.lower(): value for key, value in request_obj.header_items()  # type: ignore[attr-defined]
    }
    assert request_headers["x-goog-api-key"] == "test-api-key"
    assert captured["timeout"] == request_data.timeout_seconds


def test_upscale_image_with_vertex_requires_auth() -> None:
    request_data = VertexUpscaleRequest(
        project_id="demo-project",
        image_bytes=b"input-image",
        api_key=None,
        access_token=None,
    )
    with pytest.raises(UpscaleError):
        upscale_image_with_vertex(request_data)
