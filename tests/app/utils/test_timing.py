"""
Test timing utilities.
"""

import time

from app.utils.timing import Timeer, log_time


def test_log_time_context_manager():
    """Test log_time context manager functionality."""
    with log_time("测试操作"):
        time.sleep(0.1)


def test_timeer_class():
    """Test Timeer class functionality."""
    timer = Timeer("测试操作")
    time.sleep(0.1)
    result = timer.stop()
    assert "测试操作" in result
    assert "耗时" in result
