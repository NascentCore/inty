"""
与测试 langsmith 追踪相关的工具函数。
"""

import datetime
import os
import time

import langsmith
from langsmith import Client as LangSmithClient


# 轮询 LangSmith 时的尝试次数与每页 run 数量（用于写入延迟）
_LANGSMITH_POLL_ATTEMPTS = 3
_LANGSMITH_RUNS_PAGE_SIZE = 10
_LANGSMITH_POLL_SLEEP_SECONDS = 2


def _first_message_content(run: langsmith.schemas.Run) -> str | None:
    """Return the first message content from run.inputs if present, else None."""
    if not isinstance(run.inputs, dict) or "messages" not in run.inputs:
        return None
    messages = run.inputs["messages"]
    if not messages:
        return None
    first = messages[0]
    return first.get("content") if isinstance(first, dict) else None


def _inputs_contain_substring(obj: object, substring: str) -> bool:
    """Return True if substring appears in any string value within obj (dict/list/str)."""
    if isinstance(obj, str):
        return substring in obj
    if isinstance(obj, dict):
        return any(_inputs_contain_substring(v, substring) for v in obj.values())
    if isinstance(obj, list):
        return any(_inputs_contain_substring(v, substring) for v in obj)
    return False


def find_run_inputs_contain_string(
    start_time: datetime.datetime,
    substring: str,
    *,
    project_name: str | None = None,
) -> langsmith.schemas.Run | None:
    """Query LangSmith for a run whose inputs contain substring (e.g. prompt with UUID). Returns None if not found."""
    ls_client = LangSmithClient()
    proj = project_name or os.environ["LANGSMITH_PROJECT"]

    for attempt in range(_LANGSMITH_POLL_ATTEMPTS):
        print(f"Attempt {attempt} to find run whose inputs contain: {substring!r}")
        runs = ls_client.list_runs(
            project_name=proj,
            start_time=start_time,
            limit=_LANGSMITH_RUNS_PAGE_SIZE,
        )
        runs_list = list(runs)
        for run in runs_list:
            if run.inputs and _inputs_contain_substring(run.inputs, substring):
                return run
        if attempt < _LANGSMITH_POLL_ATTEMPTS - 1:
            time.sleep(_LANGSMITH_POLL_SLEEP_SECONDS)
    return None


def find_run_contains_random_string(
    start_time: datetime.datetime, random_str: str
) -> langsmith.schemas.Run | None:
    """Query LangSmith for a run whose first message content equals random_str; returns None if not found."""
    ls_client = LangSmithClient()

    for attempt in range(_LANGSMITH_POLL_ATTEMPTS):
        print(f"Attempt {attempt} to find the run with the random string: {random_str}")
        runs = ls_client.list_runs(
            project_name=os.environ["LANGSMITH_PROJECT"],
            start_time=start_time,
            limit=_LANGSMITH_RUNS_PAGE_SIZE,
        )
        runs_list = list(runs)
        for run in runs_list:
            if _first_message_content(run) == random_str:
                return run
        if attempt < _LANGSMITH_POLL_ATTEMPTS - 1:
            time.sleep(_LANGSMITH_POLL_SLEEP_SECONDS)
    return None
