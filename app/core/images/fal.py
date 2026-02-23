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
"""

from enum import StrEnum
import fal_client
from langsmith import traceable
from pydantic import BaseModel, Field

from app.utils.image import IMAGE_SIZE_720_1280, ImageFormat, ImageSize
from app.utils.langsmith import attach_provider_response_to_langsmith_run
from app.utils.models_catalog import SEEDREAM_V4_5_EDIT, Z_IMAGE_TURBO


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


class FalSeedreamV4_5EditArgs(BaseModel):
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

class FalSeedreamV4_5EditResult(BaseModel):
    """
    https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api#schema-output
    """
    images: list[Image] | None = None


@traceable
async def seedream_v4_5_edit(args: FalSeedreamV4_5EditArgs) -> FalSeedreamV4_5EditResult:
    handler = await fal_client.submit_async(SEEDREAM_V4_5_EDIT.id_on_provider, arguments=args.model_dump())
    attach_provider_response_to_langsmith_run(handler, key="handler")
    result = await handler.get()
    attach_provider_response_to_langsmith_run(result)
    return FalSeedreamV4_5EditResult(**result)


class AccelerationEnum(StrEnum):
    NONE = "none"
    REGULAR = "regular"
    HIGH = "high"


class ImgGenArgs(BaseModel):
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


@traceable
async def z_image_turbo(args: ImgGenArgs) -> ZImageTurboResult:
    handler = await fal_client.submit_async(Z_IMAGE_TURBO.id_on_provider, arguments=args.model_dump())
    raw_result = await handler.get()
    raw_result["handler"] = handler
    attach_provider_response_to_langsmith_run(raw_result)
    result = ZImageTurboResult(**raw_result)
    return result
