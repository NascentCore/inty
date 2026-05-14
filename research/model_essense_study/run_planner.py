from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.utils.models_catalog import CHAT_TEXT_MODELS, DataModality
from research.model_essense_study.config import ModelEssenseStudyConfig


@dataclass(frozen=True)
class ModelRunPlan:
    model_id: str
    request_count: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    input_price_per_1m_usd: float
    output_price_per_1m_usd: float
    price_source: str
    estimated_cost_usd: float


def _text_price_per_1m(model_id: str) -> tuple[float, float] | None:
    for model in CHAT_TEXT_MODELS:
        if model.id_on_provider != model_id:
            continue
        input_price = None
        output_price = None
        for item in model.pricing.inputs:
            if item.modality == DataModality.TEXT:
                input_price = item.price
                break
        for item in model.pricing.outputs:
            if item.modality == DataModality.TEXT:
                output_price = item.price
                break
        if input_price is None or output_price is None:
            return None
        return (float(input_price), float(output_price))
    return None


def build_run_plan(
    *,
    config: ModelEssenseStudyConfig,
    avg_input_tokens: int | None = None,
    avg_output_tokens: int | None = None,
    requests_per_minute: int | None = None,
) -> dict[str, Any]:
    avg_input = avg_input_tokens or config.planning.avg_input_tokens
    avg_output = avg_output_tokens or config.planning.avg_output_tokens
    rpm = requests_per_minute or config.planning.requests_per_minute

    persona_count = config.experiment.persona_count
    stimulus_count = config.experiment.stimulus_count
    repeats = config.experiment.repeats_per_cell
    model_ids = list(config.experiment.model_ids)
    requests_per_model = persona_count * stimulus_count * repeats

    model_plans: list[ModelRunPlan] = []
    for model_id in model_ids:
        pricing = _text_price_per_1m(model_id)
        if pricing:
            input_price, output_price = pricing
            source = "models_catalog.chat_text_pricing"
        else:
            input_price = config.planning.fallback_input_price_per_1m_usd
            output_price = config.planning.fallback_output_price_per_1m_usd
            source = "planning_fallback"

        request_count = requests_per_model
        input_tokens = request_count * avg_input
        output_tokens = request_count * avg_output
        cost = (input_tokens / 1_000_000.0) * input_price + (
            output_tokens / 1_000_000.0
        ) * output_price
        model_plans.append(
            ModelRunPlan(
                model_id=model_id,
                request_count=request_count,
                estimated_input_tokens=input_tokens,
                estimated_output_tokens=output_tokens,
                input_price_per_1m_usd=input_price,
                output_price_per_1m_usd=output_price,
                price_source=source,
                estimated_cost_usd=round(cost, 6),
            )
        )

    total_requests = requests_per_model * len(model_ids)
    total_input_tokens = sum(item.estimated_input_tokens for item in model_plans)
    total_output_tokens = sum(item.estimated_output_tokens for item in model_plans)
    total_cost = round(sum(item.estimated_cost_usd for item in model_plans), 6)
    estimated_hours = round(total_requests / max(rpm, 1) / 60.0, 4)
    budget_cap = config.planning.budget_cap_usd
    execution_window = config.planning.execution_window_hours

    return {
        "generated_at": config.load_time_utc_iso,
        "repeat_semantics": config.planning.repeat_semantics,
        "assumptions": {
            "avg_input_tokens": avg_input,
            "avg_output_tokens": avg_output,
            "requests_per_minute": rpm,
            "budget_cap_usd": budget_cap,
            "execution_window_hours": execution_window,
        },
        "scale": {
            "model_count": len(model_ids),
            "persona_count": persona_count,
            "stimulus_count": stimulus_count,
            "repeats_per_cell": repeats,
            "requests_per_model": requests_per_model,
            "total_requests": total_requests,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        "cost_estimate": {
            "total_estimated_cost_usd": total_cost,
            "within_budget_cap": total_cost <= budget_cap,
        },
        "execution_estimate": {
            "estimated_hours": estimated_hours,
            "within_execution_window": estimated_hours <= execution_window,
        },
        "models": [asdict(item) for item in model_plans],
    }
