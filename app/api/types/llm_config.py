# API 与内部共用的 LLM 配置类型，字段与约束取自 agent/festival_memory/core 等处常用参数。

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """LLM 模型配置，供 API 与内部统一使用。"""

    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Temperature for response generation"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, le=8192, description="Maximum tokens in response"
    )
    top_p: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Top-p sampling parameter"
    )
    top_k: Optional[int] = Field(None, ge=1, description="Top-k sampling parameter")
    frequency_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Presence penalty"
    )

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if v is not None and (v < 0.0 or v > 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @field_validator("top_p")
    @classmethod
    def validate_top_p(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Top-p must be between 0.0 and 1.0")
        return v
