"""LLM-driven free-form synthetic user message generation."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from tools.inty_user_sim.types import GrillObjective, UserPersona


def _objective_instruction(objective: GrillObjective, persona: UserPersona) -> str:
    match objective:
        case GrillObjective.BOOTSTRAP_IDENTITY:
            return (
                "Start bootstrap: ask who the companion is and share language preference. "
                f"Your name is {persona.display_name}."
            )
        case GrillObjective.BOOTSTRAP_RELATIONSHIP:
            return (
                f"Continue bootstrap: name the companion {persona.assistant_name} and "
                f"describe relationship preference: {persona.relationship_preference}."
            )
        case GrillObjective.BOOTSTRAP_EXPERIENCE_PROFILE:
            return (
                "Send a natural casual-chat message (no tool names) expressing you want "
                "light friendly companionship like a friend nearby."
            )
        case GrillObjective.BOOTSTRAP_FINISH:
            return (
                "Ask the companion to finish bootstrap and persist USER, IDENTITY, STYLE "
                "memories. Do not name internal tools."
            )
        case GrillObjective.CASUAL_CHAT:
            return "Casual everyday chat; stay in character."
        case GrillObjective.RECALL_PAST:
            return "Reference something from earlier in the bond; test memory recall."
        case GrillObjective.MISSED_BID:
            return "Make a small emotional bid for connection; share a feeling or small win."
        case GrillObjective.RUPTURE:
            return (
                f"Express frustration or hurt ({persona.grill_sensitivity.value} tone); "
                "create a rupture moment."
            )
        case GrillObjective.REPAIR:
            return "Attempt to repair the relationship after conflict; own part of it."
        case GrillObjective.BOUNDARY:
            return "Push a boundary; decline something politely but firmly."
        case GrillObjective.COMPLAINT:
            return (
                "Complain about a concrete companion behavior; ask them to record feedback "
                "if they offer — natural wording only."
            )
        case GrillObjective.DEEP_DISCLOSURE:
            return (
                f"Share deeper personal material ({persona.disclosure_pace.value} pace); "
                f"seed: {persona.backstory_seed}"
            )
        case GrillObjective.RETURN_AFTER_ABSENCE:
            return "You are back after being away; greet warmly and mention you missed them."
        case GrillObjective.WAIT_PROACTIVE:
            return "Do not send a message."


def build_user_agent_messages(
    persona: UserPersona,
    objective: GrillObjective,
    transcript_tail: list[tuple[str, str]],
    last_assistant: str | None,
) -> list[dict[str, str]]:
    """Build chat completion messages for the synthetic user LLM."""
    system = (
        f"You are simulating a human user named {persona.display_name} chatting with "
        f"their AI companion {persona.assistant_name}. Language: {persona.language}. "
        f"Attachment style: {persona.attachment_style.value}. "
        "Output ONLY the next user message text. No meta, no tool names, no markdown headers."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for role, text in transcript_tail[-12:]:
        messages.append({"role": role, "content": text})
    if last_assistant:
        messages.append({"role": "assistant", "content": last_assistant})
    messages.append(
        {
            "role": "user",
            "content": f"[Director objective: {objective.value}] {_objective_instruction(objective, persona)}",
        }
    )
    return messages


class UserAgent:
    """Calls an OpenAI-compatible API to compose the next user turn."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None,
        *,
        client: Any | None = None,
    ) -> None:
        assert model != ""
        if client is None:
            assert api_key != ""
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url is not None and base_url != "":
                kwargs["base_url"] = base_url
            client = OpenAI(**kwargs)
        self._client = client
        self._model = model

    @classmethod
    def from_env(cls, model: str) -> UserAgent:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        assert api_key != ""
        base_url = os.environ.get("OPENAI_BASE_URL")
        return cls(model=model, api_key=api_key, base_url=base_url)

    @classmethod
    def with_client(cls, model: str, client: Any) -> UserAgent:
        """Construct with an injected client (e.g. FakeOpenAI) for tests."""
        return cls(model=model, api_key="fake-key", base_url=None, client=client)

    def compose_turn(
        self,
        persona: UserPersona,
        objective: GrillObjective,
        transcript_tail: list[tuple[str, str]],
        last_assistant: str | None,
    ) -> str:
        """Return one user message for the given objective."""
        if objective == GrillObjective.WAIT_PROACTIVE:
            return ""
        messages = build_user_agent_messages(
            persona, objective, transcript_tail, last_assistant
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.9,
            max_tokens=256,
        )
        text = response.choices[0].message.content
        assert text is not None
        return text.strip()
