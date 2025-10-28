import os
import re

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
    logger.add(custom_sink, format=global_config_loaded_from_config_yaml.logging.format)

    logger.info("This is an informational message.")
    logger.debug("A debug statement here.")
    logger.error("Something went wrong!")
    
    assert len(logged_messages) == 3
    
    for message in logged_messages:
        assert " UTC " in message, f"Expected UTC timezone, got: {message}"


def test_logging_environment_timezone():
    """测试环境时区设置"""
    original_tz = os.environ.get("TZ")
    
    try:
        # 设置不同的时区
        os.environ["TZ"] = "Asia/Shanghai"
        
        # 重新初始化日志
        init_logger()
        
        # 验证TZ被强制设置为UTC
        assert os.environ.get("TZ") == "UTC"
        
    finally:
        # 恢复原始环境变量
        if original_tz is not None:
            os.environ["TZ"] = original_tz
        elif "TZ" in os.environ:
            del os.environ["TZ"]


def test_logging_config_format():
    """测试日志配置格式"""
    # 初始化日志
    init_logger()
    
    # 验证配置中的时间格式
    from app.core.config import global_config_loaded_from_config_yaml
    format_str = global_config_loaded_from_config_yaml.logging.format
    
    # 验证时间格式包含时区信息
    assert "{time:" in format_str
    assert "zz" in format_str  # 时区缩写
    
    # 验证格式字符串的完整性
    assert "YYYY-MM-DD HH:mm:ss.SSS" in format_str
    assert "{level:" in format_str
    assert "{name}" in format_str
    assert "{function}" in format_str
    assert "{line}" in format_str
    assert "{message}" in format_str
