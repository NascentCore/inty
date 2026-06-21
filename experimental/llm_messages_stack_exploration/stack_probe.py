"""Generated entirely by the Cursor agent as an experimental LLM message stack probe."""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cyclopts
import yaml

ROLE_VALUES = {"system", "user", "assistant"}
EXPERIMENTS_DIR = Path("experimental/llm_messages_stack_exploration/experiments")
RUNS_DIR = Path("experimental/llm_messages_stack_exploration/runs")


@dataclass(frozen=True)
class StackMessage:
    """One OpenAI wire message on the probe stack before an LLM call."""

    role: str
    content: str


@dataclass(frozen=True)
class StackStepPush:
    """Append one message onto the stack."""

    role: str
    content: str


@dataclass(frozen=True)
class StackStepPop:
    """Remove the top stack entry (LIFO)."""


StackStep = StackStepPush | StackStepPop


@dataclass(frozen=True)
class Probe:
    """Question appended as a tail user message; response checked by substring."""

    id: str
    question: str
    expect_contains: tuple[str, ...]


@dataclass(frozen=True)
class Experiment:
    """Named YAML experiment: build stack via steps, then run probes."""

    name: str
    description: str
    layout_zone: str
    kind: str
    temperature: float | None
    steps: tuple[StackStep, ...]
    probes: tuple[Probe, ...]
    system_content: str
    user_first: str
    user_second: str
    expect_first: str
    expect_second: str


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of one probe LLM call."""

    probe_id: str
    messages: tuple[StackMessage, ...]
    response: str
    passed: bool
    latency_ms: float


@dataclass(frozen=True)
class RunArtifact:
    """JSON-serializable run record written to runs/."""

    experiment_name: str
    layout_zone: str
    kind: str
    model_id: str
    config_yaml: str
    temperature: float | None
    probe_results: tuple[ProbeResult, ...]


class StackEngine:
    """Mutable LIFO message stack used to materialize one probe prompt."""

    def __init__(self) -> None:
        self._stack: list[StackMessage] = []

    def apply_step(self, step: StackStep) -> None:
        match step:
            case StackStepPush(role=role, content=content):
                self.push(role=role, content=content)
            case StackStepPop():
                self.pop()

    def push(self, *, role: str, content: str) -> None:
        assert role in ROLE_VALUES
        assert content
        self._stack.append(StackMessage(role=role, content=content))

    def pop(self) -> StackMessage:
        assert self._stack
        return self._stack.pop()

    def clone(self) -> StackEngine:
        out = StackEngine()
        out._stack = list(self._stack)
        return out

    def messages(self) -> tuple[StackMessage, ...]:
        return tuple(self._stack)

    def to_messages(self) -> list[dict[str, str]]:
        return [asdict(message) for message in self._stack]


def _load_step(raw: dict[str, Any]) -> StackStep:
    if "push" in raw:
        body = raw["push"]
        role = str(body["role"])
        content = str(body["content"])
        assert role in ROLE_VALUES
        assert content
        return StackStepPush(role=role, content=content)
    assert raw["pop"] is True
    return StackStepPop()


def load_experiment(path: Path) -> Experiment:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = tuple(_load_step(step) for step in raw.get("steps", []))
    probes = tuple(
        Probe(
            id=str(probe["id"]),
            question=str(probe.get("question", "")),
            expect_contains=tuple(str(x) for x in probe["expect_contains"]),
        )
        for probe in raw.get("probes", [])
    )
    temperature_raw = raw.get("temperature")
    temperature = float(temperature_raw) if temperature_raw is not None else None
    return Experiment(
        name=str(raw["name"]),
        description=str(raw["description"]),
        layout_zone=str(raw["layout_zone"]),
        kind=str(raw.get("kind", "stack_probes")),
        temperature=temperature,
        steps=steps,
        probes=probes,
        system_content=str(raw.get("system_content", "")),
        user_first=str(raw.get("user_first", "")),
        user_second=str(raw.get("user_second", "")),
        expect_first=str(raw.get("expect_first", "")),
        expect_second=str(raw.get("expect_second", "")),
    )


def _experiment_paths(experiment: str) -> tuple[Path, ...]:
    if experiment == "all":
        return tuple(sorted(EXPERIMENTS_DIR.glob("*.yaml")))
    stem = experiment.removesuffix(".yaml")
    direct = EXPERIMENTS_DIR / f"{stem}.yaml"
    if direct.exists():
        return (direct,)
    for candidate in sorted(EXPERIMENTS_DIR.glob("*.yaml")):
        if candidate.name.endswith(f"_{stem}.yaml"):
            return (candidate,)
        if load_experiment(candidate).name == stem:
            return (candidate,)
    raise AssertionError(f"experiment not found: {experiment}")


def _base_engine(experiment: Experiment) -> StackEngine:
    engine = StackEngine()
    for step in experiment.steps:
        engine.apply_step(step)
    return engine


def _assert_mid_transcript_shape(
    experiment: Experiment, messages: tuple[StackMessage, ...]
) -> None:
    if experiment.layout_zone != "mid_transcript":
        return
    assistant_indexes = [
        i for i, message in enumerate(messages) if message.role == "assistant"
    ]
    assert assistant_indexes
    last_assistant = assistant_indexes[-1]
    assert messages[-1].role == "user"
    assert any(
        message.role == "system"
        for message in messages[last_assistant + 1 : -1]
    )


def _passed(content: str, expect_contains: tuple[str, ...]) -> bool:
    return all(expected.lower() in content.lower() for expected in expect_contains)


def print_experiment_stack(experiment: Experiment) -> None:
    if experiment.kind == "two_user_comparison":
        print(f"\n## {experiment.name} [{experiment.layout_zone}]")
        print(experiment.description)
        print("\n### alternating wire (turn 1)")
        print(
            json.dumps(
                [
                    {"role": "system", "content": experiment.system_content},
                    {"role": "user", "content": experiment.user_first},
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        print("\n### alternating wire (turn 2 adds assistant + second user)")
        print(
            json.dumps(
                [
                    {"role": "system", "content": experiment.system_content},
                    {"role": "user", "content": experiment.user_first},
                    {"role": "assistant", "content": "<turn-1-response>"},
                    {"role": "user", "content": experiment.user_second},
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        print("\n### successive wire (single call)")
        print(
            json.dumps(
                [
                    {"role": "system", "content": experiment.system_content},
                    {"role": "user", "content": experiment.user_first},
                    {"role": "user", "content": experiment.user_second},
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    base = _base_engine(experiment)
    print(f"\n## {experiment.name} [{experiment.layout_zone}]")
    print(experiment.description)
    for probe in experiment.probes:
        probe_stack = base.clone()
        if probe.question:
            probe_stack.push(role="user", content=probe.question)
        messages = probe_stack.messages()
        _assert_mid_transcript_shape(experiment, messages)
        print(f"\n### probe={probe.id}")
        print(
            json.dumps(
                [asdict(message) for message in messages],
                indent=2,
                ensure_ascii=False,
            )
        )


def _config_yaml_path() -> str:
    value = os.environ.get("INTY_CONFIG_YAML", "").strip()
    if value:
        return value
    return "config.yaml"


def build_llm_client():
    from app.core.companion_harness.companion.manager_factory import (
        companion_tool_model_api_id,
    )
    from app.core.config import global_config_loaded_from_config_yaml as cfg
    from app.core.llms.client import CompanionLLMConfig, LlmClient
    from app.utils.models_catalog import resolve_chat_text_model

    chat_id = cfg.agent.free_user_chat_model.strip()
    assert chat_id
    chat_m = resolve_chat_text_model(chat_id)
    tool_m = resolve_chat_text_model(
        companion_tool_model_api_id(chat_m.id_on_provider)
    )
    llm_cfg = CompanionLLMConfig(
        api_key=os.environ["OPENROUTER_API_KEY"],
        api_base=cfg.agent.chat_llm_base_url or cfg.agent.base_url,
        default_model=chat_m,
        chat_model=chat_m,
        tool_model=tool_m,
    )
    return LlmClient(llm_cfg)


async def _chat_completion(
    llm_client,
    messages: list[dict[str, str]],
    temperature: float | None,
) -> tuple[str, float]:
    async_llm = llm_client.async_llm_client
    chat_model = async_llm.resolve_model("chat")
    api_model = chat_model.id_on_provider
    create_kw: dict[str, Any] = {
        "model": api_model,
        "messages": messages,
    }
    if temperature is not None:
        create_kw["temperature"] = temperature
    t0 = time.perf_counter()
    raw = await async_llm._async_client.chat.completions.create(**create_kw)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    content = raw.choices[0].message.content
    assert isinstance(content, str)
    return content, latency_ms


def _wire_messages(rows: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"role": role, "content": content} for role, content in rows]


async def run_two_user_comparison(
    experiment: Experiment, llm_client
) -> RunArtifact:
    assert experiment.system_content
    assert experiment.user_first
    assert experiment.user_second
    assert experiment.expect_first
    assert experiment.expect_second
    temperature = experiment.temperature
    model_id = llm_client.async_llm_client.resolve_model("chat").id_on_provider
    results: list[ProbeResult] = []

    alternating_turn_1_messages = _wire_messages(
        [
            ("system", experiment.system_content),
            ("user", experiment.user_first),
        ]
    )
    alternating_turn_1_response, latency_1 = await _chat_completion(
        llm_client,
        alternating_turn_1_messages,
        temperature,
    )
    passed_turn_1 = _passed(alternating_turn_1_response, (experiment.expect_first,))
    results.append(
        ProbeResult(
            probe_id="alternating_turn_1",
            messages=tuple(
                StackMessage(role=m["role"], content=m["content"])
                for m in alternating_turn_1_messages
            ),
            response=alternating_turn_1_response,
            passed=passed_turn_1,
            latency_ms=latency_1,
        )
    )
    print("\n## alternating_turn_1")
    print(f"passed={passed_turn_1} latency_ms={latency_1:.0f}")
    print(alternating_turn_1_response)

    alternating_turn_2_messages = _wire_messages(
        [
            ("system", experiment.system_content),
            ("user", experiment.user_first),
            ("assistant", alternating_turn_1_response),
            ("user", experiment.user_second),
        ]
    )
    alternating_turn_2_response, latency_2 = await _chat_completion(
        llm_client,
        alternating_turn_2_messages,
        temperature,
    )
    passed_turn_2 = _passed(
        alternating_turn_2_response, (experiment.expect_second,)
    )
    results.append(
        ProbeResult(
            probe_id="alternating_turn_2",
            messages=tuple(
                StackMessage(role=m["role"], content=m["content"])
                for m in alternating_turn_2_messages
            ),
            response=alternating_turn_2_response,
            passed=passed_turn_2,
            latency_ms=latency_2,
        )
    )
    print("\n## alternating_turn_2")
    print(f"passed={passed_turn_2} latency_ms={latency_2:.0f}")
    print(alternating_turn_2_response)

    successive_messages = _wire_messages(
        [
            ("system", experiment.system_content),
            ("user", experiment.user_first),
            ("user", experiment.user_second),
        ]
    )
    successive_response, latency_s = await _chat_completion(
        llm_client,
        successive_messages,
        temperature,
    )
    passed_successive = _passed(
        successive_response,
        (experiment.expect_first, experiment.expect_second),
    )
    results.append(
        ProbeResult(
            probe_id="successive_single_turn",
            messages=tuple(
                StackMessage(role=m["role"], content=m["content"])
                for m in successive_messages
            ),
            response=successive_response,
            passed=passed_successive,
            latency_ms=latency_s,
        )
    )
    print("\n## successive_single_turn")
    print(f"passed={passed_successive} latency_ms={latency_s:.0f}")
    print(successive_response)

    combined_alternating = (
        f"{alternating_turn_1_response}\n{alternating_turn_2_response}"
    )
    passed_equivalent = _passed(
        successive_response,
        (experiment.expect_first, experiment.expect_second),
    ) and _passed(combined_alternating, (experiment.expect_first, experiment.expect_second))
    results.append(
        ProbeResult(
            probe_id="successive_covers_both_questions",
            messages=tuple(
                StackMessage(role=m["role"], content=m["content"])
                for m in successive_messages
            ),
            response=successive_response,
            passed=passed_equivalent,
            latency_ms=latency_s,
        )
    )
    print("\n## successive_covers_both_questions")
    print(f"passed={passed_equivalent}")
    print(
        "combined_alternating="
        + json.dumps(combined_alternating, ensure_ascii=False)
    )

    return RunArtifact(
        experiment_name=experiment.name,
        layout_zone=experiment.layout_zone,
        kind=experiment.kind,
        model_id=model_id,
        config_yaml=_config_yaml_path(),
        temperature=temperature,
        probe_results=tuple(results),
    )


async def run_experiment(experiment: Experiment, llm_client) -> RunArtifact:
    if experiment.kind == "two_user_comparison":
        return await run_two_user_comparison(experiment, llm_client)
    base = _base_engine(experiment)
    model_id = llm_client.async_llm_client.resolve_model("chat").id_on_provider
    results: list[ProbeResult] = []
    for probe in experiment.probes:
        probe_stack = base.clone()
        if probe.question:
            probe_stack.push(role="user", content=probe.question)
        messages = probe_stack.messages()
        _assert_mid_transcript_shape(experiment, messages)
        response, latency_ms = await _chat_completion(
            llm_client,
            probe_stack.to_messages(),
            experiment.temperature,
        )
        passed = _passed(response, probe.expect_contains)
        result = ProbeResult(
            probe_id=probe.id,
            messages=messages,
            response=response,
            passed=passed,
            latency_ms=latency_ms,
        )
        results.append(result)
        print(f"\n## {experiment.name} :: {probe.id}")
        print(f"passed={passed} latency_ms={latency_ms:.0f}")
        print(response)
    return RunArtifact(
        experiment_name=experiment.name,
        layout_zone=experiment.layout_zone,
        kind=experiment.kind,
        model_id=model_id,
        config_yaml=_config_yaml_path(),
        temperature=experiment.temperature,
        probe_results=tuple(results),
    )


def _write_artifact(artifact: RunArtifact, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"{stamp}_{artifact.experiment_name}.json"
    path.write_text(
        json.dumps(asdict(artifact), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"wrote {path}")


async def _run_live(
    experiments: tuple[Experiment, ...], output_dir: Path
) -> None:
    llm_client = build_llm_client()
    for experiment in experiments:
        artifact = await run_experiment(experiment, llm_client)
        _write_artifact(artifact, output_dir)


def main(
    experiment: str = "all",
    print_stack_only: bool = False,
    output_dir: str = str(RUNS_DIR),
) -> None:
    """Run LLM message-stack experiments."""
    experiments = tuple(
        load_experiment(path) for path in _experiment_paths(experiment)
    )
    if print_stack_only:
        for loaded in experiments:
            print_experiment_stack(loaded)
        return
    asyncio.run(_run_live(experiments, Path(output_dir)))


if __name__ == "__main__":
    cyclopts.run(main)
