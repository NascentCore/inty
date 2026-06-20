import os
import re
import logging

from loguru import logger

from app.core.logging import init_logger


def test_logging_timezone_format():
    """测试日志时间格式包含时区信息"""
    logger.remove()
    init_logger()
    logged_messages = []

    def custom_sink(message):
        logged_messages.append(str(message))

    # 使用配置中的格式，确保时区信息被包含
    from app.core.config import global_config_loaded_from_config_yaml

    logger.add(
        custom_sink, format=global_config_loaded_from_config_yaml.logging.format
    )

    logger.info("This is an informational message.")
    logger.debug("A debug statement here.")
    logger.error("Something went wrong!")

    # 只校验本测试主动发出的 3 条日志；忽略其他后台线程（如 tracing/http）噪声日志。
    expected_fragments = [
        "This is an informational message.",
        "A debug statement here.",
        "Something went wrong!",
    ]
    target_messages = [
        message
        for message in logged_messages
        if any(fragment in message for fragment in expected_fragments)
    ]

    assert len(target_messages) == 3

    for message in target_messages:
        assert re.search(
            r"\d{3} [+-]\d{4}", message
        ), f"Expected local wall time with numeric offset (ZZ), got: {message}"


def test_logging_environment_timezone():
    """测试环境时区设置"""
    original_tz = os.environ.get("TZ")

    try:
        # 设置不同的时区
        os.environ["TZ"] = "Asia/Shanghai"

        # 重新初始化日志
        init_logger()

        assert os.environ.get("TZ") == "Asia/Shanghai"

    finally:
        # 恢复原始环境变量
        if original_tz is not None:
            os.environ["TZ"] = original_tz
        elif "TZ" in os.environ:
            del os.environ["TZ"]


def test_logging_config_colorize():
    """colorize=True 时格式仅增加颜色标签，占位符与结构与非 colorize 一致"""
    from app.utils.config import (
        LOGGING_FILE_FORMAT,
        LOGGING_LEVEL_FORMAT,
        LOGGING_MESSAGE_FORMAT,
        LOGGING_TIME_FORMAT,
        LoggingConfig,
    )

    cfg_plain = LoggingConfig(colorize=False)
    cfg_color = LoggingConfig(colorize=True)

    # 颜色格式应包含与无颜色相同的占位符
    for placeholder in (
        LOGGING_TIME_FORMAT,
        LOGGING_LEVEL_FORMAT,
        LOGGING_FILE_FORMAT,
        LOGGING_MESSAGE_FORMAT,
    ):
        assert (
            placeholder in cfg_color.format
        ), f"colorized format must contain {placeholder!r}"

    # 颜色格式应只增加 loguru 颜色标签，去掉标签后与无颜色格式一致（只剥已知颜色标签，避免误伤 {level: <8} 中的 <）
    color_tag_pattern = re.compile(r"</?(?:green|level|magenta|white)>")
    stripped = color_tag_pattern.sub("", cfg_color.format)
    assert (
        stripped == cfg_plain.format
    ), "colorized format must equal plain format after stripping color tags"


def test_inty_console_logging_level_filters_stderr_not_file(
    tmp_path, monkeypatch, capsys
):
    log_path = tmp_path / "app.log"
    monkeypatch.setenv("INTY_LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("INTY_CONSOLE_LOGGING_LEVEL", "INFO")
    monkeypatch.setenv("INTY_LOG_FILE", str(log_path))
    logger.remove()
    init_logger()

    logger.debug("inty_split_log_debug_marker")
    logger.info("inty_split_log_info_marker")
    logger.complete()

    err = capsys.readouterr().err
    assert "inty_split_log_debug_marker" not in err
    assert "inty_split_log_info_marker" in err
    body = log_path.read_text(encoding="utf-8")
    assert "inty_split_log_debug_marker" in body
    assert "inty_split_log_info_marker" in body


def test_logging_suppresses_openai_request_payload_debug_logs():
    init_logger()

    assert logging.getLogger("openai").level == logging.WARNING
    assert logging.getLogger("openai._base_client").level == logging.WARNING
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
