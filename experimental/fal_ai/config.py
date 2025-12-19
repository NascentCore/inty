"""
fal.ai API 配置管理
CREATED_BY_AGENT
"""

import os
from typing import Optional

FAL_MODEL_ID = "fal-ai/z-image/turbo"

# 图像尺寸选项
IMAGE_SIZES = [
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
]

# 输出格式选项
OUTPUT_FORMATS = ["jpeg", "png", "webp"]

# 加速级别选项
ACCELERATION_LEVELS = ["none", "regular", "high"]


def get_api_key() -> Optional[str]:
    """
    获取 fal.ai API Key
    优先级：环境变量 FAL_KEY > 硬编码默认值
    """
    return os.environ.get("FAL_KEY")


def set_api_key(api_key: str) -> None:
    """设置 fal.ai API Key 到环境变量"""
    os.environ["FAL_KEY"] = api_key
