"""
Timing utilities for measuring execution time.
"""

import time
from contextlib import contextmanager
from typing import Generator

from loguru import logger


@contextmanager
def log_time(operation_name: str) -> Generator[None, None, None]:
    """
    Context manager to measure and log execution time of operations.

    Args:
        operation_name: Name of the operation being measured
    Example:
        with log_time("历史记录初始化"):
            history = PostgresChatMessageHistory(...)
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.debug(f"{operation_name}耗时: {elapsed_time:.3f}秒")


class Timer:
    """计时器
    用于记录某个操作的耗时，使用方法：
    timer = Timeer("测试操作")
    time.sleep(0.1)
    mesage = timer.stop()
    print(mesage)
    """

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = time.time()

    def stop(self):
        self.elapsed_time = time.time() - self.start_time
        return f"[{self.operation_name}] 耗时: {self.elapsed_time:.3f} 秒"
