"""Vertex AI Imagen 4.0 图像超分调用封装。"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

DEFAULT_VERTEX_IMAGEN_UPSCALE_DOC_URL = "https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/imagen/4-0-upscale?hl=en"
DEFAULT_MODEL_ID = "imagen-4.0-upscale-preview"
DEFAULT_REGION = "us-central1"
DEFAULT_PROMPT = "Upscale the image"
DEFAULT_OUTPUT_MIME_TYPE = "image/png"
DEFAULT_COMPRESSION_QUALITY = 75
DEFAULT_TIMEOUT_SECONDS = 120
VALID_UPSCALE_FACTORS = {"x2", "x3", "x4"}


class UpscaleError(RuntimeError):
    """图像超分请求失败。"""


@dataclass(frozen=True, slots=True)
class VertexUpscaleRequest:
    project_id: str
    image_bytes: bytes
    api_key: str | None = None
    access_token: str | None = None
    region: str = DEFAULT_REGION
    model_id: str = DEFAULT_MODEL_ID
    prompt: str = DEFAULT_PROMPT
    upscale_factor: str = "x2"
    output_mime_type: str = DEFAULT_OUTPUT_MIME_TYPE
    compression_quality: int = DEFAULT_COMPRESSION_QUALITY
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class VertexUpscaleResult:
    image_bytes: bytes
    mime_type: str
    model_id: str
    request_url: str
    raw_response: dict[str, Any]


def build_vertex_predict_endpoint(
    *, project_id: str, region: str, model_id: str
) -> str:
    encoded_project = parse.quote(project_id.strip(), safe="-_:.")
    encoded_region = parse.quote(region.strip(), safe="-_:.")
    encoded_model = parse.quote(model_id.strip(), safe="-_.")
    return (
        f"https://{encoded_region}-aiplatform.googleapis.com/v1/projects/{encoded_project}"
        f"/locations/{encoded_region}/publishers/google/models/{encoded_model}:predict"
    )


def normalize_upscale_factor(upscale_factor: str | int) -> str:
    if isinstance(upscale_factor, int):
        normalized = f"x{upscale_factor}"
    else:
        normalized = str(upscale_factor).strip().lower()
    if normalized not in VALID_UPSCALE_FACTORS:
        raise UpscaleError(
            f"无效 upscale_factor={upscale_factor!r}，仅支持 {sorted(VALID_UPSCALE_FACTORS)}"
        )
    return normalized


MIME_TYPES_SUPPORTING_COMPRESSION_QUALITY = frozenset({"image/jpeg", "image/webp"})


def build_upscale_payload(
    *,
    image_bytes: bytes,
    prompt: str,
    upscale_factor: str,
    output_mime_type: str,
    compression_quality: int,
) -> dict[str, Any]:
    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    output_options: dict[str, Any] = {"mimeType": output_mime_type}
    if output_mime_type in MIME_TYPES_SUPPORTING_COMPRESSION_QUALITY:
        output_options["compressionQuality"] = compression_quality
    return {
        "instances": [
            {
                "prompt": prompt,
                "image": {"bytesBase64Encoded": image_base64},
            }
        ],
        "parameters": {
            "mode": "upscale",
            "outputOptions": output_options,
            "upscaleConfig": {"upscaleFactor": upscale_factor},
        },
    }


def append_api_key(url: str, api_key: str | None) -> str:
    if not api_key:
        return url
    split_result = parse.urlsplit(url)
    query_pairs = parse.parse_qsl(split_result.query, keep_blank_values=True)
    query_pairs.append(("key", api_key))
    query = parse.urlencode(query_pairs)
    return parse.urlunsplit(split_result._replace(query=query))


def build_auth_headers(
    *, api_key: str | None, access_token: str | None
) -> dict[str, str]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["x-goog-api-key"] = api_key
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def parse_upscale_response(response_json: dict[str, Any]) -> tuple[bytes, str]:
    predictions = response_json.get("predictions")
    if not isinstance(predictions, list) or not predictions:
        raise UpscaleError("响应中缺少 predictions")

    prediction = predictions[0]
    if not isinstance(prediction, dict):
        raise UpscaleError("predictions[0] 格式错误")

    encoded_image = prediction.get("bytesBase64Encoded")
    if not isinstance(encoded_image, str) or not encoded_image:
        raise UpscaleError("响应中缺少 bytesBase64Encoded")

    mime_type = prediction.get("mimeType")
    resolved_mime_type = (
        mime_type
        if isinstance(mime_type, str) and mime_type
        else DEFAULT_OUTPUT_MIME_TYPE
    )

    try:
        image_bytes = base64.b64decode(encoded_image, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise UpscaleError("响应中的图片数据不是有效 base64") from exc
    return image_bytes, resolved_mime_type


def _validate_request(request_data: VertexUpscaleRequest) -> None:
    if not request_data.project_id.strip():
        raise UpscaleError("project_id 不能为空")
    if not request_data.region.strip():
        raise UpscaleError("region 不能为空")
    if not request_data.model_id.strip():
        raise UpscaleError("model_id 不能为空")
    if not request_data.image_bytes:
        raise UpscaleError("image_bytes 不能为空")
    if request_data.compression_quality < 0 or request_data.compression_quality > 100:
        raise UpscaleError("compression_quality 必须在 0-100")
    if request_data.timeout_seconds <= 0:
        raise UpscaleError("timeout_seconds 必须大于 0")
    if not request_data.api_key and not request_data.access_token:
        raise UpscaleError("请提供 API Key 或 Access Token")


def upscale_image_with_vertex(
    request_data: VertexUpscaleRequest,
) -> VertexUpscaleResult:
    _validate_request(request_data)
    normalized_upscale_factor = normalize_upscale_factor(request_data.upscale_factor)
    endpoint = build_vertex_predict_endpoint(
        project_id=request_data.project_id,
        region=request_data.region,
        model_id=request_data.model_id,
    )
    request_url = append_api_key(endpoint, request_data.api_key)
    payload = build_upscale_payload(
        image_bytes=request_data.image_bytes,
        prompt=request_data.prompt,
        upscale_factor=normalized_upscale_factor,
        output_mime_type=request_data.output_mime_type,
        compression_quality=request_data.compression_quality,
    )
    body = json.dumps(payload).encode("utf-8")
    headers = build_auth_headers(
        api_key=request_data.api_key,
        access_token=request_data.access_token,
    )
    http_request = request.Request(
        request_url, data=body, headers=headers, method="POST"
    )

    try:
        with request.urlopen(
            http_request, timeout=request_data.timeout_seconds
        ) as response:
            response_body = response.read()
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise UpscaleError(f"Vertex AI 请求失败: HTTP {exc.code} - {details}") from exc
    except error.URLError as exc:
        raise UpscaleError(f"网络错误: {exc.reason}") from exc

    try:
        response_json = json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise UpscaleError("响应不是合法 JSON") from exc

    image_bytes, mime_type = parse_upscale_response(response_json)
    return VertexUpscaleResult(
        image_bytes=image_bytes,
        mime_type=mime_type,
        model_id=request_data.model_id,
        request_url=request_url,
        raw_response=response_json,
    )
