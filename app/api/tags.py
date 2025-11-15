"""API 标签常量定义。"""

from typing import Final


ANDROID_APP_TAG: Final[str] = "android_app"
WEB_APP_TAG: Final[str] = "web_app"
EVALUATION_APP_TAG: Final[str] = "evaluation"
INTERNAL_API_TAG: Final[str] = "internal"

# 兼容旧代码引用
INTY_EVAL_TAG: Final[str] = EVALUATION_APP_TAG
