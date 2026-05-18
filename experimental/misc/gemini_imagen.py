"""
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Set your Google API key
export GEMINI_API_KEY="your-google-api-key"
python gemini_imagen.py
# Will open preview image

Based on https://ai.google.dev/docs/imagen_api
"""

import os
import random
import string
import requests
from PIL import Image
from io import BytesIO
import base64

ENV_VAR_NAME = "GEMINI_API_KEY"

url = "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-preview-06-06:predict"
headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": os.getenv(ENV_VAR_NAME),
}
data = {
    "instances": [
        {
            "prompt": "A mid-day sunshine lakeside workplace, movie poster art, high quality",
            "negativePrompt": "low quality, blurry, pixelated, distorted, deformed, ugly, bad, poor, low quality, low resolution, low contrast, low saturation, low brightness, low contrast, low saturation, low brightness, low contrast, low saturation, low brightness",
            "language": "en",
        },
    ],
    "parameters": {
        "sampleCount": 1,
        "imageQuality": "standard",
        "aspectRatio": "9:16",
        "outputOptions": {
            "mimeType": "image/jpeg",
            "compressionQuality": 70,
        },
    },
}

compression_quality_options = [20, 30, 50, 70, 90]

for compression_quality in compression_quality_options:
    data["parameters"]["outputOptions"][
        "compressionQuality"
    ] = compression_quality
    response = requests.post(url, headers=headers, json=data)
    response_data = response.json()

    # print(response_data)
    # Extract image data from response
    for prediction in response_data["predictions"]:
        image_base64_data = prediction["bytesBase64Encoded"]
        img = Image.open(BytesIO(base64.b64decode(image_base64_data)))
        img.show()
        # img.save(f"image_{prediction['id']}.png")
        rand_str = "".join(
            random.choices(string.ascii_letters + string.digits, k=5)
        )
        filename = f"image_{rand_str}.jpeg"
        img.save(filename)
        print(
            f"Saved image to {filename}, compression quality: {compression_quality}, size: {img.size}, size kb: {os.path.getsize(filename)/1024}"
        )
