# Python Style Rules

- Group related I/O fields in Pydantic models (`QuotaCheckResult` not loose tuples).
- Feature flags: positive bool, `enable_xxx`.
- Log raw exception/vars — no f-string error prose.

## `StrEnum`

- `StrEnum` + `match/case`. No string literals for branch paths.
- Name: `{Concept}{Suffix}`. Never `*Enum`.
- Suffix = what axis you partition: **Kind** (category), **Mode** (switch), **Status**, **Role**, **Track**, **Source** — pick one that fits.
- Same noun, different axis -> different suffix (`ChannelKind` vs `GatewayKind`).
- Members: `SCREAMING_SNAKE`; wire/DB values stable snake (`APP_WS = "app_ws"`).
- Docstring: what axis; note member -> runtime type if non-obvious.
