#!/usr/bin/env python3
"""
日志配置和管理
提供统一的日志输出格式和配置
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from colorama import Fore, Style, init

init(autoreset=True)
COLORAMA_AVAILABLE = True


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式器"""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        if COLORAMA_AVAILABLE:
            self.colors = {
                "DEBUG": Fore.CYAN,
                "INFO": Fore.GREEN,
                "WARNING": Fore.YELLOW,
                "ERROR": Fore.RED,
                "CRITICAL": Fore.RED + Style.BRIGHT,
            }
        else:
            self.colors = {}

    def format(self, record):
        if COLORAMA_AVAILABLE and record.levelname in self.colors:
            record.levelname = f"{self.colors[record.levelname]}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


def setup_logger(
    name: str = "agent_tags_migration",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True,
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        console_output: 是否输出到控制台

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 清除现有的处理器
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    colored_formatter = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_default_log_file() -> str:
    """获取默认日志文件路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"agent_tags_migration_{timestamp}.log"


class MigrationLogger:
    """迁移操作专用日志记录器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._progress_count = 0
        self._total_count = 0

    def set_progress_total(self, total: int):
        """设置总进度数"""
        self._total_count = total
        self._progress_count = 0

    def log_progress(self, message: str = "", increment: int = 1):
        """记录进度"""
        self._progress_count += increment
        if self._total_count > 0:
            percentage = (self._progress_count / self._total_count) * 100
            progress_msg = f"[{self._progress_count}/{self._total_count}] ({percentage:.1f}%)"
            if message:
                progress_msg += f" {message}"
            self.logger.info(progress_msg)
        else:
            if message:
                self.logger.info(f"[{self._progress_count}] {message}")

    def log_extraction_success(self, agent_name: str, tags: list, method: str):
        """记录成功提取标签"""
        self.logger.debug(
            f"✓ {agent_name}: 提取到 {len(tags)} 个标签 ({method}) - {', '.join(tags)}"
        )

    def log_extraction_failure(self, agent_name: str, error: str):
        """记录提取失败"""
        self.logger.warning(f"✗ {agent_name}: 提取失败 - {error}")

    def log_update_success(self, agent_name: str, tags: list):
        """记录更新成功"""
        self.logger.info(f"✓ 更新成功: {agent_name} - 标签: {', '.join(tags)}")

    def log_update_failure(self, agent_name: str, error: str):
        """记录更新失败"""
        self.logger.error(f"✗ 更新失败: {agent_name} - {error}")

    def log_stats(self, stats_dict: dict):
        """记录统计信息"""
        self.logger.info("=" * 50)
        self.logger.info("迁移统计信息:")
        for key, value in stats_dict.items():
            if isinstance(value, dict) and len(value) > 0:
                self.logger.info(f"  {key}:")
                for sub_key, sub_value in list(value.items())[
                    :10
                ]:  # 只显示前10个
                    self.logger.info(f"    {sub_key}: {sub_value}")
                if len(value) > 10:
                    self.logger.info(f"    ... 还有 {len(value) - 10} 个")
            else:
                self.logger.info(f"  {key}: {value}")
        self.logger.info("=" * 50)
