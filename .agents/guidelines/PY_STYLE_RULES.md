# Python Style Rules

- Define Pydantic models for input & output variables to group variables tied to the same entity.
  Like `(is_allowed, used_count, limit)` should be `QuotaCheckResult`.
