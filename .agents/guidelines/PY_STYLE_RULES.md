# Python Style Rules

- Define Pydantic models for input & output variables to group variables tied to the same entity.
  Like `(is_allowed, used_count, limit)` should be `QuotaCheckResult`.
- Feature flag uses bool with positive semantic, eg.: enable_xxx (default true)
- Options use enum, like alternating code paths: INNER_TICK_MAINTENANCE, INTER_TICK_PROCATIVE_CHAT, etc.
