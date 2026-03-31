# AMCP: Agent Memory Custodian Protocol (minimal design)

AMCP is a minimal protocol for user-controlled and cooperative ownership of agent memory.
It is inspired by AT Protocol ideas: portable identity (`did:*`), portable data bundles, and
explicit permission records that are auditable and revocable.

## Problem

Agent runners often reuse user memory for secondary purposes without clear user control.
AMCP makes access policy explicit:

- If runner and purpose are exactly the original interaction context, access is allowed.
- For any other purpose, explicit user consent is required.
- For co-owned memory (multiple users), all owners must explicitly consent.

This supports both:

- **default usability** in the original use case, and
- **strict user control** for cross-purpose memory usage.

## Scope

This is a minimal reference design for research and prototyping:

- local in-memory policy engine,
- portable JSON export bundle,
- no network protocol, signatures, or key management yet.

## Roles

- **Owner**: user who owns memory (`owner_did`).
- **Runner**: agent runtime identity (`runner_did`).
- **Custodian**: policy engine that decides whether access is allowed.

## Core data model

### `MemoryRecord`

- `memory_id`
- `owner_dids: list[str]` (supports cooperative ownership, must be non-empty)
- `runner_did` (runner that created/uses this memory in default flow)
- `original_purpose` (e.g. `coding_assistant`)
- `content`, `tags`, `created_at`
- `cid`: SHA-256 over canonical JSON representation

### `ConsentGrant`

- `grant_id`
- `owner_did`
- `grantee_runner_did`
- `purpose`
- `scope`: `single_memory` or `all_memories_for_owner`
- optional `memory_id`
- `granted_at`, optional `expires_at`, optional `revoked_at`

### `AccessRequest`

- `memory_id`
- `requester_runner_did`
- `purpose`
- `requested_at` (audit metadata; authorization uses custodian decision time)

### `AccessDecision`

- `allowed: bool`
- `reason: str`
- `missing_owner_consents: list[str]`

## Access decision algorithm (minimal normative rule)

For a request `(memory_id, requester_runner_did, purpose)`:

1. Load `memory`.
2. If `requester_runner_did == memory.runner_did` and `purpose == memory.original_purpose`:
   - allow (`original-purpose fast path`).
3. Else:
   - evaluate grants at custodian decision time (`evaluated_at = now`), not caller-provided timestamps.
   - collect active, unexpired, matching grants from owners of that memory.
   - grant must satisfy `granted_at <= evaluated_at`.
   - if any owner is missing a matching grant:
     - deny and return missing owners.
   - otherwise allow.

In short:

- **Same runner + original purpose** => always available.
- **Anything else** => explicit consent from **every owner**.

## Cooperative ownership

When memory has multiple owners (e.g., conversation memory involving Alice + Bob):

- Consent is cooperative and non-transferable.
- One owner consenting is not enough.
- Revocation by one owner removes eligibility immediately for cross-purpose access.

## ATProto-inspired aspects

- DID-like identities for users/runners.
- Portable memory+consent bundle (`AMCPRepositoryBundle`) that can be exported/imported.
- Content-addressable memory record hash (`cid`) for integrity checks.

## Minimal reference implementation

File: `research/amcp/main.py`

CLI commands:

- `demo`: prints access decisions across key scenarios
- `self-test`: executes assertions for policy behavior
- `export-demo --output ...`: exports JSON bundle

## Framework integration architecture (LangGraph + PydanticAI)

To integrate AMCP with popular agent frameworks while keeping policy deterministic and auditable,
use a **port-adapter architecture**:

### Layer 1 — AMCP Core (framework-agnostic)

File: `research/amcp/core.py`

- owns canonical models: `MemoryRecord`, `ConsentGrant`, `AccessRequest`, `AccessDecision`
- owns policy engine: `MemoryCustodian.evaluate_access()`
- no framework imports

### Layer 2 — Adapter Ports

File: `research/amcp/adapters.py`

- defines framework-facing dependency carrier (`PydanticAIDeps`)
- converts framework tool calls into `AccessRequest`
- maps policy deny to framework-native control flow (for pydantic-ai, raise `ModelRetry`)
- defines LangGraph state and compiled graph builder for AMCP gating

### Layer 3 — Runtime adapters

- **PydanticAI adapter** (implemented): `create_pydantic_ai_amcp_agent()`
  - exposes `read_memory_with_amcp` tool
  - always runs policy check before memory read
  - records access attempts for audit
- **LangGraph adapter** (implemented): `build_langgraph_amcp_app()`
  - node split:
    - `policy_check_node`
    - `llm_node` (allowed path)
    - `consent_request_node` (denied path)
  - edge rule: denied -> consent node, allowed -> llm node
  - example entrypoint: `research/amcp/langgraph_example.py`

### Why this works

- AMCP policy remains single source of truth.
- Framework migration only changes adapter layer, not policy semantics.
- Audit trace is consistent across frameworks.

## PydanticAI tests

File: `research/amcp/test_pydanticai_amcp.py`

Covered cases:

1. original purpose read is allowed
2. cross-purpose read without consent is denied
3. cross-purpose read with all co-owner consents is allowed
4. expired grant cannot be bypassed with backdated request metadata

Run:

```bash
research/amcp/.venv/bin/python -m pytest -q research/amcp/test_pydanticai_amcp.py
```

## LangGraph tests

File: `research/amcp/test_langgraph_amcp.py`

Covered cases:

1. original purpose read is allowed and routes to `llm_node`
2. cross-purpose read without full consent routes to `consent_request_node`
3. cross-purpose read with all co-owner consents is allowed and returns memory content

Run:

```bash
research/amcp/.venv/bin/python -m pytest -q research/amcp/test_langgraph_amcp.py
research/amcp/.venv/bin/python research/amcp/langgraph_example.py
```

## AMCP Migration Manifest v0.1

File: `research/amcp/migration.py`

Purpose:

- provide a minimal, verifiable migration envelope for AMCP memory portability
- preserve policy semantics during migration (no implicit privilege expansion)

Core objects:

- `MigrationManifestV1`
  - `migration_id`, `source_runner_did`, `target_runner_did`, `snapshot_at`
  - `record_count`, `grant_count`, `bundle_sha256`
- `AMCPMigrationEnvelopeV1`
  - `manifest` + `bundle` + optional `signatures`
- `ConsentPortabilityPolicyV1`
  - `require_target_runner_match` (default `true`)
  - `allow_all_memories_scope` (default `false`)
- `ImportReceiptV1`
  - accepted/quarantined IDs + status (`staged` / `activated`)

Lifecycle:

1. `export_migration_envelope_v1(...)`
2. `import_migration_envelope_v1(...)` -> `MigrationStagingV1`
3. `activate_migration_staging_v1(...)` -> activated receipt

Safety semantics in v0.1:

- manifest count/hash mismatch => import fails
- grant bound to other runner => quarantine
- `all_memories_for_owner` scope => quarantine by default
- migration preserves strict least-privilege defaults

## Migration tests

File: `research/amcp/test_migration_manifest.py`

Covered cases:

1. happy path: export -> import(staged) -> activate
2. hash mismatch is rejected
3. mismatched-grantee grant is quarantined
4. `all_memories_for_owner` grant is quarantined by default

Run:

```bash
research/amcp/.venv/bin/python -m pytest -q research/amcp/test_migration_manifest.py
```

## Demo scenarios covered

1. Original purpose access by same runner => **allow**
2. Cross-purpose without consent => **deny**
3. Cross-purpose with only one co-owner consent => **deny**
4. Cross-purpose with all co-owner consents => **allow**
5. Cross-purpose after one owner revokes => **deny**

## Run

From repository root:

```bash
source .venv/bin/activate
pip install -r research/amcp/requirements.txt
python research/amcp/main.py demo
python research/amcp/main.py self-test
python research/amcp/main.py export-demo --output research/amcp/demo_bundle.json
```

## Future extensions

- Signature verification per grant and bundle.
- Capability delegation with bounded delegation chains.
- Fine-grained field-level masking and purpose taxonomies.
- Cross-agent network transport and compatibility profile.
