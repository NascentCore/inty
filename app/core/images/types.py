"""
公共的数据类型用于图片生成。
"""
from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel

from app.utils.image import ImageFormat, ImageSize


class GeneratedImageProcessResult(BaseModel):
    """Result of processing a provider image output: metadata plus raw data and GCS URI.
    raw_data 正常为 bytes；LangSmith trace 副本中为 base64 字符串以缩小 trace 体积。
    raw_response_from_provider 可存 Google GenerateContentResponse 或 FAL handler/raw result。
    """

    size: ImageSize
    format: ImageFormat
    raw_data: bytes | str | None = None
    raw_data_total_bytes: int = 0
    gcs_uri: str
    gcs_http_url: str
    generated_at: datetime.datetime
    raw_response_from_provider: Any | None = None
