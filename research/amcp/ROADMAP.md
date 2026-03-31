# AMCP Roadmap (ATProto-inspired)

This roadmap captures the next design milestones for AMCP by borrowing proven ideas
from AT Protocol while preserving AMCP's purpose-bound memory governance semantics.

## Guiding principles

- User memory ownership first.
- Explicit consent first, least privilege by default.
- Migration integrity and auditability before feature expansion.
- Framework interoperability without policy drift.

## Current baseline (done)

- AMCP core policy: same-runner+original-purpose allow, cross-purpose explicit consent.
- Cooperative ownership with full-owner consent requirement.
- PydanticAI and LangGraph adapters.
- Migration Manifest v0.1 with staged import/activate lifecycle and tamper checks.

## P0: Security and interoperability foundation

### P0.1 Signature verification (v0.2)

Goal:

- Replace placeholder migration signatures with verifiable signatures.

Deliverables:

- Add signature algorithm support (target: `ed25519`).
- Sign migration manifest and bundle hash on export.
- Verify signatures on import with DID-to-key resolution.
- Add key rotation compatibility baseline.

Acceptance:

- Import rejects tampered payload even if counts match.
- Import rejects invalid signature and unknown signer.
- Tests cover valid signature, tamper, wrong key, rotated key.

### P0.2 AMCP Lexicon / schema registry (v0.2)

Goal:

- Prevent cross-app semantic drift for purpose/scope/reason fields.

Deliverables:

- Define canonical purpose taxonomy.
- Define canonical quarantine reason codes.
- Define schema versioning and compatibility policy.

Acceptance:

- Unknown purpose/scope are rejected or quarantined deterministically.
- Cross-framework adapters produce identical reason codes for same scenario.

### P0.3 Incremental migration protocol (v0.3)

Goal:

- Support reliable continuous migration/sync instead of full snapshots only.

Deliverables:

- Add checkpoint-based delta export (`since_checkpoint`).
- Add append-only migration event log.
- Add idempotent import replay guarantees.

Acceptance:

- Replaying the same delta is idempotent.
- Partial failure can resume from checkpoint without privilege expansion.

## P1: Identity and governance hardening

### P1.1 DID document resolution and key lifecycle

Goal:

- Align signer trust model with portable identity model.

Deliverables:

- DID doc resolver abstraction.
- Active/previous key tracking and key expiry handling.
- Verification policy for outdated keys.

Acceptance:

- Old key cannot sign new envelope after rotation cutoff.
- Historical envelope remains verifiable if policy allows.

### P1.2 Record linkage and provenance graph

Goal:

- Improve traceability for consent and memory lineage.

Deliverables:

- Add record reference fields (`parent_cid`, `related_cid`).
- Link revoke events to grant lineage.
- Add provenance query utilities.

Acceptance:

- Every active grant is lineage-traceable to a signed origin.
- Revoke events deterministically invalidate dependent grants.

### P1.3 Capability-style consent tokens

Goal:

- Replace broad grants with narrow, composable capabilities.

Deliverables:

- Purpose+scope+time-bounded capability token model.
- Optional delegation chain with no privilege escalation.

Acceptance:

- Delegation cannot exceed parent capability scope.
- Expired capability is enforced across adapters.

## P2: Open ecosystem and productization

### P2.1 Federation transport profile

Goal:

- Enable cross-service migration/activation with a stable wire protocol.

Deliverables:

- Minimal HTTP profile for stage/activate/receipt endpoints.
- Standard status machine (`staged`, `activated`, `rejected`, `rolled_back`).

Acceptance:

- Two independent implementations can stage/activate the same envelope.

### P2.2 Policy pack and algorithmic choice

Goal:

- Let users choose governance mode without breaking baseline safeguards.

Deliverables:

- Policy pack definitions (strict/collaborative/research).
- Explicit invariant tests preserving least-privilege boundaries.

Acceptance:

- Different policy packs change behavior only within declared bounds.

### P2.3 Verifiable audit export (optional transparency log)

Goal:

- Provide independent verifiability of policy decisions.

Deliverables:

- Redacted decision log format (hashes + reason codes + timestamps).
- Export tooling and validation checks.

Acceptance:

- Third-party verifier can validate decision sequence integrity without plaintext memory.

## Execution order recommendation

1. P0.1 Signature verification
2. P0.2 Lexicon/schema registry
3. P0.3 Incremental migration
4. P1.1 DID resolver + key lifecycle
5. P1.2 Provenance graph
6. P1.3 Capability tokens
7. P2.* ecosystem and transparency features

## Out-of-scope for this roadmap cycle

- Full cryptographic wallet UX.
- On-chain anchoring.
- End-to-end encrypted multi-party key ceremony.
