from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_dids: list[str] = Field(min_length=1)
    runner_did: str
    original_purpose: str
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def cid(self) -> str:
        payload = self.model_dump(mode="json")
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class ConsentGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_did: str
    grantee_runner_did: str
    purpose: str
    scope: Literal["single_memory", "all_memories_for_owner"] = "single_memory"
    memory_id: str | None = None
    granted_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None

    def matches(self, request: "AccessRequest", evaluated_at: datetime) -> bool:
        if self.granted_at > evaluated_at:
            return False
        if self.revoked_at is not None and self.revoked_at <= evaluated_at:
            return False
        if self.expires_at is not None and self.expires_at <= evaluated_at:
            return False
        if self.grantee_runner_did != request.requester_runner_did:
            return False
        if self.purpose != request.purpose:
            return False
        if self.scope == "single_memory":
            return self.memory_id == request.memory_id
        return True


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    requester_runner_did: str
    purpose: str
    requested_at: datetime = Field(default_factory=utc_now)


class AccessDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason: str
    missing_owner_consents: list[str] = Field(default_factory=list)


class AMCPRepositoryBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: Literal["amcp"] = "amcp"
    version: str = "0.1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    memories: list[MemoryRecord] = Field(default_factory=list)
    grants: list[ConsentGrant] = Field(default_factory=list)


class MemoryCustodian:
    def __init__(self) -> None:
        self.memories: dict[str, MemoryRecord] = {}
        self.grants: list[ConsentGrant] = []

    def add_memory(self, record: MemoryRecord) -> MemoryRecord:
        self.memories[record.memory_id] = record
        return record

    def grant(self, consent: ConsentGrant) -> ConsentGrant:
        self.grants.append(consent)
        return consent

    def revoke(self, grant_id: str, owner_did: str) -> None:
        for consent in self.grants:
            if consent.grant_id == grant_id and consent.owner_did == owner_did:
                consent.revoked_at = utc_now()
                return
        raise ValueError("Grant not found for owner.")

    def evaluate_access(self, request: AccessRequest) -> AccessDecision:
        evaluated_at = utc_now()
        memory = self.memories[request.memory_id]
        if (
            request.requester_runner_did == memory.runner_did
            and request.purpose == memory.original_purpose
        ):
            return AccessDecision(
                allowed=True,
                reason="Allowed: original purpose for the same runner.",
            )

        consented_owners: set[str] = set()
        for consent in self.grants:
            if consent.owner_did in memory.owner_dids and consent.matches(
                request, evaluated_at=evaluated_at
            ):
                consented_owners.add(consent.owner_did)

        missing = sorted(set(memory.owner_dids) - consented_owners)
        if missing:
            return AccessDecision(
                allowed=False,
                reason="Denied: explicit consent missing for one or more owners.",
                missing_owner_consents=missing,
            )
        return AccessDecision(
            allowed=True,
            reason="Allowed: explicit consent exists for all cooperative owners.",
        )

    def export_bundle(self) -> AMCPRepositoryBundle:
        return AMCPRepositoryBundle(
            memories=list(self.memories.values()),
            grants=self.grants,
        )

    def read_memory_content(self, memory_id: str) -> str:
        return self.memories[memory_id].content


def build_demo_custodian() -> tuple[MemoryCustodian, str]:
    custodian = MemoryCustodian()
    memory = custodian.add_memory(
        MemoryRecord(
            owner_dids=["did:plc:alice", "did:plc:bob"],
            runner_did="did:runner:coding-agent-v1",
            original_purpose="coding_assistant",
            content="Alice and Bob prefer short actionable code review feedback.",
            tags=["coding", "style", "collaboration"],
        )
    )
    return custodian, memory.memory_id


def run_decision_trace() -> list[tuple[str, AccessDecision]]:
    custodian, memory_id = build_demo_custodian()
    runner = "did:runner:coding-agent-v1"

    decisions: list[tuple[str, AccessDecision]] = []
    original = custodian.evaluate_access(
        AccessRequest(
            memory_id=memory_id,
            requester_runner_did=runner,
            purpose="coding_assistant",
        )
    )
    decisions.append(("original-purpose", original))

    before_consent = custodian.evaluate_access(
        AccessRequest(
            memory_id=memory_id,
            requester_runner_did=runner,
            purpose="marketing_analytics",
        )
    )
    decisions.append(("cross-purpose-without-consent", before_consent))

    custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did=runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    after_alice = custodian.evaluate_access(
        AccessRequest(
            memory_id=memory_id,
            requester_runner_did=runner,
            purpose="marketing_analytics",
        )
    )
    decisions.append(("cross-purpose-only-alice-consented", after_alice))

    bob_grant = custodian.grant(
        ConsentGrant(
            owner_did="did:plc:bob",
            grantee_runner_did=runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    after_all = custodian.evaluate_access(
        AccessRequest(
            memory_id=memory_id,
            requester_runner_did=runner,
            purpose="marketing_analytics",
        )
    )
    decisions.append(("cross-purpose-all-owners-consented", after_all))

    custodian.revoke(grant_id=bob_grant.grant_id, owner_did="did:plc:bob")
    after_revoke = custodian.evaluate_access(
        AccessRequest(
            memory_id=memory_id,
            requester_runner_did=runner,
            purpose="marketing_analytics",
        )
    )
    decisions.append(("cross-purpose-after-bob-revocation", after_revoke))
    return decisions
