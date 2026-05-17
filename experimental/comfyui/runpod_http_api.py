#!/usr/bin/env python3
"""
RunPod API Client for ComfyUI

This script sends requests to RunPod's ComfyUI API endpoint
using the API key loaded from a .env file.
"""

import argparse
import os
import json
import time
import requests
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()
ENDPOINT_ID = "it8l4d88m9vek3"


class RunPodClient:
    def __init__(self, api_key: str, endpoint_id: str):
        """
        Initialize RunPod client

        Args:
            endpoint_id: The RunPod endpoint ID
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id

        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def run_sync(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Send a synchronous request to RunPod ComfyUI

        Args:
            prompt: The text prompt for image generation
            **kwargs: Additional parameters to pass to the API

        Returns:
            API response as dictionary
        """
        # This is the format used by the runpod endpoint.
        # If prompt is a single string, it's meant for a normal text2image model.
        # If prompt is a workflow, it's meant for comfyui workflows.
        # TODO: Need to further verify runpod comfyui workflows.
        # https://www.runpod.io/articles/guides/comfy-ui-flux
        # https://github.com/runpod-workers/worker-comfyui/tree/main
        payload = {"input": {"prompt": prompt, **kwargs}}

        try:
            response = requests.post(
                f"{self.base_url}/runsync",
                headers=self.headers,
                json=payload,
                timeout=300,  # 5 minutes timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return {"error": str(e)}

    def run_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Send an asynchronous request to RunPod ComfyUI

        Args:
            prompt: The text prompt for image generation
            **kwargs: Additional parameters to pass to the API

        Returns:
            API response with job ID
        """
        payload = {"input": {"prompt": prompt, **kwargs}}

        try:
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return {"error": str(e)}

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of an asynchronous job

        Args:
            job_id: The job ID returned from run_async

        Returns:
            Job status and results
        """
        try:
            response = requests.get(
                f"{self.base_url}/status/{job_id}",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error getting status: {e}")
            return {"error": str(e)}


def parse_args():
    parser = argparse.ArgumentParser(
        description="RunPod API Client for ComfyUI"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        required=True,
        help="The endpoint ID to send to the API",
    )
    return parser.parse_args()


def main():
    """Example usage of the RunPod client"""

    args = parse_args()
    try:
        client = RunPodClient(
            api_key=os.getenv("RUNPOD_API_KEY"), endpoint_id=args.endpoint
        )
        print("RunPod client initialized successfully")
    except ValueError as e:
        print(f"Error: {e}")
        print("Please make sure RUNPOD_API_KEY is set in your .env file")
        return

    # Example prompt
    prompt = "masterpiece best quality girl, beautiful, detailed"

    print(f"Sending prompt: {prompt}")

    now = time.time()
    # Send synchronous request (equivalent to the curl command)
    print("\n1. Sending synchronous request...")
    result = client.run_sync(prompt)
    print(f"Time taken: {time.time() - now}")

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print("Response received:")

    with open("response.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
