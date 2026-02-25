"""
https://docs.langchain.com/langsmith/sample-traces
export LANGSMITH_TRACING_SAMPLING_RATE=0.75
全局，不对错误进行特别处理，也就是错误/异常调用也按这个概率采样。
https://github.com/NascentCore/inty/pull/2402/changes 要对这个改动修改一下：
- [ ] 删除 external_services/fal.py
"""

from typing import Any
from langsmith.run_helpers import get_current_run_tree


PROVIDER_RESPONSE_KEY = "raw_response_from_provider"


def attach_provider_response_to_langsmith_run(response: Any, key: str = PROVIDER_RESPONSE_KEY) -> None:
    """若当前在 LangSmith trace 内，将本次响应写入当前 run 的 metadata。"""
    run = get_current_run_tree()
    if run is not None:
        run.metadata[key] = response
