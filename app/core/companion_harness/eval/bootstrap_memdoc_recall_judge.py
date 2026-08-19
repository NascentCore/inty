"""LLM-as-judge scoring for Bootstrap MemDoc golden-fact chat recall."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.core.companion_harness.eval.bootstrap_memdoc_eval_models import (
    BootstrapMemDocEvalScenario,
    ChatTurnRecord,
    GoldenFactsRecallScore,
    ProbeRecallResult,
    aggregate_probe_recall_score,
    _probe_expect_markers,
    golden_fact_chat_markers,
)
from app.core.companion_harness.llm.chat_completions import (
    create_chat_completion_sync,
)
from app.core.companion_harness.providers.openai_compatible_clients import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.utils.models_catalog import resolve_chat_model_to_id

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_MARKER_SEMANTIC: dict[str, str] = {
    "user_address": "how the user asked to be addressed (nickname)",
    "assistant_name": "the name or persona the user chose for the companion",
    "relationship_framing": (
        "the companionship style the user wanted (e.g. Doraemon-like easy chat partner)"
    ),
}


class RecallMarkerJudgment(BaseModel):
    """Semantic recall verdict for one golden marker on one probe turn."""

    name: str = Field(description="GoldenFacts marker field name")
    recalled: bool = Field(
        description="True when assistant reply semantically recalls this fact"
    )
    reason: str = Field(description="Brief justification for the verdict")


class RecallProbeJudgment(BaseModel):
    """Structured LLM judge output for one probe turn."""

    markers: tuple[RecallMarkerJudgment, ...] = Field(
        description="One judgment per expected marker"
    )


def openrouter_judge_client() -> Any:
    """Sync OpenRouter client for eval judge calls (LangSmith-wrapped)."""

    cfg = global_config_loaded_from_config_yaml
    api_key = cfg.agent.api_key
    assert api_key != ""
    return get_openai_compatible_sync_client(
        OpenAICompatibleClientOptions(
            base_url=_OPENROUTER_BASE_URL,
            api_key=api_key,
            wrap_langsmith=True,
            chat_name="bootstrap_memdoc_recall_judge",
        )
    )


def default_recall_judge_model() -> str:
    """Chat model used for semantic recall judging."""

    cfg = global_config_loaded_from_config_yaml
    return resolve_chat_model_to_id(cfg.agent.sub_user_chat_model)


def _judge_response_format() -> dict[str, Any]:
    inner = RecallProbeJudgment.model_json_schema()
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "recall_probe_judgment",
            "strict": True,
            "schema": inner,
        },
    }


def _bootstrap_context_lines(scenario: BootstrapMemDocEvalScenario) -> str:
    lines = [f"- {turn}" for turn in scenario.user_turns]
    return "\n".join(lines)


def _golden_facts_lines(golden_marker_names: tuple[str, ...]) -> str:
    markers = _MARKER_SEMANTIC
    lines: list[str] = []
    for name in golden_marker_names:
        lines.append(f"- {name}: {markers[name]}")
    return "\n".join(lines)


def _build_judge_messages(
    *,
    scenario: BootstrapMemDocEvalScenario,
    record: ChatTurnRecord,
    expect_markers: tuple[str, ...],
) -> list[dict[str, str]]:
    values = golden_fact_chat_markers(scenario.golden_facts)
    fact_values = "\n".join(
        f"- {name}: {values[name]!r}" for name in expect_markers
    )
    system = (
        "You judge whether an AI companion's visible reply correctly recalls "
        "bootstrap onboarding facts when the user asks a recall question.\n"
        "Use semantic matching, not keyword substring search.\n"
        "Accept synonyms, paraphrases, and equivalent names "
        "(e.g. 哆啦 and 多啦; 哆啦A梦和大雄 for Doraemon-like companionship).\n"
        "Mark recalled=true only when the reply demonstrates the fact was remembered, "
        "not when the assistant says it forgot or has no name yet."
    )
    user = (
        f"Bootstrap user turns:\n{_bootstrap_context_lines(scenario)}\n\n"
        f"Golden facts to check ({record.phase.value}):\n{fact_values}\n\n"
        f"Markers to judge:\n{_golden_facts_lines(expect_markers)}\n\n"
        f"User recall question:\n{record.user_text}\n\n"
        f"Assistant visible reply:\n{record.assistant_text}\n\n"
        "Return one judgment per marker name listed above."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _parse_judge_content(content: str) -> RecallProbeJudgment:
    raw = json.loads(content)
    return RecallProbeJudgment.model_validate(raw)


def _completion_text(completion: Any) -> str:
    choice = completion.choices[0]
    message = choice.message
    text = getattr(message, "content", None)
    assert text is not None
    assert str(text).strip() != ""
    return str(text)


def llm_judge_probe_turn(
    *,
    client: Any,
    model: str,
    scenario: BootstrapMemDocEvalScenario,
    record: ChatTurnRecord,
    expect_markers: tuple[str, ...],
) -> ProbeRecallResult:
    """Run LLM judge for one probe turn; returns marker hits and reasons."""

    assert client is not None
    assert model != ""
    messages = _build_judge_messages(
        scenario=scenario,
        record=record,
        expect_markers=expect_markers,
    )
    completion = create_chat_completion_sync(
        client,
        model=model,
        messages_payload=messages,
        tools=[],
        response_format=_judge_response_format(),
        langsmith_extra={
            "metadata": {
                "eval_probe_id": record.probe_id,
                "eval_probe_phase": record.phase.value,
            },
        },
    )
    judgment = _parse_judge_content(_completion_text(completion))
    by_name = {item.name: item for item in judgment.markers}
    hits: dict[str, bool] = {}
    reasons: dict[str, str] = {}
    probe_hits = 0
    for name in expect_markers:
        item = by_name.get(name)
        assert item is not None, f"judge missing marker {name!r}"
        hits[name] = item.recalled
        reasons[name] = item.reason
        if item.recalled:
            probe_hits += 1
    ratio = probe_hits / len(expect_markers) if expect_markers else 0.0
    return ProbeRecallResult(
        probe_id=record.probe_id,
        phase=record.phase,
        marker_hits=hits,
        recall_ratio=ratio,
        judge_reasons=reasons,
    )


def llm_judge_golden_chat_recall(
    *,
    scenario: BootstrapMemDocEvalScenario,
    chat_records: tuple[ChatTurnRecord, ...],
    client: Any,
    model: str,
) -> GoldenFactsRecallScore:
    """Score chat recall using LLM semantic judge on each probe turn."""

    assert scenario is not None
    assert client is not None
    assert model != ""
    per_probe: list[ProbeRecallResult] = []

    for record in chat_records:
        expect = _probe_expect_markers(scenario, record.probe_id)
        per_probe.append(
            llm_judge_probe_turn(
                client=client,
                model=model,
                scenario=scenario,
                record=record,
                expect_markers=expect,
            )
        )

    return aggregate_probe_recall_score(
        per_probe=tuple(per_probe),
        marker_names=frozenset(golden_fact_chat_markers(scenario.golden_facts)),
    )
