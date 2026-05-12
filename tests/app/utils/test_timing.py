"""
Test timing utilities.
"""

import time

from app.utils.timing import Timer


def test_timeer_class():
    """Test Timeer class functionality."""
    timer = Timer("测试操作")
    time.sleep(0.1)
    result = timer.stop()
    assert "测试操作" in result
    assert "耗时" in result
