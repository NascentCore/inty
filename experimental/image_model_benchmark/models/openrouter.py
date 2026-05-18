# CREATED_BY_AGENT
"""
OpenRouter API 实现 - 支持 Seedream 4.5 和 Flux.2 Pro
"""

import base64
import json
import re
import time
from typing import Any, Optional

import httpx

from .base import ImageGenerationResult, ImageModel


class OpenRouterModel(ImageModel):
    """基于 OpenRouter API 的图像生成模型"""

    def __init__(
        self,
        name: str,
        model_id: str,
        display_name: str,
        api_key: str,
    ):
        super().__init__(name, model_id, display_name)
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"

    def _encode_image_to_base64(self, image_data: bytes) -> str:
        """将图片数据编码为 base64 data URL"""
        b64_str = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_str}"

    def _extract_image_from_content(self, content: Any) -> Optional[bytes]:
        """从响应内容中提取图片数据"""
        # 如果 content 是字符串，尝试解析 base64
        if isinstance(content, str):
            # 尝试匹配 data URL 格式
            pattern = r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)"
            match = re.search(pattern, content)
            if match:
                return base64.b64decode(match.group(1))

            # 尝试直接作为 base64 解码
            try:
                if len(content) > 100 and all(
                    c
                    in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
                    for c in content[:100]
                ):
                    return base64.b64decode(content)
            except Exception:
                pass

        # 如果 content 是列表（multimodal response）
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    # 检查 image_url 格式
                    if item.get("type") == "image_url":
                        url = item.get("image_url", {}).get("url", "")
                        if url.startswith("data:image"):
                            match = re.search(r"base64,([A-Za-z0-9+/=]+)", url)
                            if match:
                                return base64.b64decode(match.group(1))
                    # 检查 image 格式
                    if item.get("type") == "image":
                        b64_data = item.get("data") or item.get("base64")
                        if b64_data:
                            return base64.b64decode(b64_data)

        return None

    async def generate(
        self,
        prompt: str,
        reference_images: Optional[list[bytes]] = None,
    ) -> ImageGenerationResult:
        """
        使用 OpenRouter API 生成图片

        Args:
            prompt: 生成提示词
            reference_images: 参考图片列表

        Returns:
            ImageGenerationResult: 生成结果
        """
        start_time = time.perf_counter()
        first_response_time: Optional[float] = None

        try:
            # 构建消息内容
            content_parts: list[dict] = []

            # 添加参考图片
            if reference_images:
                for img_data in reference_images:
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._encode_image_to_base64(img_data),
                            },
                        }
                    )

            # 添加文本提示
            content_parts.append(
                {
                    "type": "text",
                    "text": prompt,
                }
            )

            # 使用 httpx 直接调用 API 以获取完整响应
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/inty-backend",
            }

            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": content_parts,
                    }
                ],
                "modalities": ["image", "text"],
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
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

            # 提取响应内容
            if not result.get("choices"):
                raise ValueError(
                    f"API 未返回任何结果: {json.dumps(result, ensure_ascii=False)[:300]}"
                )

            message = result["choices"][0].get("message", {})

            # 首先尝试从 message.images 字段获取图片（OpenRouter 图像生成模型的响应格式）
            image_data: Optional[bytes] = None
            images = message.get("images", [])
            if images:
                for img in images:
                    if isinstance(img, dict):
                        img_url = img.get("image_url", {}).get("url", "")
                        if img_url.startswith("data:image"):
                            match = re.search(
                                r"base64,([A-Za-z0-9+/=]+)", img_url
                            )
                            if match:
                                image_data = base64.b64decode(match.group(1))
                                break

            # 如果 images 字段没有，尝试从 content 获取
            if not image_data:
                content = message.get("content")
                if content:
                    image_data = self._extract_image_from_content(content)

            if not image_data:
                raise ValueError(
                    f"无法从响应中提取图片数据，响应结构: {json.dumps(message, ensure_ascii=False)[:500]}"
                )

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


class SeedreamModel(OpenRouterModel):
    """Seedream 4.5 模型"""

    def __init__(self, api_key: str):
        super().__init__(
            name="seedream",
            model_id="bytedance-seed/seedream-4.5",
            display_name="Seedream 4.5",
            api_key=api_key,
        )


class FluxModel(OpenRouterModel):
    """Flux.2 Pro 模型"""

    def __init__(self, api_key: str):
        super().__init__(
            name="flux",
            model_id="black-forest-labs/flux.2-pro",
            display_name="Flux.2 Pro",
            api_key=api_key,
        )
