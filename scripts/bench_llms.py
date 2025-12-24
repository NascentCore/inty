#!/usr/bin/env python3
"""
CREATED_BY_AGENT

基于 OpenRouter 的 TTFT（time-to-first-token）最小基准测试脚本。

说明
----
- 通过 OpenAI 兼容接口（OpenRouter）以流式方式请求，并测量首次收到 content token 的耗时。
- prompt 来自 `app/core/agent/prompts.py`，用变量名通过 `--prompt` 指定。
- 输出包含：控制台汇总、JSON 结果文件、以及 matplotlib 绘图（可选）。

运行前准备
----------
- 设置环境变量：
  - `OPENROUTER_API_KEY`: OpenRouter API Key
  - 可选：`OPENROUTER_BASE_URL`（默认 https://openrouter.ai/api/v1）
- 按仓库约定，不在脚本里改 sys.path，请从仓库根目录运行，并设置：
  - `PYTHONPATH=.`

示例
----
PYTHONPATH=. OPENROUTER_API_KEY=... python scripts/bench_llms.py \
  --models openai/gpt-4o-mini --models anthropic/claude-3.5-sonnet \
  --iterations 5 \
  --prompt PURITY_ROLEPLAY_PROMPT
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import cyclopts


def _quantile(xs: list[float], q: float) -> float:
    if not xs:
        raise ValueError("empty list")
    if not (0 <= q <= 1):
        raise ValueError("q must be in [0, 1]")
    xs_sorted = sorted(xs)
    idx = int(round((len(xs_sorted) - 1) * q))
    return xs_sorted[idx]


def _now_s() -> float:
    return time.perf_counter()


def _env(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key)
    if val is not None and val.strip() == "":
        return default
    return val if val is not None else default


def _prompt_candidates() -> dict[str, Any]:
    from app.core.agent import prompts as prompts_module

    candidates: dict[str, Any] = {}
    for name, value in vars(prompts_module).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            candidates[name] = value
            continue
        # StructuredPrompt（pydantic BaseModel）在 prompts.py 里定义
        if value.__class__.__name__ == "StructuredPrompt":
            candidates[name] = value
    return candidates


def _messages_from_prompt(prompt_name: str, user_message: str) -> list[dict[str, str]]:
    candidates = _prompt_candidates()
    if prompt_name not in candidates:
        available = "\n".join(sorted(candidates.keys()))
        raise ValueError(
            f"未找到 prompt 变量：{prompt_name}\n"
            f"请使用 `app/core/agent/prompts.py` 中的变量名，例如：\n{available}"
        )

    prompt_obj = candidates[prompt_name]
    if isinstance(prompt_obj, str):
        return [
            {"role": "system", "content": prompt_obj},
            {"role": "user", "content": user_message},
        ]

    # StructuredPrompt：assemble() -> list[dict]
    assemble = getattr(prompt_obj, "assemble", None)
    if callable(assemble):
        messages = assemble()
        return [*messages, {"role": "user", "content": user_message}]

    raise TypeError(f"不支持的 prompt 类型：{prompt_name} -> {type(prompt_obj)!r}")


@dataclass(frozen=True)
class IterationResult:
    model: str
    iteration: int
    ttft_ms: float | None
    error: str | None = None


@dataclass(frozen=True)
class ModelSummary:
    model: str
    n: int
    successes: int
    failures: int
    mean_ms: float | None
    median_ms: float | None
    p95_ms: float | None
    stdev_ms: float | None


async def _measure_ttft_ms(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_s: float,
) -> float:
    start = _now_s()
    stream = None
    first: float | None = None
    try:
        async with asyncio.timeout(timeout_s):
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    first = _now_s()
                    break
    finally:
        if stream is not None:
            close = getattr(stream, "close", None)
            if callable(close):
                try:
                    res = close()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass

    if first is None:
        raise RuntimeError("stream ended before any content token received")
    return (first - start) * 1000


def _summarize(model: str, ttfts_ms: list[float], failures: int) -> ModelSummary:
    if not ttfts_ms:
        return ModelSummary(
            model=model,
            n=0,
            successes=0,
            failures=failures,
            mean_ms=None,
            median_ms=None,
            p95_ms=None,
            stdev_ms=None,
        )

    mean_ms = statistics.mean(ttfts_ms)
    median_ms = statistics.median(ttfts_ms)
    p95_ms = _quantile(ttfts_ms, 0.95)
    stdev_ms = statistics.pstdev(ttfts_ms) if len(ttfts_ms) >= 2 else 0.0
    return ModelSummary(
        model=model,
        n=len(ttfts_ms) + failures,
        successes=len(ttfts_ms),
        failures=failures,
        mean_ms=mean_ms,
        median_ms=median_ms,
        p95_ms=p95_ms,
        stdev_ms=stdev_ms,
    )


def _print_summary(summaries: list[ModelSummary]) -> None:
    def fmt(x: float | None) -> str:
        return "-" if x is None else f"{x:8.1f}"

    print("\n=== TTFT 汇总（单位：ms）===")
    print(
        "model".ljust(38),
        "ok".rjust(5),
        "fail".rjust(6),
        "mean".rjust(10),
        "median".rjust(10),
        "p95".rjust(10),
        "stdev".rjust(10),
    )
    for s in summaries:
        print(
            s.model[:38].ljust(38),
            str(s.successes).rjust(5),
            str(s.failures).rjust(6),
            fmt(s.mean_ms),
            fmt(s.median_ms),
            fmt(s.p95_ms),
            fmt(s.stdev_ms),
        )


def _write_json(
    *,
    output_json: Path,
    prompt: str,
    iterations: int,
    user_message: str,
    raw: list[IterationResult],
    summaries: list[ModelSummary],
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "prompt": prompt,
        "iterations": iterations,
        "user_message": user_message,
        "results": [asdict(r) for r in raw],
        "summaries": [asdict(s) for s in summaries],
    }
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _plot(
    *,
    output_png: Path,
    summaries: list[ModelSummary],
    title: str,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "未安装 matplotlib，无法绘图。请先安装：pip install -r scripts/requirements.txt"
        ) from e

    # 只画成功样本的 mean（失败的模型会被跳过）
    xs: list[str] = []
    means: list[float] = []
    errs: list[float] = []
    for s in summaries:
        if s.mean_ms is None or s.stdev_ms is None:
            continue
        xs.append(s.model)
        means.append(s.mean_ms)
        errs.append(s.stdev_ms)

    if not xs:
        raise RuntimeError("没有可绘制的数据（所有模型都没有成功样本）")

    output_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(max(8, len(xs) * 1.2), 4.8))
    ax.bar(xs, means, yerr=errs, capsize=4)
    ax.set_title(title)
    ax.set_ylabel("TTFT (ms)")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=25, labelsize=9)
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)


app = cyclopts.App(help="OpenRouter 模型 TTFT（首 token 延迟）基准测试")


@app.default
def main(
    models: Annotated[
        list[str],
        cyclopts.Parameter(
            name="--models",
            help="要测试的 OpenRouter 模型（可多次传入，例如：--models a --models b）",
            required=True,
        ),
    ],
    prompt: str = "PURITY_ROLEPLAY_PROMPT",
    iterations: int = 5,
    user_message: str = "用中文只回答一个词：你好",
    temperature: float = 0.0,
    max_tokens: int = 16,
    timeout_s: float = 60.0,
    sleep_s: float = 0.0,
    output_json: str = "bench_llms_ttft.json",
    output_png: str = "bench_llms_ttft.png",
    plot: bool = True,
):
    """
    运行 TTFT 基准测试。

    Args:
        models: 要测试的 OpenRouter 模型（可多次传入，例如：--models a --models b）
        prompt: `app/core/agent/prompts.py` 中的 prompt 变量名
        iterations: 每个模型重复次数
        user_message: user 消息内容（尽量短，以减少非 TTFT 变量）
        temperature: 采样温度
        max_tokens: 输出 token 上限（建议很小，只为拿到首 token）
        timeout_s: 单次请求超时（秒）
        sleep_s: 每次迭代之间 sleep（秒），用于避免触发速率限制
        output_json: JSON 输出路径
        output_png: PNG 输出路径（plot=True 时有效）
        plot: 是否绘图（需要 matplotlib）
    """
    if iterations <= 0:
        raise ValueError("--iterations 必须 > 0")
    if not models:
        raise ValueError("--models 不能为空（至少指定一个模型）")

    api_key = _env("OPENROUTER_API_KEY") or _env("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "缺少 API Key：请设置 OPENROUTER_API_KEY（或 OPENAI_API_KEY）"
        )

    base_url = _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    extra_headers: dict[str, str] = {}
    referer = _env("OPENROUTER_REFERER")
    title = _env("OPENROUTER_TITLE")
    if referer:
        extra_headers["HTTP-Referer"] = referer
    if title:
        extra_headers["X-Title"] = title

    messages = _messages_from_prompt(prompt, user_message)

    asyncio.run(
        _run(
            models=models,
            iterations=iterations,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            sleep_s=sleep_s,
            base_url=base_url,
            api_key=api_key,
            extra_headers=extra_headers,
            output_json=Path(output_json),
            output_png=Path(output_png),
            prompt=prompt,
            user_message=user_message,
            plot=plot,
        )
    )


async def _run(
    *,
    models: list[str],
    iterations: int,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_s: float,
    sleep_s: float,
    base_url: str,
    api_key: str,
    extra_headers: dict[str, str],
    output_json: Path,
    output_png: Path,
    prompt: str,
    user_message: str,
    plot: bool,
) -> None:
    try:
        from openai import AsyncOpenAI
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "未安装 openai SDK。请先安装：pip install -r scripts/requirements.txt"
        ) from e

    client = AsyncOpenAI(
        base_url=base_url, api_key=api_key, default_headers=extra_headers
    )

    raw_results: list[IterationResult] = []
    summaries: list[ModelSummary] = []

    for model in models:
        print(f"\n--- 测试模型：{model}（iterations={iterations}）---")
        ttfts: list[float] = []
        failures = 0

        for i in range(iterations):
            try:
                ttft_ms = await _measure_ttft_ms(
                    client=client,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout_s=timeout_s,
                )
                ttfts.append(ttft_ms)
                raw_results.append(
                    IterationResult(
                        model=model, iteration=i + 1, ttft_ms=ttft_ms, error=None
                    )
                )
                print(f"  iter {i + 1}/{iterations}: ttft={ttft_ms:.1f}ms")
            except Exception as e:
                failures += 1
                raw_results.append(
                    IterationResult(
                        model=model, iteration=i + 1, ttft_ms=None, error=str(e)
                    )
                )
                print(f"  iter {i + 1}/{iterations}: failed: {e}")

            if sleep_s > 0:
                await asyncio.sleep(sleep_s)

        summaries.append(_summarize(model, ttfts, failures))

    _print_summary(summaries)
    _write_json(
        output_json=output_json,
        prompt=prompt,
        iterations=iterations,
        user_message=user_message,
        raw=raw_results,
        summaries=summaries,
    )
    print(f"\n已写入 JSON：{output_json}")

    if plot:
        _plot(
            output_png=output_png,
            summaries=summaries,
            title=f"OpenRouter TTFT Benchmark (prompt={prompt}, n={iterations})",
        )
        print(f"已写入图表：{output_png}")


if __name__ == "__main__":
    app()
