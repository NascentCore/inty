from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field

try:
    from .core import (
        AMCPRepositoryBundle,
        ConsentGrant,
        MemoryCustodian,
        MemoryRecord,
    )
except ImportError:
    from core import (  # type: ignore[no-redef]
        AMCPRepositoryBundle,
        ConsentGrant,
        MemoryCustodian,
        MemoryRecord,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)


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
    key_id: str = "atproto"
    algorithm: Literal["ed25519"] = "ed25519"
    payload_sha256: str
    signature: str


class MigrationSigningKeyV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signer_did: str
    key_id: str = "atproto"
    private_key_b64url: str

    def private_key_bytes(self) -> bytes:
        return b64url_decode(self.private_key_b64url)

    def public_key_bytes(self) -> bytes:
        public = Ed25519PrivateKey.from_private_bytes(self.private_key_bytes()).public_key()
        return public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )


class DIDKeyResolverV1(Protocol):
    def resolve_public_key(self, signer_did: str, key_id: str) -> bytes:
        pass


class StaticDIDKeyResolverV1:
    def __init__(self, public_keys: dict[tuple[str, str], bytes]) -> None:
        self.public_keys = public_keys

    @classmethod
    def from_signing_keys(
        cls, signing_keys: list[MigrationSigningKeyV1]
    ) -> "StaticDIDKeyResolverV1":
        key_map: dict[tuple[str, str], bytes] = {}
        for key in signing_keys:
            key_map[(key.signer_did, key.key_id)] = key.public_key_bytes()
        return cls(key_map)

    def resolve_public_key(self, signer_did: str, key_id: str) -> bytes:
        key = self.public_keys.get((signer_did, key_id))
        if key is None:
            raise ValueError(f"No public key for signer={signer_did} key_id={key_id}")
        return key


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
    # v0.2：显式开启签名校验（兼容旧 envelope 默认关闭）。
    require_valid_signatures: bool = False
    # 要求导入时必须包含且通过校验的 signer（支持 did 或 did#key_id）。
    required_signer_dids: list[str] = Field(default_factory=list)


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


def signature_payload_json_v1(envelope: AMCPMigrationEnvelopeV1) -> str:
    payload = {
        "protocol": "amcp-migration-signature-payload",
        "version": "0.1.0",
        "manifest": envelope.manifest.model_dump(mode="json"),
    }
    return canonical_json(payload)


def signature_payload_sha256_v1(envelope: AMCPMigrationEnvelopeV1) -> str:
    payload_json = signature_payload_json_v1(envelope)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def sign_envelope_ed25519_v1(
    envelope: AMCPMigrationEnvelopeV1,
    signer_did: str,
    key_id: str,
    private_key_bytes: bytes,
) -> MigrationExportSignatureV1:
    payload_json = signature_payload_json_v1(envelope)
    payload_bytes = payload_json.encode("utf-8")
    signature = Ed25519PrivateKey.from_private_bytes(private_key_bytes).sign(payload_bytes)
    return MigrationExportSignatureV1(
        signer_did=signer_did,
        key_id=key_id,
        algorithm="ed25519",
        payload_sha256=hashlib.sha256(payload_bytes).hexdigest(),
        signature=b64url_encode(signature),
    )


def verify_envelope_signature_v1(
    envelope: AMCPMigrationEnvelopeV1,
    signature: MigrationExportSignatureV1,
    key_resolver: DIDKeyResolverV1,
) -> None:
    payload_json = signature_payload_json_v1(envelope)
    payload_bytes = payload_json.encode("utf-8")
    payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    if signature.payload_sha256 != payload_sha256:
        raise ValueError(
            f"Signature payload hash mismatch for signer={signature.signer_did} key_id={signature.key_id}"
        )

    public_key_bytes = key_resolver.resolve_public_key(signature.signer_did, signature.key_id)
    verifier = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        verifier.verify(b64url_decode(signature.signature), payload_bytes)
    except InvalidSignature as exc:
        raise ValueError(
            f"Invalid signature for signer={signature.signer_did} key_id={signature.key_id}"
        ) from exc


class SignatureTestVectorV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signer_did: str
    key_id: str
    public_key_b64url: str
    payload_json: str
    payload_sha256: str
    signature_b64url: str


def build_signature_test_vector_v1() -> SignatureTestVectorV1:
    fixed_memory = MemoryRecord(
        memory_id="mem-fixed-001",
        owner_dids=["did:plc:alice"],
        runner_did="did:runner:source",
        original_purpose="coding_assistant",
        content="fixed-memory-content",
        tags=["fixed"],
        created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    bundle = AMCPRepositoryBundle(
        protocol="amcp",
        version="0.1.0",
        generated_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        memories=[fixed_memory],
        grants=[],
    )
    envelope = AMCPMigrationEnvelopeV1(
        manifest=MigrationManifestV1(
            migration_id="migration-fixed-001",
            source_runner_did="did:runner:source",
            target_runner_did="did:runner:target",
            snapshot_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            record_count=1,
            grant_count=0,
            bundle_sha256=_bundle_sha256(bundle),
            intent="memory_portability",
        ),
        bundle=bundle,
        signatures=[],
    )
    private_key = bytes([7]) * 32
    signer_did = "did:plc:fixture-signer"
    key_id = "atproto-2026-01"
    signature = sign_envelope_ed25519_v1(
        envelope=envelope,
        signer_did=signer_did,
        key_id=key_id,
        private_key_bytes=private_key,
    )
    public_key = (
        Ed25519PrivateKey.from_private_bytes(private_key)
        .public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    )
    return SignatureTestVectorV1(
        signer_did=signer_did,
        key_id=key_id,
        public_key_b64url=b64url_encode(public_key),
        payload_json=signature_payload_json_v1(envelope),
        payload_sha256=signature.payload_sha256,
        signature_b64url=signature.signature,
    )


def verify_signature_test_vector_v1(vector: SignatureTestVectorV1) -> None:
    public_key = Ed25519PublicKey.from_public_bytes(b64url_decode(vector.public_key_b64url))
    payload_bytes = vector.payload_json.encode("utf-8")
    payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    if payload_sha256 != vector.payload_sha256:
        raise ValueError("Signature vector payload hash mismatch.")
    try:
        public_key.verify(b64url_decode(vector.signature_b64url), payload_bytes)
    except InvalidSignature as exc:
        raise ValueError("Signature vector verification failed.") from exc


def _validated_signer_refs(signature: MigrationExportSignatureV1) -> set[str]:
    return {
        signature.signer_did,
        f"{signature.signer_did}#{signature.key_id}",
    }


def export_migration_envelope_v1(
    custodian: MemoryCustodian,
    source_runner_did: str,
    target_runner_did: str,
    signing_keys: list[MigrationSigningKeyV1] | None = None,
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
    if signing_keys:
        envelope.signatures = [
            sign_envelope_ed25519_v1(
                envelope=envelope,
                signer_did=key.signer_did,
                key_id=key.key_id,
                private_key_bytes=key.private_key_bytes(),
            )
            for key in signing_keys
        ]
    return envelope


def import_migration_envelope_v1(
    envelope: AMCPMigrationEnvelopeV1,
    policy: ConsentPortabilityPolicyV1 | None = None,
    key_resolver: DIDKeyResolverV1 | None = None,
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

    if effective_policy.require_valid_signatures or effective_policy.required_signer_dids:
        if not envelope.signatures:
            raise ValueError("No signatures present but signature verification is required.")
        if key_resolver is None:
            raise ValueError("Signature verification requires a DID key resolver.")

        validated_signers: set[str] = set()
        for signature in envelope.signatures:
            verify_envelope_signature_v1(
                envelope=envelope,
                signature=signature,
                key_resolver=key_resolver,
            )
            validated_signers.update(_validated_signer_refs(signature))

        missing_required_signers = sorted(
            set(effective_policy.required_signer_dids) - validated_signers
        )
        if missing_required_signers:
            raise ValueError(
                "Missing required signer DID(s): " + ",".join(missing_required_signers)
            )

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
    for memory in staging.accepted_memories:
        target_custodian.add_memory(memory)
    for grant in staging.accepted_grants:
        target_custodian.grant(grant)

    activated = staging.receipt.model_copy(
        update={"status": "activated", "imported_at": utc_now()}
    )
    return activated
