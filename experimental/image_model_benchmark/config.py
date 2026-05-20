# CREATED_BY_AGENT
"""
配置管理模块
"""

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ModelProvider(StrEnum):
    OPENROUTER = "openrouter"
    VERTEXAI = "vertexai"
    DASHSCOPE = "dashscope"


@dataclass
class ModelConfig:
    """单个模型的配置"""

    name: str
    model_id: str
    provider: ModelProvider
    display_name: str
    notes: str = ""


# 支持的模型列表
MODELS: dict[str, ModelConfig] = {
    "seedream": ModelConfig(
        name="seedream",
        model_id="bytedance-seed/seedream-4.5",
        provider=ModelProvider.OPENROUTER,
        display_name="Seedream 4.5",
        notes="OpenRouter 图像生成，需确认模型支持 image modality",
    ),
    "gemini-flash": ModelConfig(
        name="gemini-flash",
        model_id="gemini-2.5-flash-image",
        provider=ModelProvider.VERTEXAI,
        display_name="Gemini 2.5 Flash Image",
    ),
    "nano-banana": ModelConfig(
        name="nano-banana",
        model_id="gemini-2.0-flash-exp",
        provider=ModelProvider.VERTEXAI,
        display_name="Nano Banana Pro",
        notes="使用 gemini-2.0-flash-exp 作为替代，gemini-3-pro-image-preview 可能未开放",
    ),
    "flux": ModelConfig(
        name="flux",
        model_id="black-forest-labs/flux-pro-1.1",
        provider=ModelProvider.OPENROUTER,
        display_name="Flux.2 Pro",
        notes="OpenRouter 图像生成",
    ),
    "qwen-image-edit": ModelConfig(
        name="qwen-image-edit",
        model_id="qwen-image-edit-max",
        provider=ModelProvider.DASHSCOPE,
        display_name="Qwen Image Edit Max",
        notes="阿里云百炼图像编辑模型",
    ),
}


@dataclass
class BenchmarkConfig:
    """评测配置"""

    # API Keys
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "")
    )
    gcp_credentials_path: str = field(
        default_factory=lambda: os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        )
    )
    gcp_project_id: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    )
    gcp_location: str = "us-central1"
    dashscope_api_key: str = field(
        default_factory=lambda: os.environ.get("DASHSCOPE_API_KEY", "")
    )

    # 路径配置
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)

    @property
    def test_images_dir(self) -> Path:
        return self.base_dir / "test_images"

    @property
    def results_dir(self) -> Path:
        return self.base_dir / "results"

    def get_test_image_path(self, name: str) -> Path:
        """获取测试图片路径"""
        return self.test_images_dir / name

    def validate(self) -> list[str]:
        """验证配置，返回错误列表"""
        errors = []

        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY 环境变量未设置")

        if not self.gcp_credentials_path:
            errors.append("GOOGLE_APPLICATION_CREDENTIALS 环境变量未设置")
        elif not Path(self.gcp_credentials_path).exists():
            errors.append(f"GCP 凭证文件不存在: {self.gcp_credentials_path}")

        if not self.dashscope_api_key:
            errors.append("DASHSCOPE_API_KEY 环境变量未设置")

        return errors


def get_config() -> BenchmarkConfig:
    """获取配置实例"""
    return BenchmarkConfig()
