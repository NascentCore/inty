import asyncio
import cyclopts

from app.core.agent.prompts import R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT
from app.core.images.fal import ZImageTurboImageToImageInput, ZImageTurboInput, z_image_turbo, z_image_turbo_image_to_image


PROMPT = """
The girl should lay on the floor, and open her legs wide.
"""


ARGS_IMAGE_TO_IMAGE = ZImageTurboImageToImageInput(
    prompt=R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT + "\n" + PROMPT,
    image_url="https://storage.googleapis.com/inty-static/avatars/user-01JWZ34Y4D1C92GD86A5R6EWYJ/user-01JWZ34Y4D1C92GD86A5R6EWYJ/20251113-090114-ed2c326e.jpeg",
    strength=0.6,
    num_images=1,
)

ARGS = ZImageTurboInput(
    prompt=R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT + "\n" + PROMPT,
)


async def main():
    result = await z_image_turbo_image_to_image(
        args=ARGS_IMAGE_TO_IMAGE,
        gcs_uri_base="test-gcs-uri-base",
    )
    print(result.gcs_http_url)


if __name__ == "__main__":
    asyncio.run(main())
