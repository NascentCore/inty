"""
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
#问亚雄找API键
export GETIMG_API_KEY="your-getimg-api-key"
python getimg_request.py
#会打开preview图片预览

Based on https://docs.getimg.ai/reference/poststablediffusionxltexttoimage
"""
import os
import requests
from PIL import Image
from io import BytesIO
import base64

ENV_VAR_NAME = "GETIMG_API_KEY"

url = "https://api.getimg.ai/v1/stable-diffusion-xl/text-to-image"
headers = {
    "accept": "application/json",
    "authorization": f"Bearer {os.getenv(ENV_VAR_NAME)}",
    "content-type": "application/json"
}
data = {
    "prompt": "A beautiful sunset over mountains, movie poster art, high quality",
    "negative_prompt": "blurry, low quality, distorted, superficial, ugly, bad",
    "width": 512,
    "height": 512,
    "steps": 30,
    "guidance": 7.5,
    "seed": 42,
    "output_format": "png"
}

response = requests.post(url, headers=headers, json=data)
image_base64_data = response.json()['image']
img = Image.open(BytesIO(base64.b64decode(image_base64_data)))
img.show()
