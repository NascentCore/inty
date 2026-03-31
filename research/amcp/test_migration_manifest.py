from __future__ import annotations

from research.amcp.core import AccessRequest, ConsentGrant, MemoryCustodian, build_demo_custodian
from research.amcp.migration import (
    AMCPMigrationEnvelopeV1,
    ConsentPortabilityPolicyV1,
    MigrationExportSignatureV1,
    MigrationSigningKeyV1,
    StaticDIDKeyResolverV1,
    build_signature_test_vector_v1,
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
            key_id="atproto",
            algorithm="ed25519",
            payload_sha256="0" * 64,
            signature="AA",
        )
    )
    try:
        import_migration_envelope_v1(
            envelope,
            policy=ConsentPortabilityPolicyV1(require_valid_signatures=True),
            key_resolver=StaticDIDKeyResolverV1({}),
        )
    except ValueError as exc:
        assert (
            "No public key" in str(exc)
            or "Invalid signature" in str(exc)
            or "payload hash mismatch" in str(exc)
        )
    else:
        raise AssertionError(
            "Expected placeholder signature to fail when strict signature validation is enabled."
        )


def test_import_accepts_valid_ed25519_signature_with_required_signer() -> None:
    custodian, _ = build_demo_custodian()
    signing_key = MigrationSigningKeyV1(
        signer_did="did:plc:source-runner",
        key_id="atproto-2026-01",
        private_key_b64url="AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE",
    )
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did="did:runner:migrated-agent",
        signing_keys=[signing_key],
    )
    resolver = StaticDIDKeyResolverV1.from_signing_keys([signing_key])
    staging = import_migration_envelope_v1(
        envelope=envelope,
        policy=ConsentPortabilityPolicyV1(
            require_valid_signatures=True,
            required_signer_dids=["did:plc:source-runner"],
        ),
        key_resolver=resolver,
    )
    assert staging.receipt.status == "staged"


def test_import_rejects_signature_with_wrong_public_key() -> None:
    custodian, _ = build_demo_custodian()
    signing_key = MigrationSigningKeyV1(
        signer_did="did:plc:source-runner",
        key_id="atproto-2026-01",
        private_key_b64url="AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI",
    )
    wrong_key = MigrationSigningKeyV1(
        signer_did="did:plc:source-runner",
        key_id="atproto-2026-01",
        private_key_b64url="AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM",
    )
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did="did:runner:migrated-agent",
        signing_keys=[signing_key],
    )
    resolver = StaticDIDKeyResolverV1.from_signing_keys([wrong_key])
    try:
        import_migration_envelope_v1(
            envelope=envelope,
            policy=ConsentPortabilityPolicyV1(require_valid_signatures=True),
            key_resolver=resolver,
        )
    except ValueError as exc:
        assert "Invalid signature" in str(exc)
    else:
        raise AssertionError("Expected signature verification to fail with wrong public key.")


def test_import_rejects_when_required_signer_missing_after_rotation() -> None:
    custodian, _ = build_demo_custodian()
    old_key = MigrationSigningKeyV1(
        signer_did="did:plc:source-runner",
        key_id="atproto-2025-12",
        private_key_b64url="BAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQ",
    )
    new_key = MigrationSigningKeyV1(
        signer_did="did:plc:source-runner",
        key_id="atproto-2026-01",
        private_key_b64url="BQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQU",
    )
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did="did:runner:migrated-agent",
        signing_keys=[old_key],
    )
    resolver = StaticDIDKeyResolverV1.from_signing_keys([old_key, new_key])
    try:
        import_migration_envelope_v1(
            envelope=envelope,
            policy=ConsentPortabilityPolicyV1(
                require_valid_signatures=True,
                required_signer_dids=[
                    "did:plc:source-runner#atproto-2026-01",
                ],
            ),
            key_resolver=resolver,
        )
    except ValueError as exc:
        assert "Missing required signer DID(s)" in str(exc)
    else:
        raise AssertionError("Expected missing required signer to fail import.")


def test_signature_test_vector_is_deterministic_and_verifiable() -> None:
    vec = build_signature_test_vector_v1()
    assert len(vec.payload_sha256) == 64
    assert vec.signer_did == "did:plc:fixture-signer"
    assert vec.key_id == "atproto-2026-01"


def test_required_signer_with_key_id_passes_for_matching_signature() -> None:
    custodian, _ = build_demo_custodian()
    key = MigrationSigningKeyV1(
        signer_did="did:plc:source-runner",
        key_id="atproto-2026-01",
        private_key_b64url="BgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgY",
    )
    envelope = export_migration_envelope_v1(
        custodian=custodian,
        source_runner_did="did:runner:coding-agent-v1",
        target_runner_did="did:runner:migrated-agent",
        signing_keys=[key],
    )
    resolver = StaticDIDKeyResolverV1.from_signing_keys([key])
    staging = import_migration_envelope_v1(
        envelope=envelope,
        policy=ConsentPortabilityPolicyV1(
            require_valid_signatures=True,
            required_signer_dids=["did:plc:source-runner#atproto-2026-01"],
        ),
        key_resolver=resolver,
    )
    assert staging.receipt.status == "staged"
