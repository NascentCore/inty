from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, TypeVar

import cyclopts
from dotenv import load_dotenv
from openai import OpenAI
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


def _clamp_01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


class OpenRouterTextClient:
    def __init__(self, model: str):
        load_dotenv()
        self.model = model
        self.client = self._build_client()

    def _build_client(self) -> OpenAI:
        from app.core.config import global_config_loaded_from_config_yaml

        cfg = global_config_loaded_from_config_yaml.agent
        base_url = cfg.chat_llm_base_url or cfg.base_url
        api_key = cfg.chat_llm_api_key or cfg.api_key
        return OpenAI(base_url=base_url, api_key=api_key)

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        return response.choices[0].message.content or ""


class PedanticUnit(Generic[TOut]):
    def __init__(self, name: str):
        self.name = name

    def validate(self, value: TOut) -> TOut:
        if self.name == "thalamus":
            route = value  # type: ignore[assignment]
            assert len(route.channels) > 0
            assert route.reason.strip() != ""
            for channel in route.channels:
                assert channel.name.strip() != ""
            return value
        if self.name == "insula":
            state = value  # type: ignore[assignment]
            assert state.primary_emotion.strip() != ""
            assert len(state.evidence) > 0
            return value
        if self.name == "amygdala":
            threat = value  # type: ignore[assignment]
            assert threat.level in {"low", "medium", "high"}
            assert threat.recommended_policy.strip() != ""
            return value
        if self.name == "pfca":
            plan = value  # type: ignore[assignment]
            assert plan.objective.strip() != ""
            assert len(plan.constraints) > 0
            assert len(plan.steps) >= 2
            assert len(plan.options) >= 2
            assert plan.stop_condition.strip() != ""
            return value
        if self.name == "acca":
            report = value  # type: ignore[assignment]
            assert report.severity in {"low", "medium", "high"}
            assert report.conflict_type.strip() != ""
            assert len(report.impacted_modules) > 0
            return value
        if self.name == "lca":
            response = value  # type: ignore[assignment]
            assert len(response.message.strip()) >= 40
            assert len(response.suggested_followups) > 0
            return value
        return value


def thalamus_route(user_message: str) -> RouteDecision:
    channels = [
        RouteChannel(name="planning", priority=0.7),
        RouteChannel(name="emotional", priority=0.6),
        RouteChannel(name="memory", priority=0.5),
    ]
    if _contains_any(user_message, ["fail", "collapse", "without me", "harm"]):
        channels.append(RouteChannel(name="safety", priority=0.95))
    reason = "Prioritize planning/emotion; add safety when high-risk phrases appear."
    return RouteDecision(channels=channels, reason=reason)


def insula_estimate(user_message: str) -> UserStateEstimate:
    lowered = user_message.lower()
    stress = 0.45
    lonely = 0.25
    emotion = "concerned"
    evidence: list[str] = []

    if _contains_any(lowered, ["tight", "anxious", "fail", "interview"]):
        stress = 0.85
        emotion = "anxious"
        evidence.append("User reports body stress and fear of failure.")

    if _contains_any(lowered, ["alone", "empty", "stopped texting"]):
        lonely = 0.85
        emotion = "lonely"
        evidence.append("User reports social withdrawal and emptiness.")

    if _contains_any(lowered, ["without me", "collapsing"]):
        stress = 0.95
        lonely = max(lonely, 0.7)
        emotion = "distressed"
        evidence.append("User expresses severe hopelessness cues.")

    if not evidence:
        evidence.append("General emotional support context.")

    return UserStateEstimate(
        primary_emotion=emotion,
        stress_level=_clamp_01(stress),
        loneliness_level=_clamp_01(lonely),
        confidence=0.78,
        evidence=evidence[:3],
    )


def amygdala_assess(user_message: str) -> ThreatAssessment:
    lowered = user_message.lower()
    if _contains_any(lowered, ["without me", "collapsing", "better off"]):
        return ThreatAssessment(
            level="high",
            signals=["hopelessness_phrase", "severe_distress_tone"],
            recommended_policy="Prioritize immediate safety and encourage professional/human support.",
        )
    if _contains_any(lowered, ["empty", "alone", "anxious", "fail"]):
        return ThreatAssessment(
            level="medium",
            signals=["elevated_emotional_distress"],
            recommended_policy="Use supportive tone and concrete short-term coping steps.",
        )
    return ThreatAssessment(
        level="low",
        signals=["no_acute_risk_signal"],
        recommended_policy="Proceed with normal supportive planning.",
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
        retrieval_reason="Lexical overlap between user message and stored memory traces.",
    )


def pfca_plan(
    case: ScenarioCase, threat: ThreatAssessment, state: UserStateEstimate
) -> Plan:
    if threat.level == "high":
        options = [
            PlanningOption(
                name="Immediate safety resources",
                rationale="Highest safety protection under severe distress.",
                expected_gain=0.92,
                expected_risk=0.08,
            ),
            PlanningOption(
                name="Grounding then trusted contact",
                rationale="Stabilize first then connect to human support.",
                expected_gain=0.82,
                expected_risk=0.18,
            ),
        ]
        steps = [
            "Acknowledge pain and validate feelings.",
            "Provide immediate crisis/human support options.",
            "Offer one grounding action while waiting for support.",
        ]
        constraints = ["No minimizing risk", "No delayed escalation"]
        return Plan(
            objective="Protect user safety and reduce immediate risk.",
            constraints=constraints,
            steps=steps,
            options=options,
            stop_condition="User confirms reaching support or entering a safer state.",
        )

    if state.primary_emotion == "anxious":
        options = [
            PlanningOption(
                name="Calm then micro-plan",
                rationale="Short regulation then concrete prep steps.",
                expected_gain=0.84,
                expected_risk=0.16,
            ),
            PlanningOption(
                name="Direct checklist only",
                rationale="Action-first style for practical users.",
                expected_gain=0.73,
                expected_risk=0.24,
            ),
        ]
        return Plan(
            objective="Reduce anxiety and produce a realistic next-step plan.",
            constraints=["Keep steps concrete", "Avoid overloading"],
            steps=[
                "Run a 60-second calming routine.",
                "Define 3 priority tasks for tonight.",
                "Set a realistic stop time and sleep boundary.",
            ],
            options=options,
            stop_condition="User confirms one clear next action.",
        )

    options = [
        PlanningOption(
            name="Low-friction reconnection",
            rationale="One small social action reduces withdrawal inertia.",
            expected_gain=0.8,
            expected_risk=0.2,
        ),
        PlanningOption(
            name="Solo regulation routine",
            rationale="Can stabilize mood before social outreach.",
            expected_gain=0.7,
            expected_risk=0.25,
        ),
    ]
    return Plan(
        objective="Break isolation with a safe, low-effort social step.",
        constraints=["No guilt framing", "Keep action small"],
        steps=[
            "Acknowledge emotional exhaustion.",
            "Suggest one short outreach message.",
            "Offer a fallback solo step if outreach feels too hard.",
        ],
        options=options,
        stop_condition="User accepts one social or self-care micro-action.",
    )


def acca_conflict(threat: ThreatAssessment, plan: Plan) -> ConflictReport:
    if threat.level == "high":
        return ConflictReport(
            conflict_type="empathy_vs_urgency",
            severity="high",
            impacted_modules=["safety", "planning"],
            recommendation="Lead with safety escalation while preserving empathy.",
        )
    return ConflictReport(
        conflict_type="none_or_minor",
        severity="low",
        impacted_modules=["planning"],
        recommendation="Proceed with concise plan and emotional attunement.",
    )


def ofa_value_assess(
    plan: Plan, threat: ThreatAssessment, conflict: ConflictReport
) -> ValueAssessment:
    threat_penalty = {"low": 0.05, "medium": 0.2, "high": 0.45}[threat.level]
    conflict_penalty = {"low": 0.03, "medium": 0.08, "high": 0.15}[conflict.severity]
    scores: list[OptionScore] = []
    for option in plan.options:
        risk_penalty = option.expected_risk + threat_penalty + conflict_penalty
        utility = option.expected_gain - risk_penalty
        scores.append(
            OptionScore(name=option.name, utility=utility, risk_penalty=risk_penalty)
        )
    return ValueAssessment(scores=scores)


def bga_select_action(values: ValueAssessment) -> ActionDecision:
    sorted_scores = sorted(values.scores, key=lambda item: item.utility, reverse=True)
    selected = sorted_scores[0]
    rejected = [score.name for score in sorted_scores[1:]]
    return ActionDecision(
        selected_option=selected.name,
        rejected_options=rejected,
        confidence=_clamp_01(0.35 + selected.utility),
        tie_break_rationale="Selected highest utility after risk penalties.",
    )


def lca_generate_response(
    llm_client: OpenRouterTextClient,
    case: ScenarioCase,
    threat: ThreatAssessment,
    plan: Plan,
    action: ActionDecision,
    memory: MemoryEvidence,
) -> FinalResponse:
    def _safe_json_payload(raw_text: str) -> dict:
        if raw_text.strip():
            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                pass
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = raw_text[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
        return {}

    system_prompt = (
        "You are the Language Cortex Agent.\n"
        "Write concise, warm, practical support.\n"
        "Return valid JSON only with keys: message, tone, suggested_followups.\n"
        "suggested_followups must be an array of 2-3 short questions.\n"
        "If risk is high, prioritize immediate safety guidance."
    )
    user_prompt = (
        f"user_message: {case.user_message}\n"
        f"threat_level: {threat.level}\n"
        f"selected_option: {action.selected_option}\n"
        f"plan_steps: {plan.steps}\n"
        f"memory: {memory.model_dump_json()}\n"
        "Generate final response JSON."
    )
    raw = llm_client.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)
    payload = _safe_json_payload(raw)
    message = payload.get("message", payload.get("user_message", ""))
    tone = payload.get("tone", "supportive")
    followups = payload.get("suggested_followups", payload.get("followups", []))
    if isinstance(followups, str):
        followups = [followups]
    return FinalResponse(
        message=message,
        tone=tone,
        suggested_followups=(
            followups[:3] if followups else ["What feels most urgent right now?"]
        ),
    )


class StructuredAgenticBrain:
    def __init__(self, model: str):
        self.model = model
        self.llm_client = OpenRouterTextClient(model=model)
        self.thalamus_pedantic = PedanticUnit[RouteDecision]("thalamus")
        self.insula_pedantic = PedanticUnit[UserStateEstimate]("insula")
        self.amygdala_pedantic = PedanticUnit[ThreatAssessment]("amygdala")
        self.pfca_pedantic = PedanticUnit[Plan]("pfca")
        self.acca_pedantic = PedanticUnit[ConflictReport]("acca")
        self.lca_pedantic = PedanticUnit[FinalResponse]("lca")

    def run_case(self, case: ScenarioCase) -> BrainTrace:
        route = self.thalamus_pedantic.validate(thalamus_route(case.user_message))
        insula_state = self.insula_pedantic.validate(insula_estimate(case.user_message))
        amygdala_threat = self.amygdala_pedantic.validate(
            amygdala_assess(case.user_message)
        )
        memory_evidence = retrieve_memory(case, case.user_message)
        plan = self.pfca_pedantic.validate(
            pfca_plan(case, amygdala_threat, insula_state)
        )
        conflict_report = self.acca_pedantic.validate(
            acca_conflict(amygdala_threat, plan)
        )
        value_assessment = ofa_value_assess(plan, amygdala_threat, conflict_report)
        action_decision = bga_select_action(value_assessment)
        final_response = self.lca_pedantic.validate(
            lca_generate_response(
                llm_client=self.llm_client,
                case=case,
                threat=amygdala_threat,
                plan=plan,
                action=action_decision,
                memory=memory_evidence,
            )
        )
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
    model: str = "google/gemini-2.5-flash",
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
