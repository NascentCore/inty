#!/usr/bin/env python3
"""
Minimal example of using RunPod SDK to call runsync on a serverless ComfyUI worker endpoint
"""

import argparse
import base64
from datetime import datetime
import os
import json
import random
import time
import runpod

from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="RunPod ComfyUI Serverless Endpoint Example"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        required=True,
        help="The endpoint ID to send to the API",
    )
    parser.add_argument(
        "--workflow", type=str, required=True, help="The workflow file to use"
    )
    return parser.parse_args()


runpod.api_key = os.getenv("RUNPOD_API_KEY")

args = parse_args()
endpoint = runpod.Endpoint(args.endpoint)


workflow_json = json.load(open(args.workflow))
req_json = {"input": {"workflow": workflow_json}}


def save_images(image_base64_data: str):
    rand_int = random.randint(0, 1000000)
    out_path = (
        f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rand_int}.png"
    )
    image_data = base64.b64decode(image_base64_data)
    with open(out_path, "wb") as f:
        f.write(image_data)
    print(f"Saved: {out_path}")


def run_sync(req_json):
    result = endpoint.run_sync(req_json)
    images = result["images"]
    print(images)
    for image in images:
        save_images(image["data"])


def run_async(req_json):
    result1, result2 = endpoint.run(req_json), endpoint.run(req_json)
    print(result1.status())
    print(result2.status())

    output1 = result1.output(timeout=100)
    for image in output1["images"]:
        save_images(image["data"])

    output2 = result2.output(timeout=100)
    for image in output2["images"]:
        save_images(image["data"])


def main():
    start_time = time.time()
    run_sync(req_json)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")


if __name__ == "__main__":
    main()
