#!/usr/bin/env python3
"""
大模型月度账单计算器（CLI）

能力：
- 手动输入多个模型的定价（每个模型必须有唯一标识）
- 计算时按流程执行：先输入用量数据，再选择 1 个或多个模型
- 输出每个模型的分项费用（输入/输出/缓存读/缓存写）与总费用

示例（全交互）：
    export PYTHONPATH=.
    python tools/scripts/calculate_llm_monthly_bill.py

示例（半交互，先通过参数传定价）：
    export PYTHONPATH=.
    python tools/scripts/calculate_llm_monthly_bill.py \
      --model-pricing "gpt-4o-mini,0.15,0.60,0.075,0.30" \
      --model-pricing "gemini-2.5-flash,0.10,0.40,0.05,0.20"

示例（全参数）：
    export PYTHONPATH=.
    python tools/scripts/calculate_llm_monthly_bill.py \
      --model-pricing "gpt-4o-mini,0.15,0.60,0.075,0.30" \
      --model-pricing "gemini-2.5-flash,0.10,0.40,0.05,0.20" \
      --usage-input-tokens 2000000 \
      --usage-output-tokens 1000000 \
      --usage-cache-read-tokens 500000 \
      --usage-cache-write-tokens 200000 \
      --select-model gpt-4o-mini \
      --select-model gemini-2.5-flash
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated

import cyclopts
from loguru import logger

TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class UsageData:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int


@dataclass(frozen=True)
class ModelPricing:
    model_id: str
    input_per_million_usd: float
    output_per_million_usd: float
    cache_read_per_million_usd: float
    cache_write_per_million_usd: float


@dataclass(frozen=True)
class ModelBill:
    model_id: str
    input_cost_usd: float
    output_cost_usd: float
    cache_read_cost_usd: float
    cache_write_cost_usd: float
    total_cost_usd: float


def _require_non_negative_int(value: int, field_name: str) -> int:
    if value < 0:
        raise ValueError(f"{field_name} 必须 >= 0，当前值: {value}")
    return value


def _require_non_negative_float(value: float, field_name: str) -> float:
    if value < 0:
        raise ValueError(f"{field_name} 必须 >= 0，当前值: {value}")
    return value


def parse_model_pricing(pricing_line: str) -> ModelPricing:
    """
    解析模型定价，支持两种格式：
    - model_id,input,output
    - model_id,input,output,cache_read,cache_write
    """
    parts = [x.strip() for x in pricing_line.split(",")]
    if len(parts) not in (3, 5):
        raise ValueError(
            "模型定价格式错误，应为：model_id,input,output 或 "
            "model_id,input,output,cache_read,cache_write"
        )

    model_id = parts[0]
    if not model_id:
        raise ValueError("model_id 不能为空")

    input_price = _require_non_negative_float(float(parts[1]), "input_per_million_usd")
    output_price = _require_non_negative_float(
        float(parts[2]), "output_per_million_usd"
    )
    if len(parts) == 3:
        cache_read_price = 0.0
        cache_write_price = 0.0
    else:
        cache_read_price = _require_non_negative_float(
            float(parts[3]), "cache_read_per_million_usd"
        )
        cache_write_price = _require_non_negative_float(
            float(parts[4]), "cache_write_per_million_usd"
        )

    return ModelPricing(
        model_id=model_id,
        input_per_million_usd=input_price,
        output_per_million_usd=output_price,
        cache_read_per_million_usd=cache_read_price,
        cache_write_per_million_usd=cache_write_price,
    )


def parse_model_pricings(pricing_lines: list[str]) -> dict[str, ModelPricing]:
    model_pricings: dict[str, ModelPricing] = {}
    for line in pricing_lines:
        pricing = parse_model_pricing(line)
        if pricing.model_id in model_pricings:
            raise ValueError(f"模型标识重复: {pricing.model_id}")
        model_pricings[pricing.model_id] = pricing
    return model_pricings


def calculate_bill_for_model(usage: UsageData, pricing: ModelPricing) -> ModelBill:
    input_cost = round(
        usage.input_tokens / TOKENS_PER_MILLION * pricing.input_per_million_usd, 6
    )
    output_cost = round(
        usage.output_tokens / TOKENS_PER_MILLION * pricing.output_per_million_usd, 6
    )
    cache_read_cost = round(
        usage.cache_read_tokens
        / TOKENS_PER_MILLION
        * pricing.cache_read_per_million_usd,
        6,
    )
    cache_write_cost = round(
        usage.cache_write_tokens
        / TOKENS_PER_MILLION
        * pricing.cache_write_per_million_usd,
        6,
    )
    total_cost = round(input_cost + output_cost + cache_read_cost + cache_write_cost, 6)
    return ModelBill(
        model_id=pricing.model_id,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        cache_read_cost_usd=cache_read_cost,
        cache_write_cost_usd=cache_write_cost,
        total_cost_usd=total_cost,
    )


def calculate_bills(
    usage: UsageData,
    selected_model_ids: list[str],
    model_pricings: dict[str, ModelPricing],
) -> list[ModelBill]:
    bills: list[ModelBill] = []
    for model_id in selected_model_ids:
        pricing = model_pricings.get(model_id)
        if pricing is None:
            available = ", ".join(sorted(model_pricings.keys()))
            raise ValueError(
                f"未找到模型标识: {model_id}。可选模型: {available if available else '(无)'}"
            )
        bills.append(calculate_bill_for_model(usage, pricing))
    return bills


def _normalize_selected_models(raw_items: list[str]) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        for piece in item.split(","):
            model_id = piece.strip()
            if not model_id:
                continue
            if model_id not in seen:
                selected.append(model_id)
                seen.add(model_id)
    if not selected:
        raise ValueError("至少选择 1 个模型")
    return selected


def _prompt_non_negative_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return _require_non_negative_int(int(raw), "token 用量")
        except ValueError:
            print("输入无效，请输入 >= 0 的整数。")


def _collect_pricing_interactively() -> dict[str, ModelPricing]:
    print("请输入模型定价（支持多条），格式：")
    print("  model_id,input,output 或 model_id,input,output,cache_read,cache_write")
    print("示例：gpt-4o-mini,0.15,0.60,0.075,0.30")
    print("输入空行结束。")
    model_pricings: dict[str, ModelPricing] = {}
    while True:
        line = input("定价> ").strip()
        if not line:
            if model_pricings:
                break
            print("至少输入 1 条模型定价。")
            continue
        try:
            pricing = parse_model_pricing(line)
        except ValueError as error:
            print(f"定价解析失败: {error}")
            continue
        if pricing.model_id in model_pricings:
            print(f"模型标识重复: {pricing.model_id}")
            continue
        model_pricings[pricing.model_id] = pricing
        logger.debug("已录入模型定价: {}", pricing.model_id)
    return model_pricings


def _collect_usage_interactively() -> UsageData:
    print("\n步骤 1/2：输入月度用量数据（token）")
    input_tokens = _prompt_non_negative_int("输入 token 用量: ")
    output_tokens = _prompt_non_negative_int("输出 token 用量: ")
    cache_read_tokens = _prompt_non_negative_int("缓存读 token 用量（无则填 0）: ")
    cache_write_tokens = _prompt_non_negative_int("缓存写 token 用量（无则填 0）: ")
    usage = UsageData(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
    )
    logger.debug("用量已录入: {}", usage)
    return usage


def _collect_models_interactively(model_pricings: dict[str, ModelPricing]) -> list[str]:
    print("\n步骤 2/2：选择参与计算的模型（可多选）")
    print("可选模型：")
    for model_id in sorted(model_pricings.keys()):
        print(f"  - {model_id}")
    print("请输入模型标识，多个用英文逗号分隔。")
    while True:
        raw = input("模型> ").strip()
        try:
            selected = _normalize_selected_models([raw])
            missing = [
                model_id for model_id in selected if model_id not in model_pricings
            ]
            if missing:
                print(f"以下模型不存在: {', '.join(missing)}")
                continue
            logger.debug("已选择模型: {}", selected)
            return selected
        except ValueError as error:
            print(error)


def _format_usd(value: float) -> str:
    return f"${value:.6f}"


def print_report(usage: UsageData, bills: list[ModelBill]) -> None:
    print("\n=== 月度账单明细 ===")
    print("用量（token）:")
    print(f"  输入: {usage.input_tokens}")
    print(f"  输出: {usage.output_tokens}")
    print(f"  缓存读: {usage.cache_read_tokens}")
    print(f"  缓存写: {usage.cache_write_tokens}")
    print("")
    overall_total = 0.0
    for bill in bills:
        overall_total += bill.total_cost_usd
        print(f"模型: {bill.model_id}")
        print(f"  输入费用: {_format_usd(bill.input_cost_usd)}")
        print(f"  输出费用: {_format_usd(bill.output_cost_usd)}")
        print(f"  缓存读费用: {_format_usd(bill.cache_read_cost_usd)}")
        print(f"  缓存写费用: {_format_usd(bill.cache_write_cost_usd)}")
        print(f"  总费用: {_format_usd(bill.total_cost_usd)}")
        print("")
    print(f"所选模型总计: {_format_usd(overall_total)}")


def _usage_from_args_or_prompt(
    usage_input_tokens: int | None,
    usage_output_tokens: int | None,
    usage_cache_read_tokens: int | None,
    usage_cache_write_tokens: int | None,
) -> UsageData:
    # 关键步骤说明：按需求，计算流程固定为“先输入用量，再选择模型”。
    input_tokens = (
        _require_non_negative_int(usage_input_tokens, "usage_input_tokens")
        if usage_input_tokens is not None
        else _prompt_non_negative_int("输入 token 用量: ")
    )
    output_tokens = (
        _require_non_negative_int(usage_output_tokens, "usage_output_tokens")
        if usage_output_tokens is not None
        else _prompt_non_negative_int("输出 token 用量: ")
    )
    cache_read_tokens = (
        _require_non_negative_int(usage_cache_read_tokens, "usage_cache_read_tokens")
        if usage_cache_read_tokens is not None
        else _prompt_non_negative_int("缓存读 token 用量（无则填 0）: ")
    )
    cache_write_tokens = (
        _require_non_negative_int(usage_cache_write_tokens, "usage_cache_write_tokens")
        if usage_cache_write_tokens is not None
        else _prompt_non_negative_int("缓存写 token 用量（无则填 0）: ")
    )
    return UsageData(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
    )


def _selected_models_from_args_or_prompt(
    select_model: list[str] | None, model_pricings: dict[str, ModelPricing]
) -> list[str]:
    if select_model:
        selected = _normalize_selected_models(select_model)
        missing = [model_id for model_id in selected if model_id not in model_pricings]
        if missing:
            raise ValueError(f"以下模型不存在: {', '.join(missing)}")
        return selected
    return _collect_models_interactively(model_pricings)


def _write_output_json(
    output_json: str,
    usage: UsageData,
    bills: list[ModelBill],
) -> None:
    payload = {
        "usage": asdict(usage),
        "bills": [asdict(item) for item in bills],
        "selected_models_total_usd": round(
            sum(item.total_cost_usd for item in bills), 6
        ),
    }
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已写入计算结果: {output_path}")


app = cyclopts.App(help="按模型定价计算月度账单。支持多模型比较。")


@app.default
def main(
    model_pricing: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name="--model-pricing",
            help=(
                "模型定价，可重复。格式："
                "model_id,input,output 或 model_id,input,output,cache_read,cache_write"
            ),
            required=False,
        ),
    ] = None,
    usage_input_tokens: Annotated[
        int | None,
        cyclopts.Parameter(name="--usage-input-tokens", help="月输入 token 用量"),
    ] = None,
    usage_output_tokens: Annotated[
        int | None,
        cyclopts.Parameter(name="--usage-output-tokens", help="月输出 token 用量"),
    ] = None,
    usage_cache_read_tokens: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--usage-cache-read-tokens", help="月缓存读 token 用量"
        ),
    ] = None,
    usage_cache_write_tokens: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--usage-cache-write-tokens", help="月缓存写 token 用量"
        ),
    ] = None,
    select_model: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            name="--select-model",
            help="参与计算的模型标识，可重复传入；单次也支持英文逗号分隔。",
            required=False,
        ),
    ] = None,
    output_json: Annotated[
        str | None,
        cyclopts.Parameter(name="--output-json", help="将计算结果写入 JSON 文件"),
    ] = None,
) -> None:
    logger.debug("开始执行月度账单计算")
    model_pricings = (
        parse_model_pricings(model_pricing)
        if model_pricing
        else _collect_pricing_interactively()
    )
    if not model_pricings:
        raise ValueError("未录入任何模型定价")

    if (
        usage_input_tokens is None
        and usage_output_tokens is None
        and usage_cache_read_tokens is None
        and usage_cache_write_tokens is None
        and select_model is None
    ):
        usage = _collect_usage_interactively()
        selected_model_ids = _collect_models_interactively(model_pricings)
    else:
        print("\n步骤 1/2：输入月度用量数据（token）")
        usage = _usage_from_args_or_prompt(
            usage_input_tokens=usage_input_tokens,
            usage_output_tokens=usage_output_tokens,
            usage_cache_read_tokens=usage_cache_read_tokens,
            usage_cache_write_tokens=usage_cache_write_tokens,
        )
        print("\n步骤 2/2：选择参与计算的模型（可多选）")
        selected_model_ids = _selected_models_from_args_or_prompt(
            select_model=select_model, model_pricings=model_pricings
        )

    bills = calculate_bills(
        usage=usage,
        selected_model_ids=selected_model_ids,
        model_pricings=model_pricings,
    )
    print_report(usage=usage, bills=bills)

    if output_json is not None:
        _write_output_json(output_json=output_json, usage=usage, bills=bills)


if __name__ == "__main__":
    app()
