"""
最简化命令行工具：按模型前缀选择 OpenAI 或 Anthropic API。
openai/* 使用 OpenAI SDK，anthropic/* 使用 Anthropic SDK。
"""

import json
import logging
import secrets
import time
from pathlib import Path

import cyclopts
from anthropic import Anthropic
from openai import OpenAI

log = logging.getLogger(__name__)


def _to_jsonable(obj):
    """Convert OpenAI response (and nested) to JSON-serializable dict."""
    if obj is None:
        return None
    model_dump = getattr(obj, "model_dump", None)
    if model_dump is not None:
        try:
            return model_dump(mode="json")
        except TypeError:
            log.debug(
                "model_dump(mode='json') unsupported; retrying without mode",
                exc_info=True,
            )
            try:
                return model_dump()
            except Exception as exc:
                log.debug("model_dump fallback failed: %s", exc, exc_info=True)
        except Exception as exc:
            log.debug("model_dump(mode='json') failed: %s", exc, exc_info=True)
    dict_fn = getattr(obj, "dict", None)
    if dict_fn is not None and callable(dict_fn):
        try:
            return dict_fn()
        except Exception as exc:
            log.debug("dict() serialization fallback failed: %s", exc, exc_info=True)
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


def _provider_and_model(model: str) -> tuple[str, str]:
    """Return (provider, model_id). provider 为 'openai' 或 'anthropic'，model_id 为去掉前缀的模型名。"""
    if model.startswith("openai/"):
        return "openai", model[7:]
    if model.startswith("anthropic/"):
        return "anthropic", model[10:]
    return "openai", model


def _extract_content_openai(response) -> str | None:
    if response.choices is not None and len(response.choices) > 0:
        return response.choices[0].message.content
    return None


def _extract_content_anthropic(response) -> str | None:
    if not getattr(response, "content", None):
        return None
    parts = response.content
    if not isinstance(parts, list):
        return str(parts)
    chunks = []
    for p in parts:
        if hasattr(p, "text"):
            chunks.append(p.text or "")
        elif isinstance(p, dict):
            chunks.append(p.get("text", p.get("content", "")))
    return "".join(chunks) if chunks else None


def _single_call_openai(
    client: OpenAI, model_id: str, message: str
) -> tuple[str | None, dict]:
    """OpenAI 单次调用；返回 (content, stats)。"""
    start = time.perf_counter()
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    request_payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 32,
    }
    stats = {
        "start_iso": start_iso,
        "latency_ms": None,
        "success": False,
        "error": None,
        "input_message_length": len(message),
        "output_content_length": None,
        "output_content_preview": None,
        "usage_prompt_tokens": None,
        "usage_completion_tokens": None,
        "usage_total_tokens": None,
        "model": model_id,
        "request": request_payload,
        "response": None,
    }
    log.info("openai request model=%r message_len=%d", model_id, len(message))
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": message}],
            max_tokens=32,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        content = _extract_content_openai(response)
        stats["latency_ms"] = round(latency_ms, 2)
        stats["success"] = True
        stats["response"] = _to_jsonable(response)
        if content is not None:
            stats["output_content_length"] = len(content)
            stats["output_content_preview"] = (
                content[:200] if len(content) > 200 else content
            )
            log.info(
                "openai response success latency_ms=%.2f content_len=%d",
                latency_ms,
                len(content),
            )
        else:
            raw = _to_jsonable(response)
            log.warning(
                "openai response success but content is None; response keys=%s choices_len=%s",
                (
                    list(raw.keys())
                    if isinstance(raw, dict)
                    else type(raw).__name__
                ),
                len(raw.get("choices", [])) if isinstance(raw, dict) else None,
            )
            if isinstance(raw, dict) and "choices" in raw:
                c0 = raw["choices"][0] if raw["choices"] else None
                log.warning(
                    "openai choices[0]=%s",
                    json.dumps(c0, ensure_ascii=False)[:500] if c0 else None,
                )
        usage = getattr(response, "usage", None)
        if usage is not None:
            stats["usage_prompt_tokens"] = getattr(usage, "prompt_tokens", None)
            stats["usage_completion_tokens"] = getattr(
                usage, "completion_tokens", None
            )
            stats["usage_total_tokens"] = getattr(usage, "total_tokens", None)
        return content, stats
    except Exception as e:
        stats["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        stats["error"] = f"{type(e).__name__}: {e}"
        stats["response"] = None
        log.exception("openai request failed: %s", e)
        return None, stats


def _single_call_anthropic(
    client: Anthropic, model_id: str, message: str
) -> tuple[str | None, dict]:
    """Anthropic 单次调用；返回 (content, stats)。"""
    start = time.perf_counter()
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    request_payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 32,
    }
    stats = {
        "start_iso": start_iso,
        "latency_ms": None,
        "success": False,
        "error": None,
        "input_message_length": len(message),
        "output_content_length": None,
        "output_content_preview": None,
        "usage_prompt_tokens": None,
        "usage_completion_tokens": None,
        "usage_total_tokens": None,
        "model": model_id,
        "request": request_payload,
        "response": None,
    }
    log.info(
        "anthropic request model=%r message_len=%d", model_id, len(message)
    )
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=32,
            messages=[{"role": "user", "content": message}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        content = _extract_content_anthropic(response)
        stats["latency_ms"] = round(latency_ms, 2)
        stats["success"] = True
        stats["response"] = _to_jsonable(response)
        if content is not None:
            stats["output_content_length"] = len(content)
            stats["output_content_preview"] = (
                content[:200] if len(content) > 200 else content
            )
            log.info(
                "anthropic response success latency_ms=%.2f content_len=%d",
                latency_ms,
                len(content),
            )
        else:
            raw = _to_jsonable(response)
            log.warning(
                "anthropic response success but content is None; response keys=%s content=%s",
                (
                    list(raw.keys())
                    if isinstance(raw, dict)
                    else type(raw).__name__
                ),
                (
                    str(raw.get("content", ""))[:300]
                    if isinstance(raw, dict)
                    else None
                ),
            )
        usage = getattr(response, "usage", None)
        if usage is not None:
            inp = getattr(usage, "input_tokens", None)
            out = getattr(usage, "output_tokens", None)
            stats["usage_prompt_tokens"] = inp
            stats["usage_completion_tokens"] = out
            stats["usage_total_tokens"] = (
                (inp + out) if (inp is not None and out is not None) else None
            )
        return content, stats
    except Exception as e:
        stats["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        stats["error"] = f"{type(e).__name__}: {e}"
        stats["response"] = None
        log.exception("anthropic request failed: %s", e)
        return None, stats


def _stats_filename(
    model: str, count: int, cycle: float, random_seed: bool
) -> str:
    """Filename from params: model, count, cycle, random_seed + ISO timestamp for uniqueness."""
    safe_model = model.replace("/", "-")
    iso = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    return (
        f"{safe_model}_count{count}_cycle{cycle}_seed{random_seed}_{iso}.json"
    )


def _write_stats_file(out_path: Path, all_stats: list) -> None:
    """Write invocations and (partial or final) summary to out_path."""
    latencies = [
        s["latency_ms"] for s in all_stats if s["latency_ms"] is not None
    ]
    summary = {
        "total_invocations": len(all_stats),
        "success_count": sum(1 for s in all_stats if s["success"]),
        "failure_count": sum(1 for s in all_stats if not s["success"]),
        "avg_latency_ms": (
            round(sum(latencies) / len(latencies), 2) if latencies else None
        ),
        "min_latency_ms": min(latencies) if latencies else None,
        "max_latency_ms": max(latencies) if latencies else None,
    }
    out_path.write_text(
        json.dumps(
            {"invocations": all_stats, "summary": summary},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def llm_call(
    api_endpoint: str,
    api_key: str,
    model: str,
    message: str,
    count: int = 1,
    cycle: float = 0,
    output_dir: str | None = None,
    random_seed: bool = False,
):
    """
    按模型前缀选择 API：openai/* 用 OpenAI SDK，anthropic/* 用 Anthropic SDK。
    count: 重复调用次数；cycle: 每次间隔秒数；output_dir: 将每次调用的统计写入该目录下以参数命名的 json 文件；
    random_seed: 为 True 时在 message 后追加 8 字节随机串以避免缓存。
    输出文件在每次调用后立即更新，便于监控进度。
    """
    provider, model_id = _provider_and_model(model)
    log.info(
        "provider=%s model_id=%r model_for_request will be set below",
        provider,
        model_id,
    )
    if provider == "openai":
        client = OpenAI(api_key=api_key, base_url=api_endpoint)
        single_call = lambda c, mid, msg: _single_call_openai(c, mid, msg)
        model_for_request = model_id
        log.info(
            "using OpenAI client base_url=%s model_for_request=%r",
            api_endpoint,
            model_for_request,
        )
    else:
        base = (api_endpoint or "").strip() or None
        client = Anthropic(api_key=api_key, base_url=base)
        single_call = lambda c, mid, msg: _single_call_anthropic(c, mid, msg)
        # 代理（如 LiteLLM）的 model_name 常带前缀（如 anthropic/claude-opus-4），需传完整 model 才能匹配
        model_for_request = model if base else model_id
        log.info(
            "using Anthropic client base_url=%s model_for_request=%r",
            base,
            model_for_request,
        )

    all_stats = []
    last_content = None
    out_path = (
        Path(output_dir) / _stats_filename(model, count, cycle, random_seed)
        if output_dir
        else None
    )
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        msg = message
        random_suffix = None
        if random_seed:
            random_suffix = secrets.token_hex(8)
            msg = f"{message}\n\n[{random_suffix}]"
        content, stats = single_call(client, model_for_request, msg)
        stats["index"] = i + 1
        if random_suffix is not None:
            stats["random_suffix"] = random_suffix
        all_stats.append(stats)
        last_content = content
        log.info(
            "call %d/%d success=%s content_len=%s latency_ms=%s",
            i + 1,
            count,
            stats["success"],
            len(content) if content is not None else None,
            stats.get("latency_ms"),
        )
        if out_path is not None:
            _write_stats_file(out_path, all_stats)
        if content is not None:
            print(content)
        elif not stats["success"]:
            print(stats["error"])
        elif stats["success"]:
            log.warning("success but no content printed (content was None)")
        if i < count - 1 and cycle > 0:
            time.sleep(cycle)

    return last_content


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s %(message)s"
    )
    cyclopts.run(llm_call)
