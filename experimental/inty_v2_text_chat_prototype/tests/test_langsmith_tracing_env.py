"""LangSmith 开关：SDK 只认小写字符串 true；环境规范化逻辑。"""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def _restore_langsmith_env():
    keys = (
        "LANGSMITH_TRACING_V2",
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_TRACING",
    )
    before = {k: os.environ.get(k) for k in keys}
    yield
    for k in keys:
        v = before[k]
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_coerce_langsmith_tracing_normalizes_one(_restore_langsmith_env):
    from experimental.inty_v2_text_chat_prototype.client import _coerce_langsmith_tracing_env

    os.environ["LANGSMITH_TRACING"] = "1"
    _coerce_langsmith_tracing_env()
    assert os.environ["LANGSMITH_TRACING"] == "true"


def test_coerce_langsmith_tracing_leaves_false(_restore_langsmith_env):
    from experimental.inty_v2_text_chat_prototype.client import _coerce_langsmith_tracing_env

    os.environ["LANGSMITH_TRACING_V2"] = "false"
    _coerce_langsmith_tracing_env()
    assert os.environ["LANGSMITH_TRACING_V2"] == "false"
