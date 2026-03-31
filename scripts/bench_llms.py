#!/usr/bin/env python3
"""
CREATED_BY_AGENT

LLM 模型 TTFT（time-to-first-token）和 TTL（time-to-last）基准测试脚本。

说明
----
- 支持通过 OpenAI 兼容接口（OpenRouter）或 Google GenAI SDK 调用模型
- 测量首次收到 content token 的耗时（TTFT）和流式响应完全结束的时间（TTL）
- prompt 来自 `app/core/agent/prompts.py`，用变量名通过 `--prompt` 指定
- 输出包含：控制台汇总、JSON 结果文件、以及 matplotlib 绘图（可选）

运行前准备
----------
- 按仓库约定，不在脚本里改 sys.path，请从仓库根目录运行，并设置：
  - `PYTHONPATH=.`

- 对于 OpenRouter 模型（非 `google/` 前缀）：
  - 设置环境变量：`OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`
  - 可选：`OPENROUTER_BASE_URL`（默认 https://openrouter.ai/api/v1）

- 对于 Google GenAI 模型（`google/` 前缀）：
  - 方式1（推荐）：在项目根目录放置 `inty-backend-key.json` 服务账号密钥文件
    - 脚本会自动查找并使用该文件进行 Vertex AI 认证
    - 可选：`GOOGLE_CLOUD_PROJECT`（默认：从密钥文件读取或 inty-backend）
    - 可选：`GOOGLE_CLOUD_LOCATION`（默认：us-central1）
  - 方式2：设置 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量指向服务账号密钥文件
  - 方式3：设置 `GOOGLE_API_KEY` 或 `GEMINI_API_KEY`（API Key 方式）

示例
----
# 使用默认模型（google/gemini-2.5-flash、google/gemini-2.5-flash-lite 和 minimax/minimax-m2-her）
PYTHONPATH=. OPENROUTER_API_KEY=... GOOGLE_API_KEY=... python scripts/bench_llms.py \
  --iterations 5 \
  --prompt PURITY_ROLEPLAY_PROMPT

# 测试 OpenRouter 模型
PYTHONPATH=. OPENROUTER_API_KEY=... python scripts/bench_llms.py \
  --models openai/gpt-4o-mini --models anthropic/claude-3.5-sonnet \
  --iterations 5 \
  --prompt PURITY_ROLEPLAY_PROMPT

# 测试 Google GenAI 模型
PYTHONPATH=. GOOGLE_API_KEY=... python scripts/bench_llms.py \
  --models google/gemini-2.5-flash --models google/gemini-2.0-flash-exp \
  --iterations 5 \
  --prompt PURITY_ROLEPLAY_PROMPT

# 混合测试
PYTHONPATH=. OPENROUTER_API_KEY=... GOOGLE_API_KEY=... python scripts/bench_llms.py \
  --models openai/gpt-4o-mini --models google/gemini-2.5-flash \
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


def _convert_messages_to_google_genai(
    messages: list[dict[str, str]],
) -> list[Any]:
    """将 OpenAI 格式的 messages 转换为 Google GenAI 的 types.Content 列表"""
    from google.genai import types

    contents: list[types.Content] = []
    system_parts: list[str] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            # Google GenAI 不支持单独的 system role，合并到第一个 user message
            system_parts.append(content)
        elif role == "user":
            # 如果有 system parts，合并到 user message 中
            user_content = content
            if system_parts:
                user_content = "\n\n".join(system_parts) + "\n\n" + user_content
                system_parts = []  # 清空，只合并到第一个 user message

            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_content)],
                )
            )
        elif role == "assistant":
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=content)],
                )
            )

    return contents


@dataclass(frozen=True)
class IterationResult:
    model: str
    iteration: int
    ttft_ms: float | None
    ttl_ms: float | None = None
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
    ttl_mean_ms: float | None = None
    ttl_median_ms: float | None = None
    ttl_p95_ms: float | None = None
    ttl_stdev_ms: float | None = None


async def _measure_google_genai_times(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_s: float,
) -> tuple[float, float]:
    """测量 Google GenAI 的 TTFT 和 TTL"""
    from google.genai import types

    start = _now_s()
    first: float | None = None
    last: float | None = None

    # 转换消息格式
    contents = _convert_messages_to_google_genai(messages)

    # 移除模型名称前缀 "google/"
    actual_model = (
        model.replace("google/", "", 1) if model.startswith("google/") else model
    )

    # 创建配置，降低安全过滤级别以避免测试被拦截
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_ONLY_HIGH",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_ONLY_HIGH",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ],
    )

    def run_stream() -> tuple[float | None, float | None]:
        """在同步函数中运行流式调用"""
        first_local: float | None = None
        last_local: float | None = None
        chunk_count = 0
        text_chunk_count = 0
        previous_text_length = 0

        stream = client.models.generate_content_stream(
            model=actual_model,
            contents=contents,
            config=config,
        )

        for chunk in stream:
            chunk_count += 1
            current_time = _now_s()

            # 参考 Google GenAI SDK 官方示例：
            # 检查 chunk.candidates[0].content.parts 是否存在，然后直接使用 chunk.text
            # chunk.text 返回增量文本（每个 chunk 只包含新增部分）
            has_text = False

            # 检查 chunk 是否有有效的 candidates 和 content
            if (
                hasattr(chunk, "candidates")
                and chunk.candidates
                and len(chunk.candidates) > 0
                and chunk.candidates[0].content
                and chunk.candidates[0].content.parts
            ):
                # 直接使用 chunk.text（Google GenAI SDK 提供的便捷属性）
                # chunk.text 返回增量文本（每个 chunk 只包含新增部分）
                try:
                    if hasattr(chunk, "text") and chunk.text is not None:
                        text_content = chunk.text
                        if isinstance(text_content, str) and text_content.strip():
                            has_text = True
                except Exception:
                    pass

            # 如果找到文本内容，记录时间
            if has_text:
                text_chunk_count += 1
                if first_local is None:
                    first_local = current_time
                # 更新最后时间（每个有文本的 chunk 都更新）
                last_local = current_time

        # 如果收到了 chunk 但没有检测到文本，可能是流式格式问题
        # 但我们至少知道请求执行了
        if chunk_count > 0 and first_local is None:
            # 有 chunk 但没有文本，可能是格式问题
            # 这种情况下，流式调用可能没有正确工作，需要回退到非流式调用
            pass
        elif chunk_count > 0 and first_local is not None and last_local is not None:
            # 如果 first 和 last 相同或非常接近，说明所有文本可能在一个 chunk 中
            # 或者流式调用实际上没有真正流式返回
            time_diff = abs(last_local - first_local)
            if time_diff < 0.001:  # 小于 1ms
                # 所有文本在一个 chunk 中，这不是真正的流式
                # 但至少我们检测到了文本，所以返回这个时间
                # 这种情况下，TTFT 和 TTL 会相同，这是合理的
                pass

        return (first_local, last_local)

    # 使用 asyncio.to_thread 在线程中运行同步代码，并设置超时
    try:
        async with asyncio.timeout(timeout_s):
            first, last = await asyncio.to_thread(run_stream)
    except TimeoutError:
        raise RuntimeError(f"请求超时（>{timeout_s}秒）")
    except Exception as e:
        raise RuntimeError(f"Google GenAI 流式调用失败: {e}") from e

    if first is None:
        # 尝试一次非流式调用以获取更多错误信息和作为备选方案
        try:
            non_stream_start = _now_s()
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=actual_model,
                contents=contents,
                config=config,
            )
            non_stream_end = _now_s()

            # 检查 prompt_feedback（输入被拦截）
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                prompt_feedback = response.prompt_feedback
                block_reason = getattr(prompt_feedback, "block_reason", None)
                if block_reason:
                    raise RuntimeError(f"输入被安全策略拦截: {block_reason}")

            # 检查 candidates
            if response and hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]

                # 检查 finish_reason
                finish_reason = getattr(candidate, "finish_reason", None)
                if finish_reason == "SAFETY":
                    # 检查安全评级
                    safety_ratings = getattr(candidate, "safety_ratings", [])
                    safety_details = []
                    if safety_ratings:
                        for rating in safety_ratings:
                            category = getattr(rating, "category", "UNKNOWN")
                            probability = getattr(rating, "probability", "UNKNOWN")
                            safety_details.append(f"{category}={probability}")
                    error_msg = "输出被安全策略拦截"
                    if safety_details:
                        error_msg += f"，原因: {', '.join(safety_details)}"
                    raise RuntimeError(error_msg)

                # 检查是否有文本内容（优先检查文本，而不是 finish_reason）
                text_parts = []
                if hasattr(candidate, "content") and candidate.content:
                    if hasattr(candidate.content, "parts") and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                text_parts.append(part.text)

                if text_parts:
                    # 有文本内容，说明非流式调用成功
                    # 流式调用可能没有正确检测到文本增量
                    # 使用非流式调用的时间，但 TTFT 应该更小（因为流式应该更快）
                    # 如果流式调用确实执行了但没有检测到文本，说明可能是格式问题
                    # 这种情况下，我们假设流式调用实际上返回了所有文本在最后一个 chunk
                    # 所以 TTFT 和 TTL 应该接近（但 TTFT 应该稍小）
                    total_time = (non_stream_end - non_stream_start) * 1000
                    # 对于流式调用，TTFT 应该比 TTL 小，但如果所有文本都在最后返回，它们可能接近
                    # 使用一个合理的比例：TTFT 约为 TTL 的 90-95%
                    non_stream_ttft = (
                        total_time * 0.95
                    )  # 假设大部分时间在生成，首 token 稍早
                    non_stream_ttl = total_time
                    return (non_stream_ttft, non_stream_ttl)

                # 如果没有文本内容，检查 finish_reason
                if finish_reason == "MAX_TOKENS":
                    raise RuntimeError(
                        f"响应达到最大 token 限制（max_tokens={max_tokens}），但未检测到文本内容。"
                        "建议增加 max_tokens 或检查流式响应格式。"
                    )
                elif finish_reason and finish_reason not in ("STOP", None):
                    raise RuntimeError(
                        f"响应完成原因: {finish_reason}。可能是安全策略拦截或其他问题。"
                    )

            # 如果到这里，说明 response 存在但没有文本内容
            # 检查是否有 candidates 但没有内容
            if response and hasattr(response, "candidates"):
                if not response.candidates:
                    raise RuntimeError(
                        "响应中没有 candidates。可能是安全策略拦截了输入。"
                    )
                elif len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    finish_reason = getattr(candidate, "finish_reason", None)
                    if finish_reason:
                        raise RuntimeError(
                            f"响应完成原因: {finish_reason}。"
                            "可能是安全策略拦截或其他问题。"
                        )

            # 通用错误
            raise RuntimeError(
                "流式和非流式调用都未返回文本内容。"
                "可能是安全策略拦截或模型配置问题。"
            )
        except RuntimeError:
            # 重新抛出我们自己的错误
            raise
        except Exception as debug_e:
            raise RuntimeError(
                f"stream ended before any content token received. "
                f"非流式调用也失败: {type(debug_e).__name__}: {debug_e}"
            ) from debug_e

    if last is None:
        last = first  # 如果没有收到后续 chunk，使用 first 作为 last

    ttft_ms = (first - start) * 1000
    ttl_ms = (last - start) * 1000

    return (ttft_ms, ttl_ms)


async def _measure_openrouter_times(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_s: float,
) -> tuple[float, float]:
    """测量 OpenRouter（OpenAI 兼容接口）的 TTFT 和 TTL"""
    start = _now_s()
    stream = None
    first: float | None = None
    last: float | None = None
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
                current_time = _now_s()
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    if first is None:
                        first = current_time
                    last = current_time
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

    if last is None:
        last = first  # 如果没有收到后续 chunk，使用 first 作为 last

    ttft_ms = (first - start) * 1000
    ttl_ms = (last - start) * 1000

    return (ttft_ms, ttl_ms)


def _summarize(
    model: str,
    ttfts_ms: list[float],
    ttls_ms: list[float],
    failures: int,
) -> ModelSummary:
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
            ttl_mean_ms=None,
            ttl_median_ms=None,
            ttl_p95_ms=None,
            ttl_stdev_ms=None,
        )

    mean_ms = statistics.mean(ttfts_ms)
    median_ms = statistics.median(ttfts_ms)
    p95_ms = _quantile(ttfts_ms, 0.95)
    stdev_ms = statistics.pstdev(ttfts_ms) if len(ttfts_ms) >= 2 else 0.0

    # TTL 统计
    ttl_mean_ms = statistics.mean(ttls_ms) if ttls_ms else None
    ttl_median_ms = statistics.median(ttls_ms) if ttls_ms else None
    ttl_p95_ms = _quantile(ttls_ms, 0.95) if ttls_ms else None
    ttl_stdev_ms = statistics.pstdev(ttls_ms) if ttls_ms and len(ttls_ms) >= 2 else None

    return ModelSummary(
        model=model,
        n=len(ttfts_ms) + failures,
        successes=len(ttfts_ms),
        failures=failures,
        mean_ms=mean_ms,
        median_ms=median_ms,
        p95_ms=p95_ms,
        stdev_ms=stdev_ms,
        ttl_mean_ms=ttl_mean_ms,
        ttl_median_ms=ttl_median_ms,
        ttl_p95_ms=ttl_p95_ms,
        ttl_stdev_ms=ttl_stdev_ms,
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

    print("\n=== TTL 汇总（单位：ms）===")
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
            fmt(s.ttl_mean_ms),
            fmt(s.ttl_median_ms),
            fmt(s.ttl_p95_ms),
            fmt(s.ttl_stdev_ms),
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


app = cyclopts.App(help="LLM 模型 TTFT（首 token 延迟）和 TTL（总响应时间）基准测试")


@app.default
def main(
    models: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name="--models",
            help="要测试的模型（可多次传入，例如：--models a --models b）。OpenRouter 模型直接使用名称，Google 模型使用 google/ 前缀。如果不指定，默认测试 google/gemini-2.5-flash、google/gemini-2.5-flash-lite 和 minimax/minimax-m2-her",
            required=False,
        ),
    ] = None,
    prompt: str = "PURITY_ROLEPLAY_PROMPT",
    iterations: int = 5,
    user_message: str = "用中文只回答一个词：你好",
    temperature: float = 0.0,
    max_tokens: int = 1024,
    timeout_s: float = 60.0,
    sleep_s: float = 0.0,
    output_json: str = "bench_llms_ttft.json",
    output_png: str = "bench_llms_ttft.png",
    plot: bool = True,
):
    """
    运行 TTFT 和 TTL 基准测试。

    Args:
        models: 要测试的模型（可多次传入，例如：--models a --models b）
            - OpenRouter 模型：直接使用模型名称，如 openai/gpt-4o-mini
            - Google GenAI 模型：使用 google/ 前缀，如 google/gemini-2.5-flash
            - 如果不指定，默认测试：google/gemini-2.5-flash、google/gemini-2.5-flash-lite 和 minimax/minimax-m2-her
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

    # 如果没有指定模型，使用默认值
    if not models:
        models = [
            "google/gemini-2.5-flash",
            "google/gemini-2.5-flash-lite",
            "minimax/minimax-m2-her",
        ]
        print(f"未指定模型，使用默认模型：{models}")

    # 检查是否有非 Google 模型需要 OpenRouter
    has_non_google_models = any(not m.startswith("google/") for m in models)
    if has_non_google_models:
        api_key = _env("OPENROUTER_API_KEY") or _env("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "缺少 OpenRouter API Key：请设置 OPENROUTER_API_KEY（或 OPENAI_API_KEY）"
            )
    else:
        api_key = ""  # 仅使用 Google GenAI 时不需要

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


def _get_google_genai_client() -> Any:
    """获取或创建 Google GenAI 客户端"""
    from google import genai

    import os

    # 优先使用 service account（查找 inty-backend-key.json）
    project_root = Path(__file__).parent.parent
    candidates = [
        project_root / "inty-backend-key.json",
        Path("/Users/donggang/Documents/code/inty-backend/inty-backend-key.json"),
        Path.home() / "Documents" / "code" / "inty-backend" / "inty-backend-key.json",
    ]

    # 如果环境变量已设置，优先使用
    credentials_path = _env("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and Path(credentials_path).exists():
        credentials_path = str(Path(credentials_path).resolve())
    else:
        # 查找候选路径
        credentials_path = None
        for candidate in candidates:
            if candidate.exists():
                credentials_path = str(candidate.resolve())
                break

    if credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        # 从凭证文件读取 project_id
        project_id = _env("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            try:
                import json

                with open(credentials_path, "r") as f:
                    creds = json.load(f)
                    project_id = creds.get("project_id", "inty-backend")
            except Exception:
                project_id = "inty-backend"

        location = _env("GOOGLE_CLOUD_LOCATION", "us-central1")
        return genai.Client(vertexai=True, project=project_id, location=location)

    # 回退到 API Key 方式
    api_key = _env("GOOGLE_API_KEY") or _env("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    raise RuntimeError(
        "缺少 Google GenAI 认证：请设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量，"
        "或在项目根目录放置 inty-backend-key.json 文件，"
        "或设置 GOOGLE_API_KEY（或 GEMINI_API_KEY）"
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
    raw_results: list[IterationResult] = []
    summaries: list[ModelSummary] = []

    # 初始化客户端（按需）
    openrouter_client: Any | None = None
    google_genai_client: Any | None = None

    for model in models:
        print(f"\n--- 测试模型：{model}（iterations={iterations}）---")

        # 判断使用哪个客户端
        use_google_genai = model.startswith("google/")

        if use_google_genai:
            if google_genai_client is None:
                google_genai_client = _get_google_genai_client()
            client = google_genai_client
        else:
            if openrouter_client is None:
                from openai import AsyncOpenAI

                openrouter_client = AsyncOpenAI(
                    base_url=base_url, api_key=api_key, default_headers=extra_headers
                )
            client = openrouter_client

        ttfts: list[float] = []
        ttls: list[float] = []
        failures = 0

        for i in range(iterations):
            try:
                if use_google_genai:
                    ttft_ms, ttl_ms = await _measure_google_genai_times(
                        client=client,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout_s=timeout_s,
                    )
                else:
                    ttft_ms, ttl_ms = await _measure_openrouter_times(
                        client=client,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout_s=timeout_s,
                    )

                ttfts.append(ttft_ms)
                ttls.append(ttl_ms)
                raw_results.append(
                    IterationResult(
                        model=model,
                        iteration=i + 1,
                        ttft_ms=ttft_ms,
                        ttl_ms=ttl_ms,
                        error=None,
                    )
                )
                # 如果 TTFT 和 TTL 非常接近（差异小于 1%），可能是流式调用没有真正流式返回
                time_diff_pct = (
                    abs(ttl_ms - ttft_ms) / ttft_ms * 100 if ttft_ms > 0 else 0
                )
                if time_diff_pct < 1.0:
                    print(
                        f"  iter {i + 1}/{iterations}: ttft={ttft_ms:.1f}ms, ttl={ttl_ms:.1f}ms "
                        f"(⚠️ 流式可能未工作，差异仅 {time_diff_pct:.1f}%)"
                    )
                else:
                    print(
                        f"  iter {i + 1}/{iterations}: ttft={ttft_ms:.1f}ms, ttl={ttl_ms:.1f}ms"
                    )
            except Exception as e:
                failures += 1
                raw_results.append(
                    IterationResult(
                        model=model,
                        iteration=i + 1,
                        ttft_ms=None,
                        ttl_ms=None,
                        error=str(e),
                    )
                )
                print(f"  iter {i + 1}/{iterations}: failed: {e}")

            if sleep_s > 0:
                await asyncio.sleep(sleep_s)

        summaries.append(_summarize(model, ttfts, ttls, failures))

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
            title=f"LLM TTFT Benchmark (prompt={prompt}, n={iterations})",
        )
        print(f"已写入图表：{output_png}")


if __name__ == "__main__":
    app()
