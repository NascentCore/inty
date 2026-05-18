from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ChannelType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    VOICE_CALL = "voice_call"
    TELEGRAM = "telegram"


class ModelTier(str, Enum):
    FAST = "fast"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"


@dataclass(frozen=True)
class ModelProfile:
    tier: ModelTier
    name: str


@dataclass(frozen=True)
class ModelCatalog:
    fast: ModelProfile
    reasoning: ModelProfile
    multimodal: ModelProfile

    @classmethod
    def default(cls) -> "ModelCatalog":
        return cls(
            fast=ModelProfile(tier=ModelTier.FAST, name="fast-text-1"),
            reasoning=ModelProfile(
                tier=ModelTier.REASONING, name="reasoning-1"
            ),
            multimodal=ModelProfile(
                tier=ModelTier.MULTIMODAL, name="multimodal-1"
            ),
        )


@dataclass(frozen=True)
class OutboundEvent:
    channel: ChannelType
    recipient: str
    content: str
    metadata: dict[str, str]


class ChannelTransport(Protocol):
    def send(
        self,
        *,
        channel: ChannelType,
        recipient: str,
        content: str,
        metadata: dict[str, str],
    ) -> OutboundEvent: ...


@dataclass
class InMemoryChannelTransport:
    sent_events: list[OutboundEvent] = field(default_factory=list)

    def send(
        self,
        *,
        channel: ChannelType,
        recipient: str,
        content: str,
        metadata: dict[str, str],
    ) -> OutboundEvent:
        event = OutboundEvent(
            channel=channel,
            recipient=recipient,
            content=content,
            metadata=metadata,
        )
        self.sent_events.append(event)
        return event


class ModelExecutor(Protocol):
    def generate(
        self,
        *,
        model: ModelProfile,
        channel: ChannelType,
        expression: str,
        virtual_age_years: float,
        user_message: str | None,
        proactive: bool,
    ) -> str: ...


@dataclass
class ScriptedModelExecutor:
    def generate(
        self,
        *,
        model: ModelProfile,
        channel: ChannelType,
        expression: str,
        virtual_age_years: float,
        user_message: str | None,
        proactive: bool,
    ) -> str:
        if proactive:
            body = "just checking in from my virtual world."
        else:
            body = f"I heard you: {user_message or ''}".strip()
        return (
            f"[{model.name}] via {channel.value} | expression={expression} "
            f"| age={virtual_age_years:.2f} | {body}"
        )


@dataclass
class CompanionState:
    companion_name: str
    user_name: str
    user_contact: str
    initial_virtual_age_years: float
    clock_rate: float
    now: float
    default_channel: ChannelType = ChannelType.SMS
    expression: str = "warm"
    emotion: str = "neutral"
    seconds_per_virtual_year: float = 365.2425 * 24 * 3600

    def __post_init__(self) -> None:
        assert self.clock_rate > 0, "clock_rate must be > 0"
        self.virtual_age_years = self.initial_virtual_age_years
        self.last_world_timestamp = self.now
        self.last_outreach_timestamp = self.now

    virtual_age_years: float = field(init=False)
    last_world_timestamp: float = field(init=False)
    last_outreach_timestamp: float = field(init=False)

    def advance_age(self, *, now: float) -> None:
        elapsed_world_seconds = max(0.0, now - self.last_world_timestamp)
        elapsed_virtual_seconds = elapsed_world_seconds * self.clock_rate
        self.virtual_age_years += (
            elapsed_virtual_seconds / self.seconds_per_virtual_year
        )
        self.last_world_timestamp = now


@dataclass(frozen=True)
class EmotionClassification:
    emotion: str
    expression: str


def classify_emotion(user_message: str) -> EmotionClassification:
    normalized = user_message.lower()
    if any(word in normalized for word in ("sad", "lonely", "down", "hurt")):
        return EmotionClassification(emotion="sad", expression="gentle")
    if any(word in normalized for word in ("angry", "mad", "upset", "furious")):
        return EmotionClassification(emotion="angry", expression="calm")
    if any(
        word in normalized for word in ("excited", "thrilled", "joy", "happy")
    ):
        return EmotionClassification(emotion="joyful", expression="playful")
    return EmotionClassification(emotion="neutral", expression="warm")


def select_channel(
    user_message: str | None, *, default_channel: ChannelType = ChannelType.SMS
) -> ChannelType:
    if user_message is None:
        return default_channel
    normalized = user_message.lower()
    if "email" in normalized or "mail me" in normalized:
        return ChannelType.EMAIL
    if "telegram" in normalized or "tg" in normalized:
        return ChannelType.TELEGRAM
    if (
        "call me" in normalized
        or "voice call" in normalized
        or "phone me" in normalized
    ):
        return ChannelType.VOICE_CALL
    return default_channel


def select_model_tier(
    *, user_message: str | None, channel: ChannelType
) -> ModelTier:
    if channel == ChannelType.VOICE_CALL:
        return ModelTier.MULTIMODAL
    if not user_message:
        return ModelTier.FAST
    normalized = user_message.lower()
    requires_reasoning = any(
        token in normalized
        for token in ("why", "analyze", "plan", "compare", "strategy")
    )
    if requires_reasoning or len(normalized) > 220:
        return ModelTier.REASONING
    needs_multimodal = any(
        token in normalized for token in ("image", "video", "see", "look")
    )
    if needs_multimodal:
        return ModelTier.MULTIMODAL
    return ModelTier.FAST


def pick_model_from_tier(
    model_catalog: ModelCatalog, tier: ModelTier
) -> ModelProfile:
    if tier == ModelTier.MULTIMODAL:
        return model_catalog.multimodal
    if tier == ModelTier.REASONING:
        return model_catalog.reasoning
    return model_catalog.fast


@dataclass
class PerpetualCompanionAgent:
    state: CompanionState
    model_catalog: ModelCatalog
    model_executor: ModelExecutor
    channel_transport: ChannelTransport
    proactive_interval_seconds: float = 300.0

    def tick(
        self, *, now: float, user_message: str | None = None
    ) -> list[OutboundEvent]:
        self.state.advance_age(now=now)
        if user_message is not None:
            return [self._handle_user_turn(now=now, user_message=user_message)]
        return self._handle_heartbeat(now=now)

    def _handle_user_turn(
        self, *, now: float, user_message: str
    ) -> OutboundEvent:
        classification = classify_emotion(user_message)
        self.state.emotion = classification.emotion
        self.state.expression = classification.expression

        channel = select_channel(
            user_message,
            default_channel=self.state.default_channel,
        )
        tier = select_model_tier(user_message=user_message, channel=channel)
        model = pick_model_from_tier(self.model_catalog, tier)

        content = self.model_executor.generate(
            model=model,
            channel=channel,
            expression=self.state.expression,
            virtual_age_years=self.state.virtual_age_years,
            user_message=user_message,
            proactive=False,
        )
        metadata = {
            "companion_name": self.state.companion_name,
            "emotion": self.state.emotion,
            "expression": self.state.expression,
            "model_tier": model.tier.value,
            "model_name": model.name,
            "proactive": "false",
        }
        self.state.last_outreach_timestamp = now
        return self.channel_transport.send(
            channel=channel,
            recipient=self.state.user_contact,
            content=content,
            metadata=metadata,
        )

    def _handle_heartbeat(self, *, now: float) -> list[OutboundEvent]:
        if (
            now - self.state.last_outreach_timestamp
        ) < self.proactive_interval_seconds:
            return []
        channel = self.state.default_channel
        tier = (
            ModelTier.MULTIMODAL
            if self.state.emotion == "joyful"
            else ModelTier.FAST
        )
        model = pick_model_from_tier(self.model_catalog, tier)
        content = self.model_executor.generate(
            model=model,
            channel=channel,
            expression=self.state.expression,
            virtual_age_years=self.state.virtual_age_years,
            user_message=None,
            proactive=True,
        )
        metadata = {
            "companion_name": self.state.companion_name,
            "emotion": self.state.emotion,
            "expression": self.state.expression,
            "model_tier": model.tier.value,
            "model_name": model.name,
            "proactive": "true",
        }
        self.state.last_outreach_timestamp = now
        event = self.channel_transport.send(
            channel=channel,
            recipient=self.state.user_contact,
            content=content,
            metadata=metadata,
        )
        return [event]
