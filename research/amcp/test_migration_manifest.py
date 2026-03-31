from __future__ import annotations

from research.amcp.core import AccessRequest, ConsentGrant, MemoryCustodian, build_demo_custodian
from research.amcp.migration import (
    AMCPMigrationEnvelopeV1,
    ConsentPortabilityPolicyV1,
    MigrationExportSignatureV1,
    activate_migration_staging_v1,
    export_migration_envelope_v1,
    import_migration_envelope_v1,
)


def test_export_manifest_counts_and_hash_are_consistent() -> None:
    custodian, memory_id = build_demo_custodian()
    runner = "did:runner:coding-agent-v1"
    custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did=runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did=runner,
        target_runner_did="did:runner:new-agent-v2",
    )

    assert envelope.manifest.record_count == len(envelope.bundle.memories)
    assert envelope.manifest.grant_count == len(envelope.bundle.grants)
    assert len(envelope.manifest.bundle_sha256) == 64


def test_import_quarantines_grants_with_target_runner_mismatch() -> None:
    custodian, memory_id = build_demo_custodian()
    custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did="did:runner:old-runner",
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did="did:runner:old-runner",
        target_runner_did="did:runner:new-runner",
    )
    staging = import_migration_envelope_v1(
        envelope=envelope,
        policy=ConsentPortabilityPolicyV1(
            require_target_runner_match=True,
            allow_all_memories_scope=False,
        ),
    )

    assert len(staging.accepted_memories) == 1
    assert len(staging.accepted_grants) == 0
    assert len(staging.receipt.quarantined_grant_ids) == 1
    assert staging.receipt.status == "staged"


def test_activate_staging_restores_memory_and_consent_for_target_runner() -> None:
    source_custodian, memory_id = build_demo_custodian()
    target_runner = "did:runner:migrated-agent"
    source_custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did=target_runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    source_custodian.grant(
        ConsentGrant(
            owner_did="did:plc:bob",
            grantee_runner_did=target_runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    envelope = export_migration_envelope_v1(
        custodian=source_custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did=target_runner,
    )
    staging = import_migration_envelope_v1(envelope=envelope)

    target_custodian = MemoryCustodian()
    receipt = activate_migration_staging_v1(
        staging=staging,
        target_custodian=target_custodian,
    )

    assert receipt.status == "activated"
    assert memory_id in target_custodian.memories
    decision = target_custodian.evaluate_access(
        AccessRequest(
            memory_id=memory_id,
            requester_runner_did=target_runner,
            purpose="marketing_analytics",
        )
    )
    assert decision.allowed is True


def test_activate_staging_is_idempotent_for_repeated_activation() -> None:
    source_custodian, memory_id = build_demo_custodian()
    target_runner = "did:runner:migrated-agent"
    source_custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did=target_runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    source_custodian.grant(
        ConsentGrant(
            owner_did="did:plc:bob",
            grantee_runner_did=target_runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    envelope = export_migration_envelope_v1(
        custodian=source_custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did=target_runner,
    )
    staging = import_migration_envelope_v1(envelope=envelope)
    target_custodian = MemoryCustodian()

    activate_migration_staging_v1(staging=staging, target_custodian=target_custodian)
    activate_migration_staging_v1(staging=staging, target_custodian=target_custodian)

    assert len(target_custodian.memories) == 1
    assert len(target_custodian.grants) == 2


def test_import_rejects_tampered_bundle_hash() -> None:
    custodian, _ = build_demo_custodian()
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did="did:runner:migrated-agent",
    )
    tampered_payload = envelope.model_dump(mode="python")
    tampered_payload["bundle"]["memories"][0]["content"] = "tampered"
    tampered = AMCPMigrationEnvelopeV1.model_validate(tampered_payload)

    try:
        import_migration_envelope_v1(tampered)
    except ValueError as exc:
        assert "bundle_sha256" in str(exc)
    else:
        raise AssertionError("Expected tampered bundle to fail hash verification.")


def test_manifest_accepts_placeholder_signature_list() -> None:
    custodian, _ = build_demo_custodian()
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did="did:runner:migrated-agent",
    )
    envelope.signatures.append(
        MigrationExportSignatureV1(
            signer_did="did:runner:coding-agent-v1",
            algorithm="none",
            signature="unsigned",
        )
    )
    staging = import_migration_envelope_v1(envelope)
    assert staging.receipt.migration_id == envelope.manifest.migration_id
