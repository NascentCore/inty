#!/usr/bin/env python3
"""Minimal research prototype for a piano-style agentic model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import cyclopts
import yaml
from openai import OpenAI


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

app = cyclopts.App(
    name="piano-agentic-model",
    help="Minimal prototype showing modular agentic behavior.",
)


@dataclass(frozen=True)
class ToyTask:
    task_id: str
    description: str
    state_actions: dict[str, dict[str, str]]
    start_state: str
    goal_state: str
    required_subgoal_sequence: list[str] = field(default_factory=list)

    @property
    def state_names(self) -> list[str]:
        return list(self.state_actions.keys())

    def allowed_actions(self, state: str) -> list[str]:
        return list(self.state_actions.get(state, {}).keys())

    def transition(self, state: str, action: str) -> str | None:
        return self.state_actions.get(state, {}).get(action)


@dataclass
class StepTrace:
    step_idx: int
    state_before: str
    active_subgoal: str
    actor_proposals: list[str]
    valid_actions_after_monitor: list[str]
    chosen_action: str | None
    state_after: str | None
    invalid_action: bool
    note: str


@dataclass
class EpisodeResult:
    name: str
    success: bool
    reached_goal: bool
    invalid_action_count: int
    steps_executed: int
    traces: list[StepTrace] = field(default_factory=list)


def _load_openrouter_api_key(config_yaml_path: Path) -> str:
    payload = yaml.safe_load(config_yaml_path.read_text(encoding="utf-8")) or {}
    agent_section = payload.get("agent")
    if not isinstance(agent_section, dict):
        raise ValueError("Missing 'agent' section in config yaml.")
    api_key = agent_section.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("Missing agent.api_key in config yaml.")
    return api_key.strip()


def _extract_json_object(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f"Model output does not contain a JSON object: {raw_text}")
    return json.loads(text[start : end + 1])


def _create_openrouter_client(api_key: str) -> OpenAI:
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://inty-research.local",
            "X-Title": "piano-agentic-model-prototype",
        },
    )


def _call_json_llm(
    client: OpenAI,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> dict:
    resp = client.chat.completions.create(
        model=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content if resp.choices else ""
    if content is None:
        raise ValueError("Model returned an empty content payload.")
    return _extract_json_object(content)


def _task_decomposer(
    client: OpenAI,
    model_id: str,
    task: ToyTask,
) -> list[str]:
    payload = _call_json_llm(
        client=client,
        model_id=model_id,
        system_prompt=(
            "You are the TaskDecomposer module in a modular planning architecture. "
            "Break goals into short state-based subgoals."
        ),
        user_prompt=(
            "Return JSON with field `subgoals` as an ordered array of state names.\n"
            f"Allowed states: {task.state_names}\n"
            f"Start state: {task.start_state}\n"
            f"Goal state: {task.goal_state}\n"
            f"Required checkpoints in order: {task.required_subgoal_sequence}\n"
            "Rules:\n"
            "- subgoals must be from allowed states\n"
            "- final subgoal must equal goal state\n"
            "- do not include the start state as first subgoal\n"
            "- include all required checkpoints in order when provided\n"
        ),
        temperature=0,
        max_tokens=200,
    )
    subgoals = payload.get("subgoals")
    if not isinstance(subgoals, list) or not subgoals:
        raise ValueError(f"TaskDecomposer returned invalid subgoals: {payload}")
    for goal in subgoals:
        if goal not in task.state_names:
            raise ValueError(f"TaskDecomposer used unknown state: {goal}")
    if subgoals[-1] != task.goal_state:
        raise ValueError("TaskDecomposer final subgoal is not goal state.")
    if task.required_subgoal_sequence:
        seq_idx = 0
        for goal in subgoals:
            if seq_idx < len(task.required_subgoal_sequence) and goal == task.required_subgoal_sequence[seq_idx]:
                seq_idx += 1
        if seq_idx != len(task.required_subgoal_sequence):
            raise ValueError(
                "TaskDecomposer missing required checkpoint sequence: "
                f"{task.required_subgoal_sequence}, got={subgoals}"
            )
    return [str(item) for item in subgoals]


def _actor_propose_actions(
    client: OpenAI,
    model_id: str,
    state: str,
    subgoal: str,
    allowed_actions: list[str],
    trace_history: list[StepTrace],
    temperature: float,
) -> list[str]:
    short_history = [
        {
            "step_idx": t.step_idx,
            "state_before": t.state_before,
            "chosen_action": t.chosen_action,
            "state_after": t.state_after,
        }
        for t in trace_history[-3:]
    ]
    payload = _call_json_llm(
        client=client,
        model_id=model_id,
        system_prompt=(
            "You are the Actor module. Propose candidate actions for the current state."
        ),
        user_prompt=(
            "Return JSON with field `actions` as an array of exactly 3 action strings.\n"
            "Hard constraints:\n"
            "1) action[0] MUST be a hypothetical shortcut action NOT in allowed_actions.\n"
            "2) action[1] and action[2] MUST be from allowed_actions.\n"
            "3) Keep actions short and exact.\n"
            f"Current state: {state}\n"
            f"Current subgoal: {subgoal}\n"
            f"Allowed actions: {allowed_actions}\n"
            f"Recent trace: {json.dumps(short_history, ensure_ascii=False)}"
        ),
        temperature=temperature,
        max_tokens=250,
    )
    actions = payload.get("actions")
    if not isinstance(actions, list) or len(actions) != 3:
        raise ValueError(f"Actor returned invalid actions payload: {payload}")
    action_list = [str(item).strip() for item in actions]
    # Enforce actor contract without failing hard:
    # - baseline stress-test requires one invalid first proposal
    # - monitor/evaluator should still receive valid alternatives
    if not action_list[0] or action_list[0] in allowed_actions:
        invalid_seed = f"invalid_shortcut_from_{state}"
        action_list[0] = invalid_seed if invalid_seed not in allowed_actions else "invalid_shortcut"
    if action_list[1] not in allowed_actions:
        action_list[1] = allowed_actions[0]
    if action_list[2] not in allowed_actions:
        fallback_idx = 1 if len(allowed_actions) > 1 else 0
        action_list[2] = allowed_actions[fallback_idx]
    return action_list


def _evaluator_choose_action(
    client: OpenAI,
    model_id: str,
    state: str,
    subgoal: str,
    candidates: list[str],
    predicted_next_states: dict[str, str],
) -> str:
    payload = _call_json_llm(
        client=client,
        model_id=model_id,
        system_prompt=(
            "You are the Evaluator module. Choose the best action toward the subgoal."
        ),
        user_prompt=(
            "Return JSON with keys: `selected_action`, `reason`.\n"
            f"Current state: {state}\n"
            f"Current subgoal: {subgoal}\n"
            f"Candidates: {candidates}\n"
            f"Predicted next states by action: {predicted_next_states}\n"
            "Choose exactly one action from candidates."
        ),
        temperature=0,
        max_tokens=180,
    )
    selected_action = payload.get("selected_action")
    if not isinstance(selected_action, str):
        raise ValueError(f"Evaluator returned invalid selected_action: {payload}")
    selected_action = selected_action.strip()
    if selected_action not in candidates:
        raise ValueError(f"Evaluator selected action outside candidates: {payload}")
    return selected_action


def _orchestrator_should_advance_subgoal(
    client: OpenAI,
    model_id: str,
    current_state: str,
    active_subgoal: str,
    goal_state: str,
) -> bool:
    payload = _call_json_llm(
        client=client,
        model_id=model_id,
        system_prompt=(
            "You are the Orchestrator module. Decide whether to advance to the next subgoal."
        ),
        user_prompt=(
            "Return JSON with key `advance_subgoal` as true/false.\n"
            f"Current state: {current_state}\n"
            f"Active subgoal: {active_subgoal}\n"
            f"Final goal: {goal_state}\n"
            "Advance only when active subgoal is already achieved, or final goal is already achieved."
        ),
        temperature=0,
        max_tokens=120,
    )
    advance_subgoal = payload.get("advance_subgoal")
    if not isinstance(advance_subgoal, bool):
        raise ValueError(f"Orchestrator returned invalid payload: {payload}")
    if current_state == goal_state or current_state == active_subgoal:
        return True
    return advance_subgoal


def _run_episode(
    name: str,
    client: OpenAI,
    model_id: str,
    task: ToyTask,
    subgoals: list[str],
    max_steps: int,
    use_monitor: bool,
    actor_temperature: float,
) -> EpisodeResult:
    traces: list[StepTrace] = []
    state = task.start_state
    invalid_action_count = 0
    subgoal_idx = 0

    for step_idx in range(1, max_steps + 1):
        if state == task.goal_state:
            break
        if subgoal_idx >= len(subgoals):
            break

        active_subgoal = subgoals[subgoal_idx]
        allowed = task.allowed_actions(state)
        if not allowed:
            traces.append(
                StepTrace(
                    step_idx=step_idx,
                    state_before=state,
                    active_subgoal=active_subgoal,
                    actor_proposals=[],
                    valid_actions_after_monitor=[],
                    chosen_action=None,
                    state_after=None,
                    invalid_action=True,
                    note="No available actions in this state.",
                )
            )
            invalid_action_count += 1
            break

        proposals = _actor_propose_actions(
            client=client,
            model_id=model_id,
            state=state,
            subgoal=active_subgoal,
            allowed_actions=allowed,
            trace_history=traces,
            temperature=actor_temperature,
        )

        if use_monitor:
            valid_after_monitor = [a for a in proposals if a in allowed]
            if not valid_after_monitor:
                traces.append(
                    StepTrace(
                        step_idx=step_idx,
                        state_before=state,
                        active_subgoal=active_subgoal,
                        actor_proposals=proposals,
                        valid_actions_after_monitor=[],
                        chosen_action=None,
                        state_after=None,
                        invalid_action=True,
                        note="Monitor rejected all actions.",
                    )
                )
                invalid_action_count += 1
                break
            predicted_states = {a: task.transition(state, a) or "INVALID" for a in valid_after_monitor}
            chosen_action = _evaluator_choose_action(
                client=client,
                model_id=model_id,
                state=state,
                subgoal=active_subgoal,
                candidates=valid_after_monitor,
                predicted_next_states={k: v for k, v in predicted_states.items() if v != "INVALID"},
            )
        else:
            valid_after_monitor = [proposals[0]]
            chosen_action = proposals[0]

        state_before = state
        next_state = task.transition(state_before, chosen_action)
        invalid_action = next_state is None
        if invalid_action:
            invalid_action_count += 1
            traces.append(
                StepTrace(
                    step_idx=step_idx,
                    state_before=state_before,
                    active_subgoal=active_subgoal,
                    actor_proposals=proposals,
                    valid_actions_after_monitor=valid_after_monitor,
                    chosen_action=chosen_action,
                    state_after=None,
                    invalid_action=True,
                    note="Chosen action is invalid in environment.",
                )
            )
            break

        state = next_state
        if _orchestrator_should_advance_subgoal(
            client=client,
            model_id=model_id,
            current_state=state,
            active_subgoal=active_subgoal,
            goal_state=task.goal_state,
        ):
            subgoal_idx += 1
        traces.append(
            StepTrace(
                step_idx=step_idx,
                state_before=state_before,
                active_subgoal=active_subgoal,
                actor_proposals=proposals,
                valid_actions_after_monitor=valid_after_monitor,
                chosen_action=chosen_action,
                state_after=state,
                invalid_action=False,
                note="Step executed.",
            )
        )

    reached_goal = state == task.goal_state
    return EpisodeResult(
        name=name,
        success=reached_goal and invalid_action_count == 0,
        reached_goal=reached_goal,
        invalid_action_count=invalid_action_count,
        steps_executed=len(traces),
        traces=traces,
    )


def _build_simple_task() -> ToyTask:
    return ToyTask(
        task_id="simple_bridge",
        description=(
            "Simple 4-state navigation with one reliable path and one looping detour."
        ),
        state_actions={
            "A": {"safe_bridge": "B", "risky_tunnel": "C"},
            "B": {"finish": "D", "retreat": "A"},
            "C": {"loop": "C", "recover": "A"},
            "D": {},
        },
        start_state="A",
        goal_state="D",
    )


def _build_complex_task() -> ToyTask:
    return ToyTask(
        task_id="complex_supply_chain",
        description=(
            "Multi-stage planning with mandatory checkpoints: gather credentials, "
            "unlock secure transfer, and complete audited delivery without falling into loops."
        ),
        state_actions={
            "Dock": {"collect_badge": "BadgeRoom", "unsafe_shortcut": "IncidentLoop"},
            "BadgeRoom": {"get_keycard": "ControlHub", "wander": "Dock"},
            "ControlHub": {"request_manifest": "ManifestDesk", "wrong_lift": "IncidentLoop"},
            "ManifestDesk": {"verify_manifest": "SecureGate", "return_hub": "ControlHub"},
            "SecureGate": {"authorize_transfer": "TransferBay", "panic_reset": "Dock"},
            "TransferBay": {"handoff": "AuditDesk", "misroute": "IncidentLoop"},
            "AuditDesk": {"finalize_delivery": "Completed", "missing_form": "ManifestDesk"},
            "IncidentLoop": {"recover_protocol": "Dock", "loop": "IncidentLoop"},
            "Completed": {},
        },
        start_state="Dock",
        goal_state="Completed",
        required_subgoal_sequence=["BadgeRoom", "SecureGate", "TransferBay", "AuditDesk", "Completed"],
    )


def _build_university_logic_proof_task() -> ToyTask:
    return ToyTask(
        task_id="logic_proof_university",
        description=(
            "University-level first-order logic proof: from forall x (H(x)->M(x)), "
            "forall x (M(x)->L(x)), exists x H(x), prove exists x L(x). "
            "The task requires witness introduction, universal instantiation, "
            "two implication eliminations, and existential introduction."
        ),
        state_actions={
            "Premises": {
                "pick_witness_a_from_exists_H": "WitnessChosen",
                "assert_goal_without_proof": "LogicTrap",
            },
            "WitnessChosen": {
                "derive_Ha": "HaDerived",
                "drop_witness_context": "LogicTrap",
            },
            "HaDerived": {
                "instantiate_H_implies_M_at_a": "HtoMAtADerived",
                "apply_MP_too_early": "LogicTrap",
            },
            "HtoMAtADerived": {
                "modus_ponens_to_get_Ma": "MaDerived",
                "wrong_quantifier_jump": "LogicTrap",
            },
            "MaDerived": {
                "instantiate_M_implies_L_at_a": "MtoLAtADerived",
                "existential_intro_too_early": "LogicTrap",
            },
            "MtoLAtADerived": {
                "modus_ponens_to_get_La": "LaDerived",
                "circular_reasoning": "LogicTrap",
            },
            "LaDerived": {
                "existential_intro_to_exists_L": "Conclusion",
                "lose_witness_scope": "LogicTrap",
            },
            "LogicTrap": {
                "restart_proof": "Premises",
                "loop_confusion": "LogicTrap",
            },
            "Conclusion": {},
        },
        start_state="Premises",
        goal_state="Conclusion",
        required_subgoal_sequence=[
            "WitnessChosen",
            "HaDerived",
            "MaDerived",
            "LaDerived",
            "Conclusion",
        ],
    )


def _build_task_by_id(task_id: str) -> ToyTask:
    normalized = task_id.strip().lower()
    if normalized == "simple_bridge":
        return _build_simple_task()
    if normalized == "complex_supply_chain":
        return _build_complex_task()
    if normalized == "logic_proof_university":
        return _build_university_logic_proof_task()
    raise ValueError(
        "Unknown task_id. Supported values: simple_bridge, complex_supply_chain, "
        "logic_proof_university."
    )


def _episode_to_dict(episode: EpisodeResult) -> dict:
    return {
        "name": episode.name,
        "success": episode.success,
        "reached_goal": episode.reached_goal,
        "invalid_action_count": episode.invalid_action_count,
        "steps_executed": episode.steps_executed,
        "traces": [asdict(t) for t in episode.traces],
    }


def _write_markdown_report(path: Path, result_payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    episodes = result_payload["episodes"]
    lines = [
        "# PIANO Agentic Model Experiment",
        "",
        f"- Run time (UTC): {result_payload['run_time_utc']}",
        f"- Model: {result_payload['model_id']}",
        f"- Config source: `{result_payload['config_yaml_path']}`",
        f"- Task: `{result_payload['task']['task_id']}`",
        f"- Task description: {result_payload['task']['description']}",
        f"- Required checkpoints: {result_payload['task']['required_subgoal_sequence']}",
        "",
        "## Summary",
    ]
    for ep in episodes:
        lines.append(
            f"- **{ep['name']}**: success={ep['success']}, reached_goal={ep['reached_goal']}, "
            f"invalid_actions={ep['invalid_action_count']}, steps={ep['steps_executed']}"
        )
    lines.extend(["", "## Key Behavior", "- Baseline uses first actor proposal directly (no monitor)."])
    lines.append("- PIANO run filters actions with monitor then selects via evaluator.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.command()
def run(
    config_yaml_path: Annotated[
        str,
        cyclopts.Parameter(
            name="--config-yaml-path",
            help="Path to config yaml containing agent.api_key.",
        ),
    ] = "devops/config.yaml.dev",
    model_id: Annotated[
        str,
        cyclopts.Parameter(
            name="--model-id",
            help="OpenRouter model id.",
        ),
    ] = "google/gemini-2.5-flash-lite",
    task_id: Annotated[
        str,
        cyclopts.Parameter(
            name="--task-id",
            help=(
                "Task id: simple_bridge, complex_supply_chain, or "
                "logic_proof_university."
            ),
        ),
    ] = "simple_bridge",
    max_steps: Annotated[
        int,
        cyclopts.Parameter(
            name="--max-steps",
            help="Maximum rollout steps per condition.",
        ),
    ] = 4,
    actor_temperature: Annotated[
        float,
        cyclopts.Parameter(
            name="--actor-temperature",
            help="Actor module temperature.",
        ),
    ] = 0.3,
    output_json_path: Annotated[
        str,
        cyclopts.Parameter(
            name="--output-json-path",
            help="Where to write experiment JSON.",
        ),
    ] = "researches/piano_agentic_model/results/latest_run.json",
    output_markdown_path: Annotated[
        str,
        cyclopts.Parameter(
            name="--output-markdown-path",
            help="Where to write experiment markdown summary.",
        ),
    ] = "researches/piano_agentic_model/docs/LAST_EXPERIMENT.md",
) -> None:
    """
    Execute a minimal side-by-side experiment (no-monitor baseline vs PIANO).
    """
    # Research workflow summary:
    # 1) Load OpenRouter key from devops config.
    # 2) Run identical toy task under baseline and modular conditions.
    # 3) Persist trace artifacts for behavior inspection and reproducibility.
    config_path = Path(config_yaml_path).resolve()
    api_key = _load_openrouter_api_key(config_path)
    client = _create_openrouter_client(api_key)
    task = _build_task_by_id(task_id)
    subgoals = _task_decomposer(client=client, model_id=model_id, task=task)

    baseline = _run_episode(
        name="baseline_no_monitor",
        client=client,
        model_id=model_id,
        task=task,
        subgoals=subgoals,
        max_steps=max_steps,
        use_monitor=False,
        actor_temperature=actor_temperature,
    )
    piano = _run_episode(
        name="piano_with_monitor_and_evaluator",
        client=client,
        model_id=model_id,
        task=task,
        subgoals=subgoals,
        max_steps=max_steps,
        use_monitor=True,
        actor_temperature=actor_temperature,
    )

    result_payload = {
        "run_time_utc": datetime.now(UTC).isoformat(),
        "model_id": model_id,
        "config_yaml_path": str(config_path),
        "subgoals": subgoals,
        "task": {
            "task_id": task.task_id,
            "description": task.description,
            "start_state": task.start_state,
            "goal_state": task.goal_state,
            "required_subgoal_sequence": task.required_subgoal_sequence,
            "state_actions": task.state_actions,
        },
        "episodes": [_episode_to_dict(baseline), _episode_to_dict(piano)],
    }

    output_json = Path(output_json_path).resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_md = Path(output_markdown_path).resolve()
    _write_markdown_report(output_md, result_payload)

    redacted = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "****"
    print(f"[PIANO] API key loaded from {config_path} ({redacted})")
    print(f"[PIANO] Task: {task.task_id} ({task.description})")
    print(f"[PIANO] Subgoals: {subgoals}")
    for episode in result_payload["episodes"]:
        print(
            "[PIANO] "
            f"{episode['name']} => success={episode['success']} "
            f"reached_goal={episode['reached_goal']} "
            f"invalid_actions={episode['invalid_action_count']} "
            f"steps={episode['steps_executed']}"
        )
    print(f"[PIANO] Wrote JSON: {output_json}")
    print(f"[PIANO] Wrote Markdown: {output_md}")


@app.default
def _default_help() -> None:
    print(app.help_print())


if __name__ == "__main__":
    app()
