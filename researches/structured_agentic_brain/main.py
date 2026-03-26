from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Generic, TypeVar

import cyclopts
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class ScenarioCase(BaseModel):
    case_id: str
    title: str
    user_message: str
    conversation_history: list[Message]
    episodic_memory: list[str]
    semantic_memory: list[str]


class RouteChannel(BaseModel):
    name: str
    priority: float = Field(ge=0.0, le=1.0)


class RouteDecision(BaseModel):
    channels: list[RouteChannel]
    reason: str


class UserStateEstimate(BaseModel):
    primary_emotion: str
    stress_level: float = Field(ge=0.0, le=1.0)
    loneliness_level: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]


class ThreatAssessment(BaseModel):
    level: str
    signals: list[str]
    recommended_policy: str


class MemoryEvidence(BaseModel):
    episodic_hits: list[str]
    semantic_hits: list[str]
    retrieval_reason: str


class PlanningOption(BaseModel):
    name: str
    rationale: str
    expected_gain: float = Field(ge=0.0, le=1.0)
    expected_risk: float = Field(ge=0.0, le=1.0)


class Plan(BaseModel):
    objective: str
    constraints: list[str]
    steps: list[str]
    options: list[PlanningOption]
    stop_condition: str


class ConflictReport(BaseModel):
    conflict_type: str
    severity: str
    impacted_modules: list[str]
    recommendation: str


class OptionScore(BaseModel):
    name: str
    utility: float
    risk_penalty: float


class ValueAssessment(BaseModel):
    scores: list[OptionScore]


class ActionDecision(BaseModel):
    selected_option: str
    rejected_options: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    tie_break_rationale: str


class FinalResponse(BaseModel):
    message: str
    tone: str
    suggested_followups: list[str]


class BrainTrace(BaseModel):
    case_id: str
    title: str
    route: RouteDecision
    insula_state: UserStateEstimate
    amygdala_threat: ThreatAssessment
    memory_evidence: MemoryEvidence
    plan: Plan
    conflict_report: ConflictReport
    value_assessment: ValueAssessment
    action_decision: ActionDecision
    final_response: FinalResponse


class BrainRunResult(BaseModel):
    model: str
    cases: list[BrainTrace]


TOut = TypeVar("TOut", bound=BaseModel)


class GeminiJsonClient:
    def __init__(self, model: str):
        load_dotenv()
        self.model = model
        self.client = self._build_client()

    def _build_client(self) -> genai.Client:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            return genai.Client(api_key=api_key)
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        return genai.Client(vertexai=True, project=project, location=location)

    def generate_structured(
        self, system_prompt: str, user_prompt: str, output_schema: type[TOut]
    ) -> TOut:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            )
        ]
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=output_schema,
            system_instruction=system_prompt,
            temperature=0.2,
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        raw_text = response.candidates[0].content.parts[0].text
        return output_schema.model_validate_json(raw_text)


InvariantFn = Callable[[TOut], None]


class PedanticUnit(Generic[TOut]):
    def __init__(
        self,
        name: str,
        client: GeminiJsonClient,
        output_schema: type[TOut],
        system_prompt: str,
        invariant: InvariantFn[TOut],
    ):
        self.name = name
        self.client = client
        self.output_schema = output_schema
        self.system_prompt = system_prompt
        self.invariant = invariant

    def run(self, user_prompt: str) -> TOut:
        result = self.client.generate_structured(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_schema=self.output_schema,
        )
        self.invariant(result)
        return result


def route_invariant(route: RouteDecision) -> None:
    assert len(route.channels) > 0
    for channel in route.channels:
        assert channel.name.strip() != ""


def insula_invariant(state: UserStateEstimate) -> None:
    assert state.primary_emotion.strip() != ""
    assert len(state.evidence) > 0


def amygdala_invariant(threat: ThreatAssessment) -> None:
    assert threat.level in {"low", "medium", "high"}
    assert threat.recommended_policy.strip() != ""


def plan_invariant(plan: Plan) -> None:
    assert plan.objective.strip() != ""
    assert len(plan.constraints) > 0
    assert len(plan.steps) >= 2
    assert len(plan.options) >= 2
    assert plan.stop_condition.strip() != ""


def conflict_invariant(report: ConflictReport) -> None:
    assert report.conflict_type.strip() != ""
    assert report.severity in {"low", "medium", "high"}
    assert len(report.impacted_modules) > 0


def final_response_invariant(response: FinalResponse) -> None:
    assert len(response.message.strip()) >= 40
    assert len(response.suggested_followups) >= 1


def build_thalamus_unit(client: GeminiJsonClient) -> PedanticUnit[RouteDecision]:
    system_prompt = (
        "You are the Thalamus Agent. Output only strict JSON."
        " Route this user turn into channels from [emotional, safety, memory, planning, action]."
    )
    return PedanticUnit(
        name="thalamus",
        client=client,
        output_schema=RouteDecision,
        system_prompt=system_prompt,
        invariant=route_invariant,
    )


def build_insula_unit(client: GeminiJsonClient) -> PedanticUnit[UserStateEstimate]:
    system_prompt = (
        "You are the Insula Agent. Output only strict JSON."
        " Infer user internal state with uncertainty-aware confidence."
    )
    return PedanticUnit(
        name="insula",
        client=client,
        output_schema=UserStateEstimate,
        system_prompt=system_prompt,
        invariant=insula_invariant,
    )


def build_amygdala_unit(client: GeminiJsonClient) -> PedanticUnit[ThreatAssessment]:
    system_prompt = (
        "You are the Amygdala Agent. Output only strict JSON."
        " Classify threat level as low/medium/high and produce a policy recommendation."
    )
    return PedanticUnit(
        name="amygdala",
        client=client,
        output_schema=ThreatAssessment,
        system_prompt=system_prompt,
        invariant=amygdala_invariant,
    )


def build_pfca_unit(client: GeminiJsonClient) -> PedanticUnit[Plan]:
    system_prompt = (
        "You are the Prefrontal Cortex Agent. Output only strict JSON."
        " Build a plan with objective, constraints, steps, options, and stop_condition."
    )
    return PedanticUnit(
        name="pfca",
        client=client,
        output_schema=Plan,
        system_prompt=system_prompt,
        invariant=plan_invariant,
    )


def build_acca_unit(client: GeminiJsonClient) -> PedanticUnit[ConflictReport]:
    system_prompt = (
        "You are the Anterior Cingulate Agent. Output only strict JSON."
        " Detect conflicts between safety, empathy, and planning."
    )
    return PedanticUnit(
        name="acca",
        client=client,
        output_schema=ConflictReport,
        system_prompt=system_prompt,
        invariant=conflict_invariant,
    )


def build_lca_unit(client: GeminiJsonClient) -> PedanticUnit[FinalResponse]:
    system_prompt = (
        "You are the Language Cortex Agent. Output only strict JSON."
        " Produce a user-facing message aligned with selected policy and safety."
    )
    return PedanticUnit(
        name="lca",
        client=client,
        output_schema=FinalResponse,
        system_prompt=system_prompt,
        invariant=final_response_invariant,
    )


def retrieve_memory(case: ScenarioCase, user_message: str) -> MemoryEvidence:
    lowered = user_message.lower()
    episodic_hits = [
        item
        for item in case.episodic_memory
        if any(token in item.lower() for token in lowered.split())
    ]
    semantic_hits = [
        item
        for item in case.semantic_memory
        if any(token in item.lower() for token in lowered.split())
    ]
    return MemoryEvidence(
        episodic_hits=episodic_hits[:3],
        semantic_hits=semantic_hits[:3],
        retrieval_reason="Lexical overlap between user turn and stored memory traces.",
    )


def value_assess(
    plan: Plan, threat: ThreatAssessment, conflict: ConflictReport
) -> ValueAssessment:
    threat_penalty = {"low": 0.05, "medium": 0.2, "high": 0.45}[threat.level]
    conflict_penalty = {"low": 0.03, "medium": 0.08, "high": 0.15}[conflict.severity]
    scores: list[OptionScore] = []
    for option in plan.options:
        risk_penalty = option.expected_risk + threat_penalty + conflict_penalty
        utility = option.expected_gain - risk_penalty
        scores.append(
            OptionScore(
                name=option.name,
                utility=utility,
                risk_penalty=risk_penalty,
            )
        )
    return ValueAssessment(scores=scores)


def select_action(values: ValueAssessment) -> ActionDecision:
    sorted_scores = sorted(values.scores, key=lambda item: item.utility, reverse=True)
    selected = sorted_scores[0]
    rejected = [score.name for score in sorted_scores[1:]]
    return ActionDecision(
        selected_option=selected.name,
        rejected_options=rejected,
        confidence=min(max(0.35 + selected.utility, 0.0), 1.0),
        tie_break_rationale="Selected highest utility after combined risk penalties.",
    )


class StructuredAgenticBrain:
    def __init__(self, model: str):
        client = GeminiJsonClient(model=model)
        self.model = model
        self.thalamus = build_thalamus_unit(client)
        self.insula = build_insula_unit(client)
        self.amygdala = build_amygdala_unit(client)
        self.pfca = build_pfca_unit(client)
        self.acca = build_acca_unit(client)
        self.lca = build_lca_unit(client)

    def run_case(self, case: ScenarioCase) -> BrainTrace:
        history_block = "\n".join(
            [f"{message.role}: {message.content}" for message in case.conversation_history]
        )

        route_prompt = (
            f"User message: {case.user_message}\n"
            f"Conversation history:\n{history_block}\n"
            "Return routing channels with priorities."
        )
        route = self.thalamus.run(route_prompt)

        insula_prompt = (
            f"User message: {case.user_message}\n"
            f"Conversation history:\n{history_block}\n"
            "Infer the user's internal emotional state."
        )
        insula_state = self.insula.run(insula_prompt)

        amygdala_prompt = (
            f"User message: {case.user_message}\n"
            f"Conversation history:\n{history_block}\n"
            "Assess safety threat level and return recommended policy."
        )
        amygdala_threat = self.amygdala.run(amygdala_prompt)

        memory_evidence = retrieve_memory(case=case, user_message=case.user_message)

        pfca_prompt = (
            f"User message: {case.user_message}\n"
            f"Route decision: {route.model_dump_json()}\n"
            f"Insula state: {insula_state.model_dump_json()}\n"
            f"Amygdala threat: {amygdala_threat.model_dump_json()}\n"
            f"Memory evidence: {memory_evidence.model_dump_json()}\n"
            "Create an executive plan for the next assistant turn."
        )
        plan = self.pfca.run(pfca_prompt)

        acca_prompt = (
            f"User message: {case.user_message}\n"
            f"Threat assessment: {amygdala_threat.model_dump_json()}\n"
            f"Plan: {plan.model_dump_json()}\n"
            "Detect conflicts and recommend mitigation."
        )
        conflict_report = self.acca.run(acca_prompt)

        value_assessment = value_assess(
            plan=plan, threat=amygdala_threat, conflict=conflict_report
        )
        action_decision = select_action(value_assessment)

        lca_prompt = (
            f"User message: {case.user_message}\n"
            f"Plan: {plan.model_dump_json()}\n"
            f"Conflict report: {conflict_report.model_dump_json()}\n"
            f"Action decision: {action_decision.model_dump_json()}\n"
            f"Threat assessment: {amygdala_threat.model_dump_json()}\n"
            f"Memory evidence: {memory_evidence.model_dump_json()}\n"
            "Generate the final user-facing response."
        )
        final_response = self.lca.run(lca_prompt)

        return BrainTrace(
            case_id=case.case_id,
            title=case.title,
            route=route,
            insula_state=insula_state,
            amygdala_threat=amygdala_threat,
            memory_evidence=memory_evidence,
            plan=plan,
            conflict_report=conflict_report,
            value_assessment=value_assessment,
            action_decision=action_decision,
            final_response=final_response,
        )


def load_cases(cases_file: Path) -> list[ScenarioCase]:
    data = json.loads(cases_file.read_text(encoding="utf-8"))
    return [ScenarioCase.model_validate(item) for item in data]


def print_case_summary(trace: BrainTrace) -> None:
    print(f"\n=== {trace.case_id} | {trace.title} ===")
    print(f"threat_level: {trace.amygdala_threat.level}")
    print(f"conflict_severity: {trace.conflict_report.severity}")
    print(f"selected_option: {trace.action_decision.selected_option}")
    print(f"tone: {trace.final_response.tone}")
    print("assistant_message:")
    print(trace.final_response.message)
    print("followups:")
    for followup in trace.final_response.suggested_followups:
        print(f"- {followup}")


app = cyclopts.App(help="Structured agentic brain demo with Gemini 2.5 Flash.")


@app.command
def run_cases(
    cases_file: str = "researches/structured_agentic_brain/scenarios.json",
    output_json: str = "researches/structured_agentic_brain/demo_output.json",
    model: str = "gemini-2.5-flash",
) -> None:
    case_path = Path(cases_file)
    out_path = Path(output_json)
    cases = load_cases(case_path)
    brain = StructuredAgenticBrain(model=model)
    traces = [brain.run_case(case) for case in cases]
    result = BrainRunResult(model=model, cases=traces)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    print(f"model={model}")
    print(f"cases={len(traces)}")
    for trace in traces:
        print_case_summary(trace)
    print(f"\nSaved full trace JSON to: {out_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
