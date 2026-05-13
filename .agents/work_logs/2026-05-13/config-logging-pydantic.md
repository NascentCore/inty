Migrated `LoggingConfig` from dataclass to Pydantic `BaseModel` as the first config migration maintenance task.

- Selected `P2_CONFIG_DATACLASS_PYDANTIC_MIGRATION.md` because the P1 maintenance file has no actionable TODO.
- Converted `LoggingConfig` to `BaseModel` with ignored extra YAML keys and preserved colorized log format behavior through an after-validator.
- Updated `load_config` to construct `LoggingConfig` through `model_validate`.
- Marked `CFG-PYD-01` complete in the maintenance task file.

Follow-ups:

- Continue with `CFG-PYD-02` (`SecurityConfig`) in a later maintenance iteration.
