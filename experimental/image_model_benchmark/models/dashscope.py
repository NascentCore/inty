# CREATED_BY_AGENT
"""
阿里云 DashScope API 实现 - 支持 Qwen Image Edit 系列模型
"""

import base64
import time
from typing import Optional

import httpx

from .base import ImageGenerationResult, ImageModel


class DashScopeModel(ImageModel):
    """基于阿里云 DashScope API 的图像编辑模型"""

    API_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

    def __init__(
        self,
        name: str,
        model_id: str,
        display_name: str,
        api_key: str,
    ):
        super().__init__(name, model_id, display_name)
        self.api_key = api_key

    def _encode_image_to_data_url(self, image_data: bytes) -> str:
        """将图片数据编码为 Base64 data URL"""
        b64_str = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_str}"

    async def _download_image(self, url: str) -> bytes:
        """从 URL 下载图片数据"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def generate(
        self,
        prompt: str,
        reference_images: Optional[list[bytes]] = None,
    ) -> ImageGenerationResult:
        """
        使用 DashScope API 生成/编辑图片

        Args:
            prompt: 编辑提示词
            reference_images: 参考图片列表（字节数据）

        Returns:
            ImageGenerationResult: 生成结果
        """
        start_time = time.perf_counter()
        first_response_time: Optional[float] = None

        try:
            # 构建消息内容
            content: list[dict] = []

            # 添加参考图片
            if reference_images:
                for img_data in reference_images:
                    content.append(
                        {"image": self._encode_image_to_data_url(img_data)}
                    )

            # 添加文本提示
            content.append({"text": prompt})

            # 构建请求体
            payload = {
                "model": self.model_id,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": content,
                        }
                    ]
                },
                "parameters": {
                    "n": 1,
                    "watermark": False,
                    "prompt_extend": True,
                },
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # 调用 API
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/services/aigc/multimodal-generation/generation",
                    headers=headers,
                    json=payload,
                )

            first_response_time = (time.perf_counter() - start_time) * 1000

            if response.status_code != 200:
                error_text = response.text[:500]
                raise ValueError(
                    f"API 错误 ({response.status_code}): {error_text}"
                )

            result = response.json()

            # 检查响应结构
            output = result.get("output", {})
            choices = output.get("choices", [])

            if not choices:
                raise ValueError(f"API 未返回任何结果: {result}")

            # 提取图片 URL
            message = choices[0].get("message", {})
            content_list = message.get("content", [])

            image_url: Optional[str] = None
            for item in content_list:
                if isinstance(item, dict) and "image" in item:
                    image_url = item["image"]
                    break

            if not image_url:
                raise ValueError(f"响应中没有找到图片 URL: {message}")

            # 下载图片
            image_data = await self._download_image(image_url)

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


class QwenImageEditModel(DashScopeModel):
    """Qwen Image Edit Max 模型"""

    def __init__(self, api_key: str):
        super().__init__(
            name="qwen-image-edit",
            model_id="qwen-image-edit-max",
            display_name="Qwen Image Edit Max",
            api_key=api_key,
        )
