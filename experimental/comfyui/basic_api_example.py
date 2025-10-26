import json
import time
from urllib import request
from pathlib import Path
# 这是 ComfyUI api prompt 格式。
# 如果你想要它用于特定的工作流程，你可以“启用开发模式选项”
# 在 UI 的设置中（“排列大小：”旁边的齿轮）这将启用
# UI 上的一个按钮，用于以 api 格式保存工作流程。
# 请记住 ComfyUI 是 pre alpha 软件，此格式会发生变化。
#这是默认工作流程
# 从请求中读取。json 到 req_text
req_json = json.load(open("req.json"))


def queue_prompt(prompt):
    """Queue a prompt and return the prompt_id"""
    p = {"prompt": prompt}
# 如果工作流包含 API 节点，您可以将 Comfy API 热点添加到负载的 `extra_data` 字段中。
# p["extra_data"] = {
# "api_key_comfy_org": "comfyui-87d01e28d********************************************************************" # 替换为真实密钥
# }
# 请参阅：https://docs.comfy.org/tutorials/api-nodes/overview
#这里生成密钥：https://platform.comfy.org/login

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

    raise TimeoutError(f"Prompt {prompt_id} did not complete within {max_wait} seconds")


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
# 保存图片
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
