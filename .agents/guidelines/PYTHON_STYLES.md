# Python Style Rules

- When several fields belong together, put them in a Pydantic model — not a tuple or a long list of function parameters.
- Feature flags are positive booleans: `enable_xxx`, not `disable_xxx`.
- In logs, pass the exception or variables directly. Do not craft a custom error sentence in an f-string.

## Naming enums

Use `StrEnum` for fixed choices. Branch with `match/case`, not string literals or bool pairs.

**Type name:** say what you are classifying, then how you are classifying it.

- Good: `ChannelKind`, `QueueStatus`, `UserTurnLlmLoopMode`
- Bad: `ChannelEnum` (redundant), bare `Channel` (collides with runtime classes)

**Suffix** picks the angle:

- **Kind** — what category something is (`ChannelKind`, `CompanionGuestAgentKind`)
- **Mode** — which behavior is on (`UserTurnLlmLoopMode`)
- **Status** — lifecycle state (`QueueStatus`)
- **Role**, **Track**, **Source** — same idea: suffix names the dimension

Same word, different dimension → different suffix. Example: `ChannelKind` (which medium) vs future `GatewayKind` (which integration class).

**Members:** `SCREAMING_SNAKE`. If stored in DB or on the wire, use a stable lowercase value: `APP_WS = "app_ws"`.

**Docstring:** one line on what the enum classifies. Comment a member when its meaning or wire value is not obvious.
