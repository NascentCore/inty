from __future__ import annotations

import time
import urllib.error
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryableError(RuntimeError):
    """可重试错误：触发指数退避重试。"""


class TerminalError(RuntimeError):
    """不可重试错误：立即失败并上抛。"""


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    base_delay_seconds: float

    def execute(self, func: Callable[[], T]) -> T:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be > 0")
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be > 0")

        attempt = 0
        while True:
            try:
                return func()
            except TerminalError:
                raise
            except (
                TimeoutError,
                ConnectionError,
                urllib.error.URLError,
            ) as exc:
                attempt += 1
                if attempt >= self.max_attempts:
                    raise RetryableError(
                        f"exceeded retries: attempts={attempt}"
                    ) from exc
                backoff = self.base_delay_seconds * (2 ** (attempt - 1))
                time.sleep(backoff)
