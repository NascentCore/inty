from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .core import (
    AMCPRepositoryBundle,
    ConsentGrant,
    MemoryCustodian,
    MemoryRecord,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class MigrationManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: Literal["amcp-migration-manifest"] = "amcp-migration-manifest"
    version: Literal["0.1.0"] = "0.1.0"
    migration_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_runner_did: str
    target_runner_did: str
    snapshot_at: datetime = Field(default_factory=utc_now)
    record_count: int = Field(ge=0)
    grant_count: int = Field(ge=0)
    bundle_sha256: str
    intent: str = "memory_portability"


class MigrationExportSignatureV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signer_did: str
    algorithm: Literal["none"] = "none"
    signature: str = "unsigned"


class AMCPMigrationEnvelopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: MigrationManifestV1
    bundle: AMCPRepositoryBundle
    signatures: list[MigrationExportSignatureV1] = Field(default_factory=list)

    def canonical_payload(self) -> dict:
        return self.model_dump(mode="json")

    def canonical_json(self) -> str:
        return canonical_json(self.canonical_payload())

    def save(self, output_path: Path) -> None:
        output_path.write_text(self.canonical_json() + "\n", encoding="utf-8")

    @classmethod
    def load(cls, input_path: Path) -> "AMCPMigrationEnvelopeV1":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        return cls.model_validate(payload)


class ConsentPortabilityPolicyV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 默认最小化：仅迁移与目标 runner 绑定的 consent。
    require_target_runner_match: bool = True
    # 默认最小化：拒绝全局 scope，防止在目标环境隐式扩大权限。
    allow_all_memories_scope: bool = False


class ImportReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: Literal["amcp-import-receipt"] = "amcp-import-receipt"
    version: Literal["0.1.0"] = "0.1.0"
    migration_id: str
    imported_at: datetime = Field(default_factory=utc_now)
    accepted_memory_ids: list[str] = Field(default_factory=list)
    accepted_grant_ids: list[str] = Field(default_factory=list)
    quarantined_memory_ids: list[str] = Field(default_factory=list)
    quarantined_grant_ids: list[str] = Field(default_factory=list)
    target_runner_did: str
    notes: list[str] = Field(default_factory=list)
    status: Literal["staged", "activated"] = "staged"


class MigrationStagingV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope: AMCPMigrationEnvelopeV1
    receipt: ImportReceiptV1
    accepted_memories: list[MemoryRecord] = Field(default_factory=list)
    accepted_grants: list[ConsentGrant] = Field(default_factory=list)


def _bundle_sha256(bundle: AMCPRepositoryBundle) -> str:
    payload = bundle.model_dump(mode="json")
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def export_migration_envelope_v1(
    custodian: MemoryCustodian,
    source_runner_did: str,
    target_runner_did: str,
) -> AMCPMigrationEnvelopeV1:
    bundle = custodian.export_bundle()
    envelope = AMCPMigrationEnvelopeV1(
        manifest=MigrationManifestV1(
            source_runner_did=source_runner_did,
            target_runner_did=target_runner_did,
            snapshot_at=utc_now(),
            record_count=len(bundle.memories),
            grant_count=len(bundle.grants),
            bundle_sha256=_bundle_sha256(bundle),
        ),
        bundle=bundle,
    )
    return envelope


def import_migration_envelope_v1(
    envelope: AMCPMigrationEnvelopeV1,
    policy: ConsentPortabilityPolicyV1 | None = None,
) -> MigrationStagingV1:
    effective_policy = policy or ConsentPortabilityPolicyV1()
    manifest = envelope.manifest
    bundle = envelope.bundle

    if manifest.record_count != len(bundle.memories):
        raise ValueError("Manifest record_count does not match bundle memories.")
    if manifest.grant_count != len(bundle.grants):
        raise ValueError("Manifest grant_count does not match bundle grants.")
    if manifest.bundle_sha256 != _bundle_sha256(bundle):
        raise ValueError("Manifest bundle_sha256 does not match bundle content.")

    accepted_memories = list(bundle.memories)
    accepted_memory_ids = [record.memory_id for record in accepted_memories]

    accepted_grants: list[ConsentGrant] = []
    quarantined_grant_ids: list[str] = []
    notes: list[str] = []

    for grant in bundle.grants:
        if effective_policy.require_target_runner_match and (
            grant.grantee_runner_did != manifest.target_runner_did
        ):
            quarantined_grant_ids.append(grant.grant_id)
            notes.append(
                f"quarantine grant={grant.grant_id}: grantee_runner_did mismatch target runner"
            )
            continue
        if not effective_policy.allow_all_memories_scope and (
            grant.scope == "all_memories_for_owner"
        ):
            quarantined_grant_ids.append(grant.grant_id)
            notes.append(
                f"quarantine grant={grant.grant_id}: all_memories_for_owner not allowed in v0.1"
            )
            continue
        accepted_grants.append(grant)

    receipt = ImportReceiptV1(
        migration_id=manifest.migration_id,
        accepted_memory_ids=accepted_memory_ids,
        accepted_grant_ids=[grant.grant_id for grant in accepted_grants],
        quarantined_memory_ids=[],
        quarantined_grant_ids=quarantined_grant_ids,
        target_runner_did=manifest.target_runner_did,
        notes=notes,
        status="staged",
    )
    return MigrationStagingV1(
        envelope=envelope,
        receipt=receipt,
        accepted_memories=accepted_memories,
        accepted_grants=accepted_grants,
    )


def activate_migration_staging_v1(
    staging: MigrationStagingV1,
    target_custodian: MemoryCustodian,
) -> ImportReceiptV1:
    existing_memory_ids = set(target_custodian.memories.keys())
    existing_grant_ids = {grant.grant_id for grant in target_custodian.grants}

    for memory in staging.accepted_memories:
        if memory.memory_id in existing_memory_ids:
            continue
        target_custodian.add_memory(memory)
        existing_memory_ids.add(memory.memory_id)
    for grant in staging.accepted_grants:
        if grant.grant_id in existing_grant_ids:
            continue
        target_custodian.grant(grant)
        existing_grant_ids.add(grant.grant_id)

    activated = staging.receipt.model_copy(
        update={"status": "activated", "imported_at": utc_now()}
    )
    return activated
