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
    steps: tuple[StackStep, ...]
    probes: tuple[Probe, ...]


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
    model_id: str
    config_yaml: str
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
    steps = tuple(_load_step(step) for step in raw["steps"])
    probes = tuple(
        Probe(
            id=str(probe["id"]),
            question=str(probe["question"]),
            expect_contains=tuple(str(x) for x in probe["expect_contains"]),
        )
        for probe in raw["probes"]
    )
    return Experiment(
        name=str(raw["name"]),
        description=str(raw["description"]),
        layout_zone=str(raw["layout_zone"]),
        steps=steps,
        probes=probes,
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


def print_experiment_stack(experiment: Experiment) -> None:
    base = _base_engine(experiment)
    print(f"\n## {experiment.name} [{experiment.layout_zone}]")
    print(experiment.description)
    for probe in experiment.probes:
        probe_stack = base.clone()
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


async def run_experiment(experiment: Experiment, llm_client) -> RunArtifact:
    base = _base_engine(experiment)
    model_id = llm_client.async_llm_client.resolve_model("chat").id_on_provider
    results: list[ProbeResult] = []
    for probe in experiment.probes:
        probe_stack = base.clone()
        probe_stack.push(role="user", content=probe.question)
        messages = probe_stack.messages()
        _assert_mid_transcript_shape(experiment, messages)
        t0 = time.perf_counter()
        response = await llm_client.async_llm_client.chat_completion(
            messages=probe_stack.to_messages(),
            tools=[],
            tool_choice=None,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        content = response.choices[0].message.content
        assert isinstance(content, str)
        passed = all(
            expected.lower() in content.lower()
            for expected in probe.expect_contains
        )
        result = ProbeResult(
            probe_id=probe.id,
            messages=messages,
            response=content,
            passed=passed,
            latency_ms=latency_ms,
        )
        results.append(result)
        print(f"\n## {experiment.name} :: {probe.id}")
        print(f"passed={passed} latency_ms={latency_ms:.0f}")
        print(content)
    return RunArtifact(
        experiment_name=experiment.name,
        layout_zone=experiment.layout_zone,
        model_id=model_id,
        config_yaml=_config_yaml_path(),
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
