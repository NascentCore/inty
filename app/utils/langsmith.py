"""
https://docs.langchain.com/langsmith/sample-traces
export LANGSMITH_TRACING_SAMPLING_RATE=0.75
全局，不对错误进行特别处理，也就是错误/异常调用也按这个概率采样。
https://github.com/NascentCore/inty/pull/2402/changes 要对这个改动修改一下：
- [ ] 删除 external_services/fal.py
"""

from typing import Any, Optional

from langsmith.run_helpers import get_current_run_tree


PROVIDER_RESPONSE_KEY = "raw_response_from_provider"


def attach_provider_response_to_langsmith_run(response: Any, key: str = PROVIDER_RESPONSE_KEY) -> None:
    """若当前在 LangSmith trace 内，将本次响应写入当前 run 的 metadata。"""
    run = get_current_run_tree()
    if run is not None:
        run.metadata[key] = response


def get_current_trace_info() -> tuple[Optional[str], Optional[str]]:
    """返回当前 trace 的 trace_id 与可直接访问的 LangSmith URL。"""
    run = get_current_run_tree()
    if run is None:
        return (None, None)
    trace_id_raw = getattr(run, "trace_id", None) or getattr(run, "id", None)
    trace_id = str(trace_id_raw) if trace_id_raw is not None else None
    trace_url = run.get_url() if trace_id is not None else None
    return (trace_id, trace_url)
