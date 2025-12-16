"""
fal.ai Z-Image Turbo 客户端封装
CREATED_BY_AGENT
"""

from dataclasses import dataclass
from typing import Literal, Optional

import fal_client
from config import FAL_MODEL_ID, set_api_key

ImageSize = Literal[
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
]
OutputFormat = Literal["jpeg", "png", "webp"]
AccelerationLevel = Literal["none", "regular", "high"]


@dataclass
class GeneratedImage:
    """生成的图像信息"""

    url: str
    width: int
    height: int
    content_type: str


@dataclass
class GenerationResult:
    """图像生成结果"""

    images: list[GeneratedImage]
    seed: int
    prompt: str
    has_nsfw_concepts: list[bool]


class ZImageTurboClient:
    """fal.ai Z-Image Turbo 客户端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端

        Args:
            api_key: fal.ai API Key，如果不提供则使用环境变量 FAL_KEY
        """
        if api_key:
            set_api_key(api_key)

    def generate(
        self,
        prompt: str,
        image_size: ImageSize = "landscape_4_3",
        num_inference_steps: int = 8,
        seed: Optional[int] = None,
        num_images: int = 1,
        enable_safety_checker: bool = True,
        enable_prompt_expansion: bool = False,
        output_format: OutputFormat = "png",
        acceleration: AccelerationLevel = "none",
    ) -> GenerationResult:
        """
        生成图像

        Args:
            prompt: 生成图像的文本提示
            image_size: 图像尺寸
            num_inference_steps: 推理步数，默认 8
            seed: 随机种子，相同种子和提示会生成相同图像
            num_images: 生成图像数量，默认 1
            enable_safety_checker: 是否启用安全检查，默认 True
            enable_prompt_expansion: 是否启用提示扩展，默认 False
            output_format: 输出格式，默认 png
            acceleration: 加速级别，默认 none

        Returns:
            GenerationResult: 包含生成图像信息的结果
        """
        input_params = {
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": num_inference_steps,
            "num_images": num_images,
            "enable_safety_checker": enable_safety_checker,
            "enable_prompt_expansion": enable_prompt_expansion,
            "output_format": output_format,
            "acceleration": acceleration,
        }

        if seed is not None:
            input_params["seed"] = seed

        result = fal_client.subscribe(
            FAL_MODEL_ID,
            arguments=input_params,
            with_logs=True,
            on_queue_update=self._on_queue_update,
        )

        return self._parse_result(result)

    def _on_queue_update(self, update) -> None:
        """处理队列更新回调"""
        # fal_client 使用类型化事件对象，检查类名
        update_type = type(update).__name__
        if update_type == "InProgress" and hasattr(update, "logs"):
            for log in update.logs:
                print(
                    f"[进度] {log.get('message', log) if isinstance(log, dict) else log}"
                )

    def _parse_result(self, result: dict) -> GenerationResult:
        """解析 API 返回结果"""
        images = [
            GeneratedImage(
                url=img["url"],
                width=img.get("width", 0),
                height=img.get("height", 0),
                content_type=img.get("content_type", "image/png"),
            )
            for img in result.get("images", [])
        ]

        return GenerationResult(
            images=images,
            seed=result.get("seed", 0),
            prompt=result.get("prompt", ""),
            has_nsfw_concepts=result.get("has_nsfw_concepts", []),
        )
