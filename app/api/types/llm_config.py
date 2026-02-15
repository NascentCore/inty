# API 与内部共用的 LLM 配置类型，字段与约束取自 agent/festival_memory/core 等处常用参数。

from typing import Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM 模型配置，供 API 与内部统一使用。"""
    model: Optional[str] = Field(
        None,
        description="Model name, e.g. 'gpt-4o'. With aggregate providers (e.g. OpenRouter), use <provider>/<model> format.",
    )

    max_tokens: Optional[int] = Field(
        2048, ge=1, le=8192, description="Maximum tokens in response"
    )

    temperature: Optional[float] = Field(
        0.7, ge=0.0, le=2.0, description="Temperature for response generation"
    )

    top_p: Optional[float] = Field(
        0.9, ge=0.0, le=1.0, description="Top-p sampling parameter"
    )
    top_k: Optional[int] = Field(None, ge=1, description="Top-k sampling parameter")
    presence_penalty: Optional[float] = Field(
        0.3, ge=-2.0, le=2.0, description="只要你提过这个词，我就打压它, higher means more likely to generate new tokens"
    )
    frequency_penalty: Optional[float] = Field(
        0.3, ge=-2.0, le=2.0, description="你提这个词次数越多，我打压得越狠。higher means less repetition"
    )
