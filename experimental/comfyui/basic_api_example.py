import json
import time
from urllib import request
from pathlib import Path

# This is the ComfyUI api prompt format.

# If you want it for a specific workflow you can "enable dev mode options"
# in the settings of the UI (gear beside the "Queue Size: ") this will enable
# a button on the UI to save workflows in api format.

# keep in mind ComfyUI is pre alpha software so this format will change a bit.

# this is the one for the default workflow
# Read from req.json to req_text
req_json = json.load(open("req.json"))


def queue_prompt(prompt):
    """Queue a prompt and return the prompt_id"""
    p = {"prompt": prompt}

    # If the workflow contains API nodes, you can add a Comfy API key to the `extra_data`` field of the payload.
    # p["extra_data"] = {
    #     "api_key_comfy_org": "comfyui-87d01e28d*******************************************************"  # replace with real key
    # }
    # See: https://docs.comfy.org/tutorials/api-nodes/overview
    # Generate a key here: https://platform.comfy.org/login

    data = json.dumps(p).encode("utf-8")
    print("Sending data: ", data)
    req = request.Request("http://127.0.0.1:8188/prompt", data=data)
    response = request.urlopen(req)
    return json.loads(response.read())


def get_history(prompt_id):
    """Get the history for a specific prompt_id"""
    req = request.Request(f"http://127.0.0.1:8188/history/{prompt_id}")
    response = request.urlopen(req)
    return json.loads(response.read())


def get_image(filename):
    """Download an image by filename"""
    req = request.Request(f"http://127.0.0.1:8188/view?filename={filename}")
    response = request.urlopen(req)
    print("response: ", response.read())
    return response.read()


def wait_for_completion(prompt_id, max_wait=60):
    """Wait for a prompt to complete and return the results"""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            history = get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(1)
        except Exception as e:
            print(f"Error checking history: {e}")
            time.sleep(1)

    raise TimeoutError(
        f"Prompt {prompt_id} did not complete within {max_wait} seconds"
    )


def save_images_from_history(history_data, output_dir="output"):
    """Save images from history data to local files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    saved_files = []

    if "outputs" in history_data:
        for node_id, node_output in history_data["outputs"].items():
            print("node_output: ", node_output)
            print("node_id: ", node_id)
            if "images" in node_output:
                for image_data in node_output["images"]:
                    print("image_data: ", image_data)
                    filename = image_data["filename"]
                    image_bytes = get_image(filename)

                    # Save the image
                    file_path = output_path / filename
                    with open(file_path, "wb") as f:
                        f.write(image_bytes)

                    saved_files.append(str(file_path))
                    print(f"Saved image: {file_path}")

    return saved_files


def main():
    """Main function to demonstrate the complete workflow"""
    print("Queueing prompt...")
    result = queue_prompt(req_json)
    prompt_id = result["prompt_id"]
    print(f"Prompt queued with ID: {prompt_id}")

    print("Waiting for completion...")
    history_data = wait_for_completion(prompt_id)
    print("Prompt completed!")

    print("Saving images...")
    saved_files = save_images_from_history(history_data)
    print(f"Saved {len(saved_files)} images")

    return saved_files


if __name__ == "__main__":
    main()
