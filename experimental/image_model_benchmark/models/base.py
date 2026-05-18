# CREATED_BY_AGENT
"""
图像生成模型的抽象基类和结果数据类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ImageGenerationResult:
    """图像生成结果"""

    # 是否成功
    success: bool

    # 计时信息（毫秒）
    total_time_ms: float
    first_response_time_ms: Optional[float] = None

    # 图像数据
    image_data: Optional[bytes] = None
    image_format: str = "jpeg"

    # 元信息
    model_name: str = ""
    prompt: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 错误信息
    error_message: Optional[str] = None

    @property
    def image_size_kb(self) -> float:
        """图像大小（KB）"""
        if self.image_data:
            return len(self.image_data) / 1024
        return 0.0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "total_time_ms": self.total_time_ms,
            "first_response_time_ms": self.first_response_time_ms,
            "image_size_kb": self.image_size_kb,
            "image_format": self.image_format,
            "model_name": self.model_name,
            "prompt": self.prompt,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
        }


class ImageModel(ABC):
    """图像生成模型的抽象基类"""

    def __init__(self, name: str, model_id: str, display_name: str):
        self.name = name
        self.model_id = model_id
        self.display_name = display_name

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        reference_images: Optional[list[bytes]] = None,
    ) -> ImageGenerationResult:
        """
        生成图片

        Args:
            prompt: 生成提示词
            reference_images: 参考图片列表（字节数据）

        Returns:
            ImageGenerationResult: 生成结果
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model_id={self.model_id!r})"
