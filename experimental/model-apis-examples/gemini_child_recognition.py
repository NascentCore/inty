import argparse
import enum
import io
import os
import time
from google.genai import types
from google import genai
from PIL import Image


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-path", type=str, required=True)
    return parser.parse_args()


args = parse_args()


def detect_child_in_image_file(image_path):
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    return detect_child_in_image(image_bytes)


def detect_child_in_image(image_bytes):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    class YesOrNo(enum.Enum):
        YES = "Yes"
        NO = "No"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg",
            ),
            "Does this image contain a child?",
        ],
        config={
            "response_mime_type": "text/x.enum",
            "response_schema": YesOrNo,
        },
    )

    return response


def resize_to_512_if_needed(image_path):
    """
    Resize image to fit within 512x512 square while maintaining aspect ratio.

    Args:
        image_path (str): Path to input image

    Returns:
        PIL.Image: Resized image
    """
    # Open the image
    with Image.open(image_path) as img:
        # Get original dimensions
        width, height = img.size

        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        if width <= 512 and height <= 512:
            # Create a copy to avoid file handle issues
            return img.copy()

        # Calculate scaling factor to fit within 512x512
        scale = 512 / max(width, height)

        # Calculate new dimensions
        new_width = int(width * scale)
        new_height = int(height * scale)

        # Resize the image
        resized_img = img.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )
        return resized_img.copy()


# Example usage:
if __name__ == "__main__":
    # Show the input image
    input_img = Image.open(args.image_path)
    input_img.show()

    resized_img = resize_to_512_if_needed(args.image_path)
    # Display the resized image
    resized_img.show()

    bytesio = io.BytesIO()
    resized_img.save(bytesio, format="JPEG")
    bytesio.seek(0)
    resized_img_bytes = bytesio.getvalue()

    time_start = time.time()
    response = detect_child_in_image(resized_img_bytes)
    time_end = time.time()
    print(f"Time taken: {time_end - time_start} seconds")
    print(response)
