Generated entirely by Cursor agent.

# Cross-channel identity follow-ups

## Minimal invariant

- One canonical User.id has at most one active companion Agent.id.
- Channel identities must resolve to a canonical User.id before companion provisioning decides whether to reuse, create, or terminate an agent.
- Telegram, Weixin, App, and future channels are not assumed to be the same human until an account-linking flow proves they map to the same canonical User.id.

## GitHub issue drafts

Umbrella issue: #3491.

### Epic: Consistent identity across companion channels

- Objective:
  - Build a canonical identity layer so App, Telegram, Weixin, and future channels can bind to the same human user.
- Scope:
  - Channel identity registry keyed by channel and channel user id.
  - Account-linking flow from each channel to canonical User.id.
  - Conflict policy when one channel identity is already linked to another canonical user.
  - Migration/audit for existing guest users created per channel.
- Acceptance:
  - A proven same human receives the same active companion across channels.
  - Unlinked channel identities remain isolated and cannot accidentally merge.

### Issue: DB-enforced companion bond invariant

- Objective:
  - Make one canonical user to one active companion agent a database invariant.
- Scope:
  - Add companion bond persistence with active user and active agent uniqueness.
  - Route all companion onboarding through the bond service.
  - Add repair/audit script for duplicate active bonds or orphaned agents.
- Acceptance:
  - Concurrent onboarding cannot create two active companions for one canonical user.
  - Any code path bypassing the bond service fails at the database constraint.

### Issue: Shared companion provisioning service

- Objective:
  - Replace per-channel provisioning decisions with one service that resolves canonical identity, locks the companion bond, and returns the active scope.
- Scope:
  - Move Telegram and Weixin provisioning to the shared service.
  - Keep channel-specific transport/auth logic outside the service.
  - Emit structured logs for identity resolution, bond reuse, bond creation, and conflict.
- Acceptance:
  - Telegram, Weixin, and App bootstrap use the same user-agent invariant.
  - Tests cover idempotent onboard, concurrent onboard, and cross-channel reuse after explicit linking.

### Issue: Explicit companion reset and termination policy

- Objective:
  - Define the only product-approved path that can replace a user's active companion.
- Scope:
  - Terminated bond status and terminated_at semantics.
  - Product UX decision for how users request, confirm, and understand companion reset.
  - Whether old memory remains archived, hidden, exportable, or deleted.
  - Endpoint repointing behavior after reset.
- Acceptance:
  - A new active companion for a canonical user always terminates the previous active bond in the same transaction.
  - Old companion state is never silently reused by the replacement.
  - Ordinary channel onboarding never terminates an old companion as an implicit side effect.

### Issue: Product design for companion reset

- Objective:
  - Decide the user-visible semantics for replacing a long-term companion before backend reset implementation.
- Scope:
  - Reset entry points across App and chat channels.
  - Confirmation copy and emotional framing.
  - What the user can see, recover, export, or delete after reset.
  - Whether support/admin reset is allowed and how it is audited.
- Acceptance:
  - Backend reset API has a product-approved state transition and UX contract.
  - Implementation TODOs can reference the product decision instead of encoding ad hoc reset semantics.
