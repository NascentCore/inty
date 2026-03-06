# Cache Optimization Plan for `app/` Database Access

## 1. Goal

Reduce database pressure in the Python backend by caching high-frequency, read-heavy access paths in `app/`, while keeping correctness and operability clear.

Primary goals:
- Lower read QPS to Postgres (especially `users`, `user_subscriptions`, `subscription_usage`, `chat_history`).
- Reduce repeated aggregation queries in hot request paths.
- Keep stale-data windows explicit and controlled via TTL + invalidation.

## 2. Scope

In scope:
- API dependency authentication path
- Subscription and quota checks
- Chat list preview and chat-related metadata reads
- User profile summary-style reads (`/users/me`)
- Push and voice hot-path DB reads/writes that can be amortized

Out of scope (this phase):
- Full schema redesign
- Replacing business logic semantics
- Non-DB optimizations (model serving, external API latency)

## 3. Current State Summary

- Existing cache is mostly in-process memory (`InMemoryCache`) with TTL.
- Current cache coverage focuses on:
  - user info block
  - chat session info
  - lightweight agent config
  - system settings key-value reads
- Multi-instance deployments do not share cache state, so cache hit ratio degrades across replicas.

## 4. Prioritized Optimization Backlog

## P0 (Highest ROI)

### P0-A: Auth user snapshot cache

Problem:
- `get_current_user` queries DB on almost every authenticated request.

Plan:
- Cache key: `user_auth_snapshot:{user_id}`
- Value: minimal auth fields (`id`, `deleted_at`, `is_active`, `is_superuser`, optional version marker)
- TTL: 30-120 seconds

Invalidation triggers:
- user profile update
- user soft-delete/reactivation
- privilege changes

Expected impact:
- Significant reduction on repeated `select(User)` reads in endpoint-heavy traffic.

---

### P0-B: Subscription status/request-scope reuse

Problem:
- In single request flows, subscription state is re-queried multiple times.
- Cross-request, subscription status and current-subscription checks are frequent.

Plan:
1. Add request-scope memoization first (zero stale risk in-request).
2. Add short TTL cache:
   - `user_sub_status:{user_id}`
   - optional `user_current_subscription:{user_id}`
   - TTL: 30-120 seconds

Invalidation triggers:
- purchase verification success
- subscription webhook update/refund/cancel/recover paths
- manual admin subscription mutation

Expected impact:
- Lower repetitive reads on `user_subscriptions` and related joins.

---

### P0-C: Usage aggregation cache (`subscription_usage`)

Problem:
- High-frequency SUM/COUNT aggregations for 24h/day windows in limit checks:
  - chat
  - voice_generation
  - image_generation/background_generation
  - music_generation
  - live_chat duration

Plan:
- Cache keys per window:
  - `usage_24h:{user_id}:{usage_type}`
  - `usage_day:{user_id}:{usage_type}:{yyyy-mm-dd}` (when needed)
- TTL: 10-60 seconds
- Prefer write-through/write-behind update on `record_usage` to reduce DB re-aggregation.

Invalidation triggers:
- `record_usage` success path updates corresponding keys
- fallback TTL expiration for safety

Expected impact:
- Major drop in repeated aggregate SQL load on hot endpoints.

---

### P0-D: `/users/me` summary cache

Problem:
- `/users/me` combines connector count + user actions.
- User actions include multiple DB checks (new user, total chats, feedback state, latest feedback push record).

Plan:
- Cache key: `user_profile_summary:{user_id}`
- Value: connector_count + actions payload
- TTL: 30-120 seconds

Invalidation triggers:
- new chat usage record
- feedback submission
- feedback action history insert
- account state changes

Expected impact:
- Reduce repeated multi-query summary fetches on profile polling.

## P1 (High value, after P0)

### P1-A: Chat preview metadata cache

Problem:
- Chat list path may perform per-chat last-message / has-user-message checks against `chat_history`.

Plan:
- Cache key: `chat_preview:{session_id}`
- Value: `last_message`, `last_message_time`, `has_user_messages_ever`
- TTL: 30-120 seconds
- Optionally migrate to write-time denormalized columns on `chats` later.

Invalidation triggers:
- on user/agent message insert/delete (chat history mutation)

---

### P1-B: Surprise Snap unlocked-id set cache

Problem:
- Message list flow loads unlocked message IDs repeatedly per user.

Plan:
- Cache key: `surprise_unlock_ids:{user_id}`
- Value: set/list of unlocked message IDs
- TTL: 1-5 minutes

Invalidation triggers:
- unlock success -> targeted invalidation or append update

---

### P1-C: Creator stats cache in agent detail

Problem:
- Creator public-agent stats queried repeatedly.

Plan:
- Cache key: `creator_stats:{creator_id}`
- TTL: 5-30 minutes

Invalidation triggers:
- public agent create/update visibility/delete

---

### P1-D: Subscription plans list cache

Problem:
- plan list is low-churn but frequently requested.

Plan:
- Cache key: `subscription_plans:active`
- TTL: 10-60 minutes

Invalidation triggers:
- plan create/update/activate/deactivate

## P2 (Nice-to-have)

### P2-A: Push generation path user/subscription read amortization

- In worker/batch paths, use short-lived local memoization per batch/user.

### P2-B: Voice cache hit-stat write amortization

- Cache-hit DB updates (`hit_count`) currently write frequently.
- Batch flush hit counters periodically to reduce write amplification.

## 5. Cache Architecture Evolution

Phase 1 (fastest):
- Keep existing in-process cache.
- Add request-scope memoization and short TTL keys in hot services.

Phase 2:
- Introduce Redis as L2 shared cache across replicas.
- Keep local in-process cache as L1 for ultra-low latency.

Recommended model:
- L1: process memory (current `InMemoryCache`)
- L2: Redis (shared)
- DB: source of truth

## 6. Consistency Policy

Use explicit policy by data class:
- Stronger consistency (auth/permission/subscription state): short TTL + active invalidation.
- Eventual consistency acceptable (stats/recommendation/profile summary): longer TTL allowed.

Rule:
- Any write path that changes cached fields must either:
  1) invalidate key(s), or
  2) update cached value atomically.

## 7. Rollout Plan

1. Implement P0-A (auth snapshot) + P0-B request-scope reuse.
2. Implement P0-C usage aggregation cache.
3. Implement P0-D `/users/me` summary cache.
4. Implement P1 set (chat preview, unlock set, creator stats, plans list).
5. Introduce Redis L2 and migrate hottest keys first.

For each step:
- ship behind config switches
- observe metrics 24-72h
- then expand scope

## 8. Observability and Success Metrics

Track before/after for each rollout:
- DB QPS by table/query family
- p95/p99 latency for:
  - `/api/v1/chat/completions`
  - `/api/v1/chats/*`
  - `/api/v1/users/me`
  - subscription-related endpoints
- cache hit ratio per key family
- stale-read incident count (if any)

Target trend:
- meaningful DB read reduction on `users`, `user_subscriptions`, `subscription_usage`, `chat_history`
- no regression in correctness checks

## 9. Risks and Guardrails

Risks:
- stale privilege/subscription state
- partial invalidation bugs
- memory growth due to unbounded key cardinality

Guardrails:
- strict TTL ceilings on user-scoped keys
- bounded key design and periodic cleanup
- centralized helper methods for cache set/get/invalidate
- log cache hit/miss at sampled rate for validation

## 10. Implementation Notes

- Keep key naming conventions stable and documented.
- Prefer typed cache payload schemas where practical.
- Start with minimal payload snapshots; avoid caching entire ORM objects.
- Ensure all new caches have:
  - clear owner
  - explicit invalidation points
  - metric instrumentation
