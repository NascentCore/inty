"""
Timing utilities for measuring execution time.
"""

import time
from contextlib import contextmanager
from typing import Generator, Optional

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
