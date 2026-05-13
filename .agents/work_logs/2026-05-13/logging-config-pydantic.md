Summary: Migrated `LoggingConfig` from dataclass to Pydantic `BaseModel` as the first config migration maintenance task.

- Picked `CFG-PYD-01` from `.agents/maintenance/P2_CONFIG_DATACLASS_PYDANTIC_MIGRATION.md` because the P1 maintenance file has no actionable TODO.
- Preserved colorized logging format behavior with a Pydantic `model_validator(mode="after")`.
- Updated `load_config` to construct the logging section through `LoggingConfig.model_validate`.
- Marked `CFG-PYD-01` complete in the maintenance task table.
- Verified with `uv run pytest tests/app/utils/test_config.py tests/app/core/test_logging.py`.

Follow-ups:

- Continue the config migration with `CFG-PYD-02` (`SecurityConfig`).
