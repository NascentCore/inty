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

import asyncio
import fal_client
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pydantic import BaseModel

from app.utils.langsmith import attach_provider_response_to_langsmith_run
from app.utils.models_catalog import SEEDREAM_V4_5_EDIT, Z_IMAGE_TURBO


class FalSeedreamV4_5EditArgs(BaseModel):
    prompt: str
    image_urls: list[str]


@traceable
async def seedream_v4_5_edit(args: FalSeedreamV4_5EditArgs):
    handler = await fal_client.submit_async(SEEDREAM_V4_5_EDIT.id_on_provider, arguments=args.model_dump())
    return handler


class ImgGenArgs(BaseModel):
    prompt: str


class ImageFile(BaseModel):
    """
    https://fal.ai/models/fal-ai/z-image/turbo/image-to-image/api#type-ImageFile
    Used for testing fal ai API, z-image is fast and cheap.
    """
    url: str
    content_type: str
    file_name: str
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
    attach_provider_response_to_langsmith_run(raw_result)
    result = ZImageTurboResult(**raw_result)
    print(result)
    return result
