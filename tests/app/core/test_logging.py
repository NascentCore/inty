import os
import re

from loguru import logger

from app.core.logging import init_logger


def test_logging_config_colorize():
    """colorize=True 时格式仅增加颜色标签，占位符与结构与非 colorize 一致"""
    from app.utils.config import LOGGING_FILE_FORMAT, LOGGING_LEVEL_FORMAT, LOGGING_MESSAGE_FORMAT, LOGGING_TIME_FORMAT, LoggingConfig

    cfg_plain = LoggingConfig(colorize=False)
    cfg_color = LoggingConfig(colorize=True)

    # 颜色格式应包含与无颜色相同的占位符
    for placeholder in (LOGGING_TIME_FORMAT, LOGGING_LEVEL_FORMAT, LOGGING_FILE_FORMAT, LOGGING_MESSAGE_FORMAT):
        assert placeholder in cfg_color.format, f"colorized format must contain {placeholder!r}"

    # 颜色格式应只增加 loguru 颜色标签，去掉标签后与无颜色格式一致（只剥已知颜色标签，避免误伤 {level: <8} 中的 <）
    color_tag_pattern = re.compile(r"</?(?:green|level|magenta|white)>")
    stripped = color_tag_pattern.sub("", cfg_color.format)
    assert stripped == cfg_plain.format, "colorized format must equal plain format after stripping color tags"
