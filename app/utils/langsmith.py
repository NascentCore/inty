from typing import Any
from langsmith.run_helpers import get_current_run_tree


PROVIDER_RESPONSE_KEY = "raw_response_from_provider"


def attach_provider_response_to_langsmith_run(response: Any) -> None:
    """若当前在 LangSmith trace 内，将本次响应写入当前 run 的 metadata。"""
    run = get_current_run_tree()
    if run is not None:
        run.metadata[PROVIDER_RESPONSE_KEY] = response
