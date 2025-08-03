#!/usr/bin/env python3
"""
Minimal example of using RunPod SDK to call runsync on a serverless ComfyUI worker endpoint
"""

import argparse
import base64
import os
import json
import re
import runpod

from dotenv import load_dotenv


load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="RunPod ComfyUI Serverless Endpoint Example"
    )
    parser.add_argument(
        "--endpoint", type=str, required=True, help="The endpoint ID to send to the API"
    )
    return parser.parse_args()


runpod.api_key = os.getenv("RUNPOD_API_KEY")

args = parse_args()
endpoint = runpod.Endpoint(args.endpoint)


print("pwd: ", os.getcwd())
req_json = json.load(open("runpod_serverless_comfyui_sd3_workflow.json"))


result = endpoint.run_sync(req_json)

# Extract images from the images field
images = result["images"]

# Save each image as PNG
for idx, image in enumerate(images):
    out_path = f"image_{idx+1:03d}.png"
    image_data = base64.b64decode(image["data"])
    with open(out_path, "wb") as f:
        f.write(image_data)
    print(f"Saved: {out_path}")

# json.dump(result, open("result.json", "w"), indent=2)

print(f"Saved {len(images)} images to {os.path.abspath(out_path)}")
