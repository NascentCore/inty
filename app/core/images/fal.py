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
import io
import uuid
from enum import StrEnum

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


# ImageFormat to MIME content_type for GCS upload.
_IMAGE_FORMAT_TO_CONTENT_TYPE: dict[ImageFormat, str] = {
    ImageFormat.JPEG: "image/jpeg",
    ImageFormat.JPG: "image/jpeg",
    ImageFormat.PNG: "image/png",
    ImageFormat.WEBP: "image/webp",
    ImageFormat.GIF: "image/gif",
    ImageFormat.AVIF: "image/avif",
}


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


def _data_uri_to_generated_image_process_result(
    data_uri: str,
    gcs_uri_base: str,
    raw_response_from_provider: object,
    width_hint: int | None = None,
    height_hint: int | None = None,
) -> GeneratedImageProcessResult:
    """Parse data URI, upload to GCS, return GeneratedImageProcessResult. Used by FAL entrypoints."""
    file_data, image_format = parse_image_data_uri(data_uri)
    if image_format == ImageFormat.PNG:
        file_data, image_format = compress_png_to_jpeg(file_data), ImageFormat.JPEG
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    gcs_path = f"{gcs_uri_base}/{timestamp}_{uuid.uuid4().hex[:8]}.{image_format.value}"
    gcs_http_url = upload_to_gcs(
        file_data=file_data,
        content_type=_IMAGE_FORMAT_TO_CONTENT_TYPE[image_format],
        bucket_name=global_config.gcs.bucket,
        path=gcs_path,
    )
    bucket_name = global_config.gcs.bucket
    gcs_uri = f"gs://{bucket_name}/{gcs_path}"
    if width_hint is not None and height_hint is not None:
        width, height = width_hint, height_hint
    else:
        pil_image = PIL.Image.open(io.BytesIO(file_data))
        width, height = pil_image.size
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return GeneratedImageProcessResult(
        size=ImageSize(width=width, height=height),
        format=image_format,
        raw_data=file_data,
        raw_data_total_bytes=len(file_data),
        gcs_uri=gcs_uri,
        gcs_http_url=gcs_http_url,
        generated_at=now_utc,
        raw_response_from_provider=raw_response_from_provider,
    )


@traceable
async def seedream_v4_5_edit(
    args: FalSeedreamV4_5EditInput,
    gcs_uri_base: str,
) -> GeneratedImageProcessResult:
    handler = await fal_client.submit_async(SEEDREAM_V4_5_EDIT.id_on_provider, arguments=args.model_dump())
    attach_provider_response_to_langsmith_run(handler, key="handler")
    raw_result = await handler.get()
    attach_provider_response_to_langsmith_run(raw_result)
    result = FalSeedreamV4_5EditOutput(**raw_result)
    if not result.images:
        raise ValueError("No images returned from SeedreamV4_5Edit")
    first_img = result.images[0]
    if not first_img.url.startswith("data:"):
        raise ValueError(f"Image URL is not a data URI: {first_img.url}")
    logger.debug("Uploaded SeedreamV4_5Edit data URI to GCS (first image)")
    return _data_uri_to_generated_image_process_result(
        data_uri=first_img.url,
        gcs_uri_base=gcs_uri_base,
        raw_response_from_provider=raw_result,
        width_hint=first_img.width,
        height_hint=first_img.height,
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


class ZImageTurboResult(BaseModel):
    """
    https://fal.ai/models/fal-ai/z-image/turbo/api#schema-output
    """
    images: list[ImageFile] | None = None
    timings: dict[str, float] | None = None
    seed: int | None = None
    has_nsfw_concepts: list[bool] | None = None
    prompt: str


def _upload_data_uri_to_gcs_and_return_url(
    data_uri: str,
    gcs_uri_base: str,
    enable_compress_png_to_jpeg: bool = True,
) -> str:
    """Parse image data URI, upload to GCS with gcs_uri_base as path prefix, return public HTTP URL."""
    file_data, image_format = parse_image_data_uri(data_uri)
    if enable_compress_png_to_jpeg and image_format == ImageFormat.PNG:
        file_data, image_format = compress_png_to_jpeg(file_data), ImageFormat.JPEG
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    gcs_path = f"{gcs_uri_base}/{timestamp}_{uuid.uuid4().hex[:8]}.{image_format.value}"
    return upload_to_gcs(
        file_data=file_data,
        content_type=_IMAGE_FORMAT_TO_CONTENT_TYPE[image_format],
        bucket_name=global_config.gcs.bucket,
        path=gcs_path,
    )


@traceable
async def z_image_turbo(
    args: ZImageTurboInput,
    gcs_uri_base: str,
) -> GeneratedImageProcessResult:
    handler = await fal_client.submit_async(Z_IMAGE_TURBO.id_on_provider, arguments=args.model_dump())
    raw_result = await handler.get()
    raw_result["handler"] = handler
    attach_provider_response_to_langsmith_run(raw_result)
    result = ZImageTurboResult(**raw_result)
    logger.debug("ZImageTurbo raw result before processing and uploading to GCS: {}", raw_result)
    if not result.images:
        raise ValueError("No images returned from ZImageTurbo")
    first_img = result.images[0]
    if not first_img.url.startswith("data:"):
        raise ValueError(f"Image URL is not a data URI: {first_img.url}")
    logger.debug("Uploaded ZImageTurbo data URI to GCS (first image)")
    return _data_uri_to_generated_image_process_result(
        data_uri=first_img.url,
        gcs_uri_base=gcs_uri_base,
        raw_response_from_provider=raw_result,
        width_hint=first_img.width,
        height_hint=first_img.height,
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
    output_format: ImageFormat = ImageFormat.PNG
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
async def z_image_turbo_image_to_image(args: ZImageTurboImageToImageInput) -> ZImageTurboImageToImageOutput:
    handler = await fal_client.submit_async(Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider, arguments=args.model_dump())
    raw_result = await handler.get()
    raw_result["handler"] = handler
    attach_provider_response_to_langsmith_run(raw_result)
    result = ZImageTurboImageToImageOutput(**raw_result)
    logger.debug(f"ZImageTurboImageToImage raw result before processing and uploading to GCS: {raw_result}")
    if not result.images:
        raise ValueError("No images returned from ZImageTurboImageToImage")

    new_images: list[ImageFile] = []
    for img in result.images:
        if not img.url.startswith("data:"):
            raise ValueError(f"Image URL is not a data URI: {img.url}")
        gcs_url = _upload_data_uri_to_gcs_and_return_url(img.url, gcs_uri_base="fal_images")
        logger.debug("Uploaded ZImageTurboImageToImage data URI to GCS: {}", gcs_url)
        new_images.append(img.model_copy(update={
            "url": gcs_url,
            "file_data": None,
        }))
    logger.debug("ZImageTurboImageToImageResult after processing and uploading to GCS: {}", result)
    return result.model_copy(update={"images": new_images})
