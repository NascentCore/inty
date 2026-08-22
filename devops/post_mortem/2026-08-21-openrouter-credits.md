<!-- CREATED_BY_AGENT -->

# 2026-08-21 OpenRouter credits depleted (investigation note)

Status: **open** — resume examination **2026-08-22** (human). Follow-up engineering still tracked in [issues/3888](https://github.com/NascentCore/inty/issues/3888). Related prior incident: [2026-08-19-prod-outage.md](./2026-08-19-prod-outage.md).

## Confirmed

- Prod VM / containers / TLS healthy; Android chat fails with generic toast because OpenRouter returns **402** (`openrouter_credits`), mapped to HTTP 500.
- Account (SXWL.AI org): `total_credits=1020` / `total_usage≈1020` at check time (balance ~0).
- IntelliMate Android / `inty-backend-prod` logged chat model: **`google/gemini-2.5-flash-lite`** (baked `/config.yaml` has no `free_user_chat_model`; pydantic default).
- OpenRouter usage chart (Aug 19–20 spike): spend dominated by **Kimi K3** (~$6.45 on Aug 20) and **DeepSeek V4 Pro** (~$2.16), with Flash Lite ~$0.02. Neither K3 nor V4 Pro appears in Inty repo wiring or prod/ops container logs for those days.

## Human action (2026-08-21 evening PT)

- Disabled an OpenRouter **API key not associated with IntelliMate** (suspected non-product consumer of the same org credits). Exact key label/hash not recorded here.
- Re-check tomorrow: credits/usage after disable, whether Android chat recovers after top-up, and whether K3/V4 Pro spend stops.

## Resume checklist

- [ ] OpenRouter Credits + Usage (by API key): confirm disabled key no longer spends; identify remaining keys.
- [ ] Top up SXWL.AI / `it@sxwl.ai` if still empty; retest Android `POST /api/v1/chat/completions/...`.
- [ ] Optionally create a management key for `GET /api/v1/activity` (prod app key cannot).
- [ ] Advance [issues/3888](https://github.com/NascentCore/inty/issues/3888) (balance alert + 402 mapping).
