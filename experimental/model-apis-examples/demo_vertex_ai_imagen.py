import random
import typing

from PIL import Image as PIL_Image
from PIL import ImageOps as PIL_ImageOps

from openai import BaseModel
from pydantic import Field
from vertexai.preview.vision_models import ImageGenerationModel
import vertexai


# See https://developers.googleblog.com/en/experiment-with-gemini-20-flash-native-image-generation/
# https://ai.google.dev/gemini-api/docs/image-generation claims 'gemini-2.0-flash-preview-image-generation'
# which is wrong.
# Turns out that gemini image generation is only available with genai api endpoint.
# Note on the vertex ai api.
GEMINI_MODEL = "gemini-2.0-flash-exp"
IMAGEN_MODEL = "imagen-4.0-generate-preview-06-06"


def display_image(
    image,
    max_width: int = 600,
    max_height: int = 350,
) -> None:
    pil_image = typing.cast(PIL_Image.Image, image._pil_image)
    if pil_image.mode != "RGB":
        # RGB is supported by all Jupyter environments (e.g. RGBA is not yet)
        pil_image = pil_image.convert("RGB")
    image_width, image_height = pil_image.size
    if max_width < image_width or max_height < image_height:
        # Resize to display a smaller notebook image
        pil_image = PIL_ImageOps.contain(pil_image, (max_width, max_height))
    pil_image.show()


vertexai.init(project="cosmic-gizmo-424300-t1", location="us-central1")

generation_model = ImageGenerationModel.from_pretrained(
    # This is by far the best model for this task, all other models are not good.
    # IMAGEN_MODEL
    GEMINI_MODEL
)

GENDERS = ["female", "male"]
AGE_RANGE = [22, 35]
HAIR_COLORS = ["blonde", "brown", "black", "red", "gray", "white"]
EYE_COLORS = ["blue", "green", "brown", "gray", "hazel"]
FACE_SHAPES = ["oval", "round", "square", "heart", "triangle"]
SKIN_TONES = ["white", "brown", "black", "yellow", "red"]
# STYLES = ["realistic", "cartoon", "anime", "digital art", "watercolor", "oil painting"]
STYLES = ["realistic"]


class Appearance(BaseModel):
    gender: str = Field(description="The gender of the person")
    age: int = Field(description="The age of the person")
    hair_color: str = Field(description="The hair color of the person")
    eye_color: str = Field(description="The eye color of the person")
    face_shape: str = Field(description="The face shape of the person")
    skin_tone: str = Field(description="The skin tone of the person")


def get_random_appearance(gender: str) -> Appearance:
    return Appearance(
        gender=gender,
        age=random.randint(AGE_RANGE[0], AGE_RANGE[1]),
        hair_color=random.choice(HAIR_COLORS),
        eye_color=random.choice(EYE_COLORS),
        face_shape=random.choice(FACE_SHAPES),
        skin_tone=random.choice(SKIN_TONES),
    )


def get_generation_prompt(
    appearance: Appearance, additional_descriptions: str, style: str
) -> str:
    prompt = """Generate pictures of a person in varying backgrounds

The person's information
{appearance}

Additional descriptions of this person:
{additional_descriptions}

The backgrounds choice:
Be creative
Be generally safe and agreeable

Style: {style}
"""
    return prompt.format(
        appearance=str(appearance),
        additional_descriptions=additional_descriptions,
        style=style,
    )


appearance = get_random_appearance("female")
additional_descriptions = "beautiful"
style = random.choice(STYLES)
prompt = get_generation_prompt(appearance, additional_descriptions, style)
num_of_images = 1


print("Prompt: ", prompt)

images = generation_model.generate_images(
    prompt=prompt,
    number_of_images=num_of_images,
    aspect_ratio="9:16",
    negative_prompt="",
    guidance_scale=10,
    person_generation="allow_adult",
    safety_filter_level="block_few",
    add_watermark=True,
)

for image in images:
    display_image(image)
