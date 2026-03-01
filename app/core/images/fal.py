"""
https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api

export FAL_KEY="YOUR_API_KEY"

import asyncio
import fal_client

async def subscribe():
    handler = await fal_client.submit_async(
        "fal-ai/bytedance/seedream/v4.5/edit",
        arguments={
            "prompt": "Replace the product in Figure 1 with that in Figure 2. For the title copy the text in Figure 3 to the top of the screen, the title should have a clear contrast with the background but not be overly eye-catching.",
            "image_urls": ["https://storage.googleapis.com/falserverless/example_inputs/seedreamv45/seedream_v45_edit_input_1.png", "https://storage.googleapis.com/falserverless/example_inputs/seedreamv45/seedream_v45_edit_input_2.png", "https://storage.googleapis.com/falserverless/example_inputs/seedreamv45/seedream_v45_edit_input_3.png"]
        },
    )

    async for event in handler.iter_events(with_logs=True):
        print(event)

    result = await handler.get()

    print(result)


if __name__ == "__main__":
    asyncio.run(subscribe())

Once the request is completed, you can fetch the result. See the Output Schema for the expected result format.
result = await fal_client.result_async("fal-ai/bytedance/seedream/v4.5/edit", request_id)

output format:
{
  "images": [
    {
      "url": "https://storage.googleapis.com/falserverless/example_outputs/seedreamv45/seedream_v45_edit_output.png"
    }
  ]
}

NOTES:
- partner model's safety tolerance does not seem get loosened on fal.ai.
  "safety_tolerance": "6" for https://fal.ai/models/fal-ai/nano-banana/api is still rejected.
"""

import datetime
import copy
import io
import uuid
from enum import StrEnum
from typing import Any, NamedTuple

import fal_client
import PIL
from langsmith import traceable
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import global_config_loaded_from_config_yaml as global_config
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.gcs import upload_to_gcs
from app.utils.image import IMAGE_SIZE_720_1280, ImageFormat, ImageSize, compress_png_to_jpeg, parse_image_data_uri
from app.utils.langsmith import attach_provider_response_to_langsmith_run
from app.utils.models_catalog import SEEDREAM_V4_5_EDIT, Z_IMAGE_TURBO, Z_IMAGE_TURBO_IMAGE_TO_IMAGE


class _DataUriUploadResult(NamedTuple):
    """Result of parsing data URI, optional PNG→JPEG compression, and uploading to GCS."""

    gcs_uri: str
    gcs_http_url: str
    file_data: bytes
    image_format: ImageFormat
    gcs_path: str
    image_size: ImageSize


# ImageFormat to MIME content_type for GCS upload.
_IMAGE_FORMAT_TO_CONTENT_TYPE: dict[ImageFormat, str] = {
    ImageFormat.JPEG: "image/jpeg",
    ImageFormat.JPG: "image/jpeg",
    ImageFormat.PNG: "image/png",
    ImageFormat.WEBP: "image/webp",
    ImageFormat.GIF: "image/gif",
    ImageFormat.AVIF: "image/avif",
}

_LANGSMITH_OMITTED_DATA_URI_TEXT = "[omitted data URI after GCS upload]"


def _build_omitted_data_uri_marker(raw_value: str) -> str:
    return f"{_LANGSMITH_OMITTED_DATA_URI_TEXT} ({len(raw_value)} chars)"


def _remove_data_uri_inplace(payload: dict[str, Any] | list[Any]) -> None:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, (dict, list)):
                _remove_data_uri_inplace(item)
        return

    url = payload.get("url")
    if isinstance(url, str) and url.startswith("data:"):
        payload["url"] = _build_omitted_data_uri_marker(url)

    for value in payload.values():
        if isinstance(value, (dict, list)):
            _remove_data_uri_inplace(value)


def _sanitize_provider_response_for_trace(response: Any) -> Any:
    """
    上传 GCS 成功后，LangSmith trace 内不保留 provider response 中的 data URI 原文，
    避免 trace 体积被 base64 图片放大。
    """
    if response is None:
        return None

    if isinstance(response, dict):
        payload: Any = copy.deepcopy(response)
    elif isinstance(response, BaseModel):
        payload = response.model_dump(mode="python")
    else:
        model_dump = getattr(response, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(mode="python")
            if isinstance(dumped, dict):
                payload = dumped
            else:
                return response
        else:
            return response

    if isinstance(payload, (dict, list)):
        _remove_data_uri_inplace(payload)
    return payload


class ImageSizeEnum(StrEnum):
    """
    https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api#schema-input-image_size
    仅供参考，默认值为 
    """
    SQUARE_HD = "square_hd"
    SQUARE = "square"
    PORTRAIT_4_3 = "portrait_4_3"
    PORTRAIT_16_9 = "portrait_16_9"
    LANDSCAPE_4_3 = "landscape_4_3"
    LANDSCAPE_16_9 = "landscape_16_9"
    AUTO_2K = "auto_2K"
    AUTO_4K = "auto_4K"


class EnhancePromptModeEnum(StrEnum):
    STANDARD = "standard"
    FAST = "fast"


class FalSeedreamV4_5EditInput(BaseModel):
    """
    https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api#schema-input
    """
    prompt: str
    image_size: ImageSize | ImageSizeEnum = IMAGE_SIZE_720_1280
    num_images: int = 1
    # max_images
    # seed
    sync_mode: bool = True
    enable_safety_checker: bool = False
    enhance_prompt_mode: EnhancePromptModeEnum = EnhancePromptModeEnum.STANDARD
    image_urls: list[str] = Field(...,
        description="""The URLs of the images to edit. Must be a list of two URLs.
        Example: ["https://example.com/image1.png", "https://example.com/image2.png"]
        """
    )


class Image(BaseModel):
    """
    https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api#type-Image
    """
    url: str
    content_type: str
    file_name: str
    file_size: int
    width: int | None = None
    height: int | None = None

class FalSeedreamV4_5EditOutput(BaseModel):
    """
    https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api#schema-output
    """
    images: list[Image] | None = None


@traceable
async def seedream_v4_5_edit(
    args: FalSeedreamV4_5EditInput,
    gcs_uri_base: str,
) -> GeneratedImageProcessResult:
    handler = await fal_client.submit_async(SEEDREAM_V4_5_EDIT.id_on_provider, arguments=args.model_dump())
    attach_provider_response_to_langsmith_run(handler, key="handler")
    raw_result = await handler.get()
    result = FalSeedreamV4_5EditOutput(**raw_result)
    if not result.images:
        raise ValueError("No images returned from SeedreamV4_5Edit")
    first_img = result.images[0]
    if not first_img.url.startswith("data:"):
        raise ValueError(f"Image URL is not a data URI: {first_img.url}")
    logger.debug("Uploaded SeedreamV4_5Edit data URI to GCS (first image)")
    upload_result = _upload_image_file_to_gcs_and_return_url(
        first_img, gcs_uri_base, enable_compress_png_to_jpeg=True
    )
    # GCS 上传成功后，trace 中脱敏 data URI，减少 LangSmith 存储压力。
    trace_raw_result = _sanitize_provider_response_for_trace(raw_result)
    attach_provider_response_to_langsmith_run(trace_raw_result)
    return GeneratedImageProcessResult(
        size=upload_result.image_size,
        format=upload_result.image_format,
        raw_data=upload_result.file_data,
        raw_data_total_bytes=len(upload_result.file_data),
        gcs_uri=upload_result.gcs_uri,
        gcs_http_url=upload_result.gcs_http_url,
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        raw_response_from_provider=raw_result,
    )


class AccelerationEnum(StrEnum):
    NONE = "none"
    REGULAR = "regular"
    HIGH = "high"


class ZImageTurboInput(BaseModel):
    """
    https://fal.ai/models/fal-ai/z-image/turbo/api#schema-input
    """
    prompt: str
    image_size: ImageSize | ImageSizeEnum = IMAGE_SIZE_720_1280
    num_inference_steps: int = 8
    seed: int | None = None
    sync_mode: bool = Field(default=True, description="""
        If True, the media will be returned as a data URI
        and the output data won't be available in the request history.
        Example:
        {
            "url": "data:image/jpeg;base64,..."
        }
        If False, the function will return a url to the fal CDN.
        考虑统一，我们用 sync_mode=True 来处理，并自己上传文件到 GCS。
    """)
    num_images: int = 1
    enable_safety_checker: bool = False
    output_format: ImageFormat = ImageFormat.JPEG
    acceleration: AccelerationEnum = AccelerationEnum.NONE
    enable_prompt_expansion: bool = False


class ImageFile(BaseModel):
    """
    https://fal.ai/models/fal-ai/z-image/turbo/image-to-image/api#type-ImageFile
    Used for testing fal ai API, z-image is fast and cheap.
    """
    url: str
    content_type: str
    file_name: str | None = None
    file_size: int | None = None
    file_data: str | None = None  # optional; text-to-image response does not include it
    width: int
    height: int


class ZImageTurboOutput(BaseModel):
    """
    https://fal.ai/models/fal-ai/z-image/turbo/api#schema-output
    """
    images: list[ImageFile] | None = None
    timings: dict[str, float] | None = None
    seed: int | None = None
    has_nsfw_concepts: list[bool] | None = None
    prompt: str


def _upload_image_file_to_gcs_and_return_url(
    image_file: ImageFile,
    gcs_uri_base: str,
    enable_compress_png_to_jpeg: bool = True,
) -> _DataUriUploadResult:
    """
    Parse image data URI, upload to GCS with gcs_uri_base as path prefix; return URL, file_data, format, path.
    The data URI is a base64 encoded image string with MIME type and base64 encoding.
    eg: data:image/jpeg;base64,/9j/4A...
    """
    file_data, image_format = parse_image_data_uri(image_file.url)
    if enable_compress_png_to_jpeg and image_format == ImageFormat.PNG:
        file_data, image_format = compress_png_to_jpeg(file_data), ImageFormat.JPEG
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    gcs_path = f"{gcs_uri_base}/{timestamp}_{uuid.uuid4().hex[:8]}.{image_format.value}"
    gcs_uri = f"gs://{global_config.gcs.bucket}/{gcs_path}"
    gcs_http_url = upload_to_gcs(
        file_data=file_data,
        content_type=_IMAGE_FORMAT_TO_CONTENT_TYPE[image_format],
        bucket_name=global_config.gcs.bucket,
        path=gcs_path,
    )
    image_size = ImageSize(width=image_file.width, height=image_file.height)
    return _DataUriUploadResult(
        gcs_uri=gcs_uri,
        gcs_http_url=gcs_http_url,
        file_data=file_data,
        image_format=image_format,
        gcs_path=gcs_path,
        image_size=image_size,
    )


@traceable
async def z_image_turbo(
    args: ZImageTurboInput,
    gcs_uri_base: str,
) -> GeneratedImageProcessResult:
    handler = await fal_client.submit_async(Z_IMAGE_TURBO.id_on_provider, arguments=args.model_dump())
    attach_provider_response_to_langsmith_run(handler, key="handler")
    raw_result = await handler.get()
    result = ZImageTurboOutput(**raw_result)
    logger.debug("ZImageTurbo raw result before processing and uploading to GCS: {}", raw_result)
    if not result.images:
        raise ValueError("No images returned from ZImageTurbo")
    first_img = result.images[0]
    if not first_img.url.startswith("data:"):
        raise ValueError(f"Image URL is not a data URI: {first_img.url}")
    logger.debug("Uploaded ZImageTurbo data URI to GCS (first image)")
    upload_result = _upload_image_file_to_gcs_and_return_url(
        first_img, gcs_uri_base, enable_compress_png_to_jpeg=True
    )
    trace_raw_result = _sanitize_provider_response_for_trace(raw_result)
    attach_provider_response_to_langsmith_run(trace_raw_result)
    return GeneratedImageProcessResult(
        size=upload_result.image_size,
        format=upload_result.image_format,
        raw_data=upload_result.file_data,
        raw_data_total_bytes=len(upload_result.file_data),
        gcs_uri=upload_result.gcs_uri,
        gcs_http_url=upload_result.gcs_http_url,
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        raw_response_from_provider=raw_result,
    )


class ZImageTurboImageToImageImageSizeEnum(StrEnum):
    """Preset names for image_size; use ImageSize(width=..., height=...) for custom."""
    SQUARE_HD = "square_hd"
    SQUARE = "square"
    PORTRAIT_4_3 = "portrait_4_3"
    PORTRAIT_16_9 = "portrait_16_9"
    LANDSCAPE_4_3 = "landscape_4_3"
    LANDSCAPE_16_9 = "landscape_16_9"
    AUTO = "auto"


class ZImageTurboImageToImageInput(BaseModel):
    """
    https://fal.ai/models/fal-ai/z-image/turbo/image-to-image/api
    https://fal.ai/models/fal-ai/z-image/turbo/image-to-image/api#schema-input
    """
    prompt: str = Field(description="The prompt to generate an image from.")
    image_url: str = Field(description="URL of Image for Image-to-Image generation.")
    image_size: ImageSize | ZImageTurboImageToImageImageSizeEnum = (
        ZImageTurboImageToImageImageSizeEnum.PORTRAIT_16_9
    )
    num_inference_steps: int = 8
    seed: int | None = None
    sync_mode: bool = Field(
        default=True,
        description="If True, the media will be returned as a data URI and the output data won't be available in the request history.",
    )
    num_images: int = 1
    enable_safety_checker: bool = False
    output_format: ImageFormat = ImageFormat.JPEG
    acceleration: AccelerationEnum = AccelerationEnum.REGULAR
    enable_prompt_expansion: bool = Field(
        default=False,
        description="Whether to enable prompt expansion. Note: this will increase the price by 0.0025 credits per request.",
    )
    strength: float = Field(
        default=0.6,
        description="The strength of the image-to-image conditioning.",
    )


class ZImageTurboImageToImageOutput(BaseModel):
    """
    https://fal.ai/models/fal-ai/z-image/turbo/image-to-image/api#schema-output
    """
    images: list[ImageFile] | None = Field(
        default=None,
        description="The generated image files info.",
    )
    timings: dict[str, float] | None = Field(
        default=None,
        description="The timings of the generation process.",
    )
    seed: int | None = Field(
        default=None,
        description="Seed of the generated Image. It will be the same value of the one passed in the input or the randomly generated that was used in case none was passed.",
    )
    has_nsfw_concepts: list[bool] | None = Field(
        default=None,
        description="Whether the generated images contain NSFW concepts.",
    )
    prompt: str = Field(description="The prompt used for generating the image.")


@traceable
async def z_image_turbo_image_to_image(
    args: ZImageTurboImageToImageInput,
    gcs_uri_base: str,
) -> GeneratedImageProcessResult:
    handler = await fal_client.submit_async(Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider, arguments=args.model_dump())
    attach_provider_response_to_langsmith_run(handler, key="handler")
    raw_result = await handler.get()
    result = ZImageTurboImageToImageOutput(**raw_result)
    logger.debug("ZImageTurboImageToImage raw result before processing and uploading to GCS: {}", raw_result)
    if not result.images:
        raise ValueError("No images returned from ZImageTurboImageToImage")
    first_img = result.images[0]
    if not first_img.url.startswith("data:"):
        raise ValueError(f"Image URL is not a data URI: {first_img.url}")
    upload_result = _upload_image_file_to_gcs_and_return_url(
        first_img, gcs_uri_base, enable_compress_png_to_jpeg=True
    )
    logger.debug("Uploaded ZImageTurboImageToImage data URI to GCS: {}", upload_result.gcs_http_url)
    trace_raw_result = _sanitize_provider_response_for_trace(raw_result)
    attach_provider_response_to_langsmith_run(trace_raw_result)
    return GeneratedImageProcessResult(
        size=upload_result.image_size,
        format=upload_result.image_format,
        raw_data=upload_result.file_data,
        raw_data_total_bytes=len(upload_result.file_data),
        gcs_uri=upload_result.gcs_uri,
        gcs_http_url=upload_result.gcs_http_url,
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        raw_response_from_provider=raw_result,
    )
