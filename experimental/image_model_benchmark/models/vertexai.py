# CREATED_BY_AGENT
"""
Google Vertex AI 实现 - 支持 Gemini 2.5 Flash Image 和 Nano Banana Pro
"""

import io
import json
import os
import time
from typing import Optional

import google.genai as genai
from google.genai import types

from .base import ImageGenerationResult, ImageModel


def _get_genai_client(
    credentials_path: str,
    project_id: str,
    location: str = "us-central1",
) -> genai.Client:
    """获取 Google GenAI 客户端"""
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    # 尝试从凭证文件获取 project_id
    if not project_id and os.path.exists(credentials_path):
        with open(credentials_path, "r") as f:
            creds = json.load(f)
            project_id = creds.get("project_id", "")

    return genai.Client(vertexai=True, project=project_id, location=location)


class VertexAIModel(ImageModel):
    """基于 Google Vertex AI 的图像生成模型"""

    def __init__(
        self,
        name: str,
        model_id: str,
        display_name: str,
        credentials_path: str,
        project_id: str,
        location: str = "us-central1",
    ):
        super().__init__(name, model_id, display_name)
        self.client = _get_genai_client(credentials_path, project_id, location)

    async def generate(
        self,
        prompt: str,
        reference_images: Optional[list[bytes]] = None,
    ) -> ImageGenerationResult:
        """
        使用 Vertex AI 生成图片

        Args:
            prompt: 生成提示词
            reference_images: 参考图片列表

        Returns:
            ImageGenerationResult: 生成结果
        """
        start_time = time.perf_counter()
        first_response_time: Optional[float] = None

        try:
            # 构建内容部分
            parts: list[types.Part] = []

            # 添加参考图片
            if reference_images:
                for img_data in reference_images:
                    parts.append(
                        types.Part.from_bytes(
                            data=img_data,
                            mime_type="image/jpeg",
                        )
                    )

            # 添加文本提示
            parts.append(types.Part.from_text(text=prompt))

            contents = [
                types.Content(
                    role="user",
                    parts=parts,
                )
            ]

            # 配置生成参数
            generate_config = types.GenerateContentConfig(
                temperature=1.0,
                top_p=0.95,
                max_output_tokens=8192,
                response_modalities=["IMAGE"],
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                ],
            )

            # 调用 API（同步调用，因为 google.genai 不支持原生异步）
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=generate_config,
            )

            first_response_time = (time.perf_counter() - start_time) * 1000

            # 检查响应
            if (
                hasattr(response, "prompt_feedback")
                and response.prompt_feedback
            ):
                if hasattr(response.prompt_feedback, "block_reason"):
                    raise ValueError(
                        f"请求被安全过滤器阻止: {response.prompt_feedback.block_reason}"
                    )

            if not response.candidates:
                raise ValueError("API 未返回任何候选结果")

            candidate = response.candidates[0]

            # 检查完成原因
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason == "SAFETY":
                raise ValueError("图片生成被安全过滤器阻止")

            if not candidate.content or not candidate.content.parts:
                raise ValueError("候选结果中没有内容")

            # 提取图片数据
            image_data: Optional[bytes] = None
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    raw_data = part.inline_data.data
                    if isinstance(raw_data, str):
                        import base64

                        image_data = base64.b64decode(raw_data)
                    elif isinstance(raw_data, bytes):
                        image_data = raw_data
                    break

            if not image_data:
                raise ValueError("响应中没有找到图片数据")

            total_time = (time.perf_counter() - start_time) * 1000

            return ImageGenerationResult(
                success=True,
                total_time_ms=total_time,
                first_response_time_ms=first_response_time,
                image_data=image_data,
                image_format="jpeg",
                model_name=self.display_name,
                prompt=prompt,
            )

        except Exception as e:
            total_time = (time.perf_counter() - start_time) * 1000
            return ImageGenerationResult(
                success=False,
                total_time_ms=total_time,
                first_response_time_ms=first_response_time,
                model_name=self.display_name,
                prompt=prompt,
                error_message=str(e),
            )


class GeminiFlashImageModel(VertexAIModel):
    """Gemini 2.5 Flash Image 模型"""

    def __init__(
        self,
        credentials_path: str,
        project_id: str,
        location: str = "us-central1",
    ):
        super().__init__(
            name="gemini-flash",
            model_id="gemini-2.5-flash-image",
            display_name="Gemini 2.5 Flash Image",
            credentials_path=credentials_path,
            project_id=project_id,
            location=location,
        )


class NanoBananaProModel(VertexAIModel):
    """Nano Banana Pro - 使用 Gemini 2.0 Flash Experimental 作为替代"""

    def __init__(
        self,
        credentials_path: str,
        project_id: str,
        location: str = "us-central1",
    ):
        super().__init__(
            name="nano-banana",
            model_id="gemini-2.0-flash-exp",
            display_name="Nano Banana Pro",
            credentials_path=credentials_path,
            project_id=project_id,
            location=location,
        )
