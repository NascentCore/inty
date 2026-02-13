"""
最小 Gemini Image-to-Video 示例（Veo）。

运行前请设置：
1) GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
2) GOOGLE_CLOUD_PROJECT=your-gcp-project-id
3) （可选）GOOGLE_CLOUD_LOCATION=us-central1

示例仅用于展示 Gemini Image-to-Video 的最小接口调用，不包含生产级错误处理。
"""

import os
import time

from google import genai
from google.genai import types


# AI 工作总结（关键中间步骤）：
# 1) 先在仓库中定位现有 Veo 调用路径：app/services/video_generation_service.py
# 2) 从生产实现中提炼最小必需参数：model + source(prompt/image) + config(duration/output_gcs_uri)
# 3) 保留官方 SDK 典型异步轮询方式：generate_videos -> operations.get -> 读取 generated_videos[0].video.uri

MODEL = "veo-3.0-fast-generate-preview"
PROMPT = "A cinematic slow push-in, gentle wind, natural motion."
IMAGE_GCS_URI = "gs://your-bucket/input.jpg"
OUTPUT_GCS_URI = "gs://your-bucket/generated-video/demo"


def main() -> None:
    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    client = genai.Client(vertexai=True, project=project_id, location=location)

    source = types.GenerateVideosSource(
        prompt=PROMPT,
        image=types.Image(gcs_uri=IMAGE_GCS_URI, mime_type="image/jpeg"),
    )

    config = types.GenerateVideosConfig(
        duration_seconds=4,
        output_gcs_uri=OUTPUT_GCS_URI,
    )

    operation = client.models.generate_videos(
        model=MODEL,
        source=source,
        config=config,
    )

    while not operation.done:
        print("Waiting for video generation...")
        time.sleep(10)
        operation = client.operations.get(operation)

    video_uri = operation.response.generated_videos[0].video.uri
    print(f"Generated video URI: {video_uri}")


if __name__ == "__main__":
    main()
