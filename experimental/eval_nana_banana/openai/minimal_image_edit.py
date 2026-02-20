import base64
from openai import OpenAI
client = OpenAI()

prompt = """
A man and a woman sit in a movie theater, watching a movie.
"""

result = client.images.edit(
    model="gpt-image-1.5",
    image=[
        open("tests/files/nurse_char.jpg", "rb"),
        open("tests/files/zunlong.jpg", "rb"),
    ],
    prompt=prompt
)

image_base64 = result.data[0].b64_json
image_bytes = base64.b64decode(image_base64)

# Save the image to a file
with open("tmp/openai/gpt-image-1.5/scene_prompt_00001.png", "wb") as f:
    f.write(image_bytes)
