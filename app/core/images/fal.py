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
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Any, AsyncIterator, NamedTuple

import fal_client
import PIL
from langsmith import traceable
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import (
    global_config_loaded_from_config_yaml as global_config,
)
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.gcs import upload_to_gcs
from app.utils.image import (
    IMAGE_SIZE_720_1280,
    ImageFormat,
    ImageSize,
    compress_png_to_jpeg,
    parse_image_data_uri,
)
from app.utils.langsmith import attach_provider_response_to_langsmith_run
from app.utils.models_catalog import (
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
)


@asynccontextmanager
async def _scoped_fal_async_client() -> AsyncIterator[Any]:
    """
    One fal_client.AsyncClient (and its httpx.AsyncClient) per inference call.

    The fal_client package exposes a module-level singleton whose httpx client is
    cached on the AsyncClient instance. That singleton breaks when REPL-style code
    uses a fresh ``asyncio.run()`` per turn (loop closes and may aclose the client)
    or when tools run in a background thread with a different event loop. A dedicated
    client per call avoids sharing a closed client across loops/threads.
    """
    client = fal_client.AsyncClient()
    try:
        yield client
    finally:
        inner = client.__dict__.get("_client")
        if inner is not None and not inner.is_closed:
            await inner.aclose()


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
_CONTENT_TYPE_TO_IMAGE_FORMAT: dict[str, ImageFormat] = {
    "image/jpeg": ImageFormat.JPEG,
    "image/jpg": ImageFormat.JPEG,
    "image/png": ImageFormat.PNG,
    "image/webp": ImageFormat.WEBP,
    "image/gif": ImageFormat.GIF,
    "image/avif": ImageFormat.AVIF,
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
    image_urls: list[str] = Field(
        ...,
        description="""The URLs of the images to edit. Must be a list of two URLs.
        Example: ["https://example.com/image1.png", "https://example.com/image2.png"]
        """,
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
    async with _scoped_fal_async_client() as fal:
        handler = await fal.submit(
            SEEDREAM_V4_5_EDIT.id_on_provider, arguments=args.model_dump()
        )
        attach_provider_response_to_langsmith_run(handler, key="handler")
        raw_result = await handler.get()
        result = FalSeedreamV4_5EditOutput(**raw_result)
        if not result.images:
            raise ValueError("No images returned from SeedreamV4_5Edit")
        first_img = result.images[0]
        if first_img.url.startswith("data:"):
            logger.debug(
                "Uploaded SeedreamV4_5Edit data URI to GCS (first image)"
            )
            upload_result = _upload_image_file_to_gcs_and_return_url(
                first_img, gcs_uri_base, enable_compress_png_to_jpeg=True
            )
            generated_result = GeneratedImageProcessResult(
                size=upload_result.image_size,
                format=upload_result.image_format,
                raw_data=upload_result.file_data,
                raw_data_total_bytes=len(upload_result.file_data),
                gcs_uri=upload_result.gcs_uri,
                gcs_http_url=upload_result.gcs_http_url,
                generated_at=datetime.datetime.now(datetime.timezone.utc),
                raw_response_from_provider=raw_result,
            )
        elif first_img.url.startswith("http://") or first_img.url.startswith(
            "https://"
        ):
            logger.info(
                "SeedreamV4_5Edit returned remote URL output; skipping GCS re-upload: {}",
                first_img.url,
            )
            generated_result = _build_result_from_remote_image_url(
                image_url=first_img.url,
                content_type=first_img.content_type,
                file_name=first_img.file_name,
                file_size=first_img.file_size,
                width=first_img.width,
                height=first_img.height,
                raw_result=raw_result,
            )
        else:
            raise ValueError(
                f"Unsupported image URL format from SeedreamV4_5Edit: {first_img.url}"
            )
        # GCS 上传成功后，trace 中脱敏 data URI，减少 LangSmith 存储压力。
        trace_raw_result = _sanitize_provider_response_for_trace(raw_result)
        attach_provider_response_to_langsmith_run(trace_raw_result)
        return generated_result


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
    seed: int = Field(
        default=0,
        description="Fal: same seed + same prompt + same model version yields the same image.",
    )
    sync_mode: bool = Field(
        default=True,
        description="""
        If True, the media will be returned as a data URI
        and the output data won't be available in the request history.
        Example:
        {
            "url": "data:image/jpeg;base64,..."
        }
        If False, the function will return a url to the fal CDN.
        考虑统一，我们用 sync_mode=True 来处理，并自己上传文件到 GCS。
    """,
    )
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
    file_data: str | None = (
        None  # optional; text-to-image response does not include it
    )
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


def _process_data_uri_image_bytes_for_z_image_turbo(
    image_file: ImageFile,
    *,
    enable_compress_png_to_jpeg: bool = True,
) -> tuple[ImageSize, ImageFormat, bytes]:
    """Parse Fal data URI to bytes (same transform as GCS path); no upload."""
    file_data, image_format = parse_image_data_uri(image_file.url)
    if enable_compress_png_to_jpeg and image_format == ImageFormat.PNG:
        file_data, image_format = (
            compress_png_to_jpeg(file_data),
            ImageFormat.JPEG,
        )
    image_size = ImageSize(width=image_file.width, height=image_file.height)
    return image_size, image_format, file_data


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
        file_data, image_format = (
            compress_png_to_jpeg(file_data),
            ImageFormat.JPEG,
        )
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )
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


def _infer_image_format_from_remote_image(
    *,
    content_type: str | None,
    file_name: str | None,
    image_url: str,
) -> ImageFormat:
    if isinstance(content_type, str):
        normalized_content_type = content_type.strip().lower()
        from_content_type = _CONTENT_TYPE_TO_IMAGE_FORMAT.get(
            normalized_content_type
        )
        if from_content_type is not None:
            return from_content_type

    candidate = file_name or image_url
    candidate_without_query = candidate.split("?", 1)[0]
    if "." in candidate_without_query:
        ext = candidate_without_query.rsplit(".", 1)[1].strip().lower()
        if ext in ("jpg", "jpeg"):
            return ImageFormat.JPEG
        if ext == "png":
            return ImageFormat.PNG
        if ext == "webp":
            return ImageFormat.WEBP
        if ext == "gif":
            return ImageFormat.GIF
        if ext == "avif":
            return ImageFormat.AVIF

    logger.warning(
        "无法从 Fal 返回结果推断图片格式，默认使用 JPEG: content_type={}, file_name={}, url={}",
        content_type,
        file_name,
        image_url,
    )
    return ImageFormat.JPEG


def _build_result_from_remote_image_url(
    *,
    image_url: str,
    content_type: str | None,
    file_name: str | None,
    file_size: int | None,
    width: int | None,
    height: int | None,
    raw_result: Any,
) -> GeneratedImageProcessResult:
    if width is None or height is None:
        raise ValueError(
            "Fal returned remote image URL but did not provide width/height metadata"
        )
    image_format = _infer_image_format_from_remote_image(
        content_type=content_type,
        file_name=file_name,
        image_url=image_url,
    )
    return GeneratedImageProcessResult(
        size=ImageSize(width=width, height=height),
        format=image_format,
        raw_data=None,
        raw_data_total_bytes=(
            file_size if isinstance(file_size, int) and file_size > 0 else 0
        ),
        gcs_uri=image_url,
        gcs_http_url=image_url,
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        raw_response_from_provider=raw_result,
    )


@traceable
async def z_image_turbo(
    args: ZImageTurboInput,
    gcs_uri_base: str,
    *,
    skip_gcs_upload: bool = False,
) -> list[GeneratedImageProcessResult]:
    async with _scoped_fal_async_client() as fal:
        handler = await fal.submit(
            Z_IMAGE_TURBO.id_on_provider, arguments=args.model_dump()
        )
        attach_provider_response_to_langsmith_run(handler, key="handler")
        raw_result = await handler.get()
        result = ZImageTurboOutput(**raw_result)
        logger.debug(
            "ZImageTurbo raw result before processing{} (images_n={}): {}",
            (
                " (skip_gcs_upload)"
                if skip_gcs_upload
                else " and uploading to GCS"
            ),
            len(result.images) if result.images else 0,
            _sanitize_provider_response_for_trace(raw_result),
        )
        if not result.images:
            raise ValueError("No images returned from ZImageTurbo")
        processed_results: list[GeneratedImageProcessResult] = []
        for i, image in enumerate(result.images):
            if image.url.startswith("data:"):
                if skip_gcs_upload:
                    image_size, image_format, file_data = (
                        _process_data_uri_image_bytes_for_z_image_turbo(
                            image, enable_compress_png_to_jpeg=True
                        )
                    )
                    logger.debug(
                        "ZImageTurbo skip_gcs_upload=True; data URI kept local (image index: {})",
                        i,
                    )
                    processed_results.append(
                        GeneratedImageProcessResult(
                            size=image_size,
                            format=image_format,
                            raw_data=file_data,
                            raw_data_total_bytes=len(file_data),
                            gcs_uri="",
                            gcs_http_url="",
                            generated_at=datetime.datetime.now(
                                datetime.timezone.utc
                            ),
                            raw_response_from_provider=raw_result,
                        )
                    )
                else:
                    upload_result = _upload_image_file_to_gcs_and_return_url(
                        image, gcs_uri_base, enable_compress_png_to_jpeg=True
                    )
                    logger.debug(
                        "Uploaded ZImageTurbo data URI to GCS (image index: {})",
                        i,
                    )
                    processed_results.append(
                        GeneratedImageProcessResult(
                            size=upload_result.image_size,
                            format=upload_result.image_format,
                            raw_data=upload_result.file_data,
                            raw_data_total_bytes=len(upload_result.file_data),
                            gcs_uri=upload_result.gcs_uri,
                            gcs_http_url=upload_result.gcs_http_url,
                            generated_at=datetime.datetime.now(
                                datetime.timezone.utc
                            ),
                            raw_response_from_provider=raw_result,
                        )
                    )
                continue

            if image.url.startswith("http://") or image.url.startswith(
                "https://"
            ):
                logger.info(
                    "ZImageTurbo returned remote URL output; skipping GCS re-upload: {}",
                    image.url,
                )
                processed_results.append(
                    _build_result_from_remote_image_url(
                        image_url=image.url,
                        content_type=image.content_type,
                        file_name=image.file_name,
                        file_size=image.file_size,
                        width=image.width,
                        height=image.height,
                        raw_result=raw_result,
                    )
                )
                continue

            raise ValueError(
                f"Unsupported image URL format from ZImageTurbo: {image.url}"
            )
        if not processed_results:
            raise ValueError("No valid images returned from ZImageTurbo")
        trace_raw_result = _sanitize_provider_response_for_trace(raw_result)
        attach_provider_response_to_langsmith_run(trace_raw_result)
        return processed_results


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
    image_url: str = Field(
        description="URL of Image for Image-to-Image generation."
    )
    image_size: ImageSize | ZImageTurboImageToImageImageSizeEnum = (
        ZImageTurboImageToImageImageSizeEnum.PORTRAIT_16_9
    )
    num_inference_steps: int = 8
    seed: int = Field(
        default=0,
        description="Fal: same seed + same prompt + same model version yields the same image.",
    )
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
    *,
    skip_gcs_upload: bool = False,
) -> GeneratedImageProcessResult:
    async with _scoped_fal_async_client() as fal:
        handler = await fal.submit(
            Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider,
            arguments=args.model_dump(),
        )
        attach_provider_response_to_langsmith_run(handler, key="handler")
        raw_result = await handler.get()
        result = ZImageTurboImageToImageOutput(**raw_result)
        logger.debug(
            "ZImageTurboImageToImage raw result before processing{} (images_n={}): {}",
            (
                " (skip_gcs_upload)"
                if skip_gcs_upload
                else " and uploading to GCS"
            ),
            len(result.images) if result.images else 0,
            _sanitize_provider_response_for_trace(raw_result),
        )
        if not result.images:
            raise ValueError("No images returned from ZImageTurboImageToImage")
        first_img = result.images[0]
        if first_img.url.startswith("data:"):
            if skip_gcs_upload:
                image_size, image_format, file_data = (
                    _process_data_uri_image_bytes_for_z_image_turbo(
                        first_img, enable_compress_png_to_jpeg=True
                    )
                )
                logger.debug(
                    "ZImageTurboImageToImage skip_gcs_upload=True; data URI kept local"
                )
                generated_result = GeneratedImageProcessResult(
                    size=image_size,
                    format=image_format,
                    raw_data=file_data,
                    raw_data_total_bytes=len(file_data),
                    gcs_uri="",
                    gcs_http_url="",
                    generated_at=datetime.datetime.now(datetime.timezone.utc),
                    raw_response_from_provider=raw_result,
                )
            else:
                upload_result = _upload_image_file_to_gcs_and_return_url(
                    first_img, gcs_uri_base, enable_compress_png_to_jpeg=True
                )
                logger.debug(
                    "Uploaded ZImageTurboImageToImage data URI to GCS: {}",
                    upload_result.gcs_http_url,
                )
                generated_result = GeneratedImageProcessResult(
                    size=upload_result.image_size,
                    format=upload_result.image_format,
                    raw_data=upload_result.file_data,
                    raw_data_total_bytes=len(upload_result.file_data),
                    gcs_uri=upload_result.gcs_uri,
                    gcs_http_url=upload_result.gcs_http_url,
                    generated_at=datetime.datetime.now(datetime.timezone.utc),
                    raw_response_from_provider=raw_result,
                )
        elif first_img.url.startswith("http://") or first_img.url.startswith(
            "https://"
        ):
            logger.info(
                "ZImageTurboImageToImage returned remote URL output; skipping GCS re-upload: {}",
                first_img.url,
            )
            generated_result = _build_result_from_remote_image_url(
                image_url=first_img.url,
                content_type=first_img.content_type,
                file_name=first_img.file_name,
                file_size=first_img.file_size,
                width=first_img.width,
                height=first_img.height,
                raw_result=raw_result,
            )
        else:
            raise ValueError(
                f"Unsupported image URL format from ZImageTurboImageToImage: {first_img.url}"
            )
        trace_raw_result = _sanitize_provider_response_for_trace(raw_result)
        attach_provider_response_to_langsmith_run(trace_raw_result)
        return generated_result
