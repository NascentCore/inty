# Pydantic models for API endpoints

- Ops platform analytics schemas live under `app/schemas/analytics/` (e.g. user_analytics).
- Must keep consistent between data types here and
  [kotlin data types](/android_app/library/inty)
- Also keep consistent with [SqlAlchemy table models](/app/models/)
- Do not use `model_config` as field name in Pydantic Model objects,
  which conflicts with <https://docs.pydantic.dev/2.0/usage/model_config/>
