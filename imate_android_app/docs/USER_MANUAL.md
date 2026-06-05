# iMate User Guide

> CREATED_BY_AGENT
> Counterpart to [docs/INTELLIMATE.md](../../docs/INTELLIMATE.md) (IntelliMate user-facing guide).

> TODO: If this doc is mirrored to Notion or another help center, add the canonical URL on the next line.
> Target public help URL: _TBD_

> If copied into the iMate official assistant system message, remove lines starting with `>`.

Plain-language help for **iMate** (`com.inty.imate`) end users. Technical implementation details stay in code and `imate_android_app/AGENTS.md`.

Terminology (draft):

- **iMate** = this Android app product (`com.inty.imate`).
- **IntelliMate** = separate app (`android_app/`); do not confuse in support copy.

<!-- TODO(follow-up): Align terminology with marketing and in-app strings. -->

## TL;DR

- **Install or update**: _TODO: Add Google Play listing or internal testing link when published._
- **Sign in**: _TODO: Describe Google / guest flow as implemented in iMate._
- **Main flow**: _TODO: Short map of primary screens (match actual bottom nav and product copy)._
- **Environments**: Release builds use production API base URL; debug uses dev URL (see `core` BuildConfig `API_BASE_URL`). _TODO: User-facing wording only; no raw URLs if not needed._

## App overview

_TODO: Screenshots and copy for each primary surface (navigation, chat, profile, settings). Mirror structure in INTELLIMATE.md only where iMate UX matches._

## Where do I go to...?

| Task | App path | Notes |
| --- | --- | --- |
| Start a realtime voice call | Chat → phone button in the top bar | Grant microphone permission when prompted. The call uses the same iMate and chat context as the text conversation. |

<!-- TODO(follow-up): Fill the table from real UX; link to FR or design doc if helpful. -->

## Troubleshooting

- **Voice call cannot hear you**: grant Microphone permission in Android system Settings → Apps → iMate → Permissions.
- **Voice call fails to connect**: check network connectivity and sign in again if your session has expired.
- **No reply audio**: end the call and start again; realtime voice depends on the backend Live Chat service being available.
