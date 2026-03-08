#!/usr/bin/env python3
"""
Replay a chat-to-image trace request from LangSmith.

Key steps:
1) Load a trace record from LangSmith (or from a previously saved JSON file).
2) Normalize and persist the full trace runs for repeatable offline analysis.
3) Rebuild one provider request from trace inputs and replay it against real APIs.
"""

from __future__ import annotations

import asyncio

from app.core.images.fal import AccelerationEnum, ImageSizeEnum, ZImageTurboImageToImageInput, z_image_turbo_image_to_image
from app.utils.image import ImageFormat, ImageSize


prompt="""
Generate an image of the character in the reference image.
The scene is a close-up shot of the character's face.
The character is looking directly at the viewer with a neutral, yet intense expression.

The character is covering her upper body with a purple veil.
The facial features of the character in the reference image should be identical to the reference image.

Artistic Style:
Genre: Traditional Anime/Manga character illustration with high-quality, polished digital painting.
Lighting & Shading: Strong, dramatic use of chiaroscuro. The face is dramatically lit from above and slightly to the side, creating a clear dividing line of shadow and highlight that emphasizes form and adds to the character's mysterious demeanor.
Overall Vibe: Elegant, mysterious, and exotic, with a classic, classic fantasy RPG feel. The details are clean and refined.

Facial Features:
Face Shape: Softly defined, oval-shaped face, but the lower half is mostly concealed.
Eyes: This is the most striking feature. The eyes are large, expressive, and detailed in a classic anime style. They have a striking deep amethyst/purple color with multiple points of light reflection (pupils are darker). The eye shape is almond, with elegant, dark eyelashes that fan out dramatically.
Eyebrows: Medium-length, thin, and neatly groomed. They follow the line of the eyes, pointing inward and slightly upward, conveying a focused, perhaps slightly intense or serious gaze.
Nose: Primarily obscured, but the bridge is visible, suggesting a fine, straight profile. The nostrils are not visible.
Mouth: Fully obscured by the mask.
Ears: Both ears are partially visible, with hair pulled away, showing simple, elegant gold drop earrings with a red gemstone.
Skin Tone: A smooth, light, creamy peach complexion, which stands out against the darker, cool-toned clothing.

Hairstyle:
Color: A warm, lustrous golden blonde.
Style: The hair is parted in the middle and styled into two loose, medium-length pigtails that frame her neck. Her hair is kept tidy but natural.
Detail: Both pigtails are held by golden bangles or rings (matching her earrings). Her hair is pulled away from her face, making her eyes the clear focus.

Clothing & Accessories (Visible in the Image):
Face Mask (Veil): A semi-sheer, dusty-mauve/lavender purple veil covers her nose and mouth. It has a beautiful, intricate gold embroidered trim along the top edge, resting just below her cheekbones.
Necklace/Neckwear: Multiple gold accessories frame her neck. The uppermost is a thick, ornate gold collar that is integrated with her purple headpiece/veil. Below that are multiple strands of a heavy, gold chain necklace made of flattened disks (pennies/coins) that rest at her collarbone.
Clothing: A simple, high-collared light pink or peach-colored top is visible below her necklaces, providing a soft contrast.

Pose & Composition:
Angle: A direct, head-on (frontal) medium-close-up shot. The character is looking directly at the viewer with a neutral, yet intense expression.
Background: A simple, dark, and undefined textured background (perhaps deep grey/black), which draws all attention to the character.

"""


reference_image_url = "https://storage.googleapis.com/inty-static/avatars/user-01JWZ34Y4D1C92GD86A5R6EWYJ/user-01JWZ34Y4D1C92GD86A5R6EWYJ/20251218-043242-4657a94c.jpeg"


sample_args = ZImageTurboImageToImageInput(
    acceleration=AccelerationEnum.REGULAR,
    enable_prompt_expansion=False,
    enable_safety_checker=False,
    image_size=ImageSizeEnum.PORTRAIT_16_9,
    image_url=reference_image_url,
    num_images=1,
    num_inference_steps=16,
    output_format=ImageFormat.JPEG,
    prompt=prompt,
    strength=0.75,
)


if __name__ == "__main__":
    result = asyncio.run(
        z_image_turbo_image_to_image(
            args=sample_args,
            gcs_uri_base="gs://inty-static/images",
            upload_to_gcs=False,
        )
    )
    print(reference_image_url)
    print(result.gcs_http_url)
