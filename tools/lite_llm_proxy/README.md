# LiteLLM On-Prem Proxy for OpenRouter

This folder provides a copy-paste setup for running an on-prem LiteLLM proxy that routes requests to OpenRouter, with:

- virtual API key creation (`/key/generate`)
- per-key quota (`max_budget`, `budget_duration`)
- per-key rate limits (`rpm_limit`, `tpm_limit`)
- key expiration (`duration`, including seconds like `604800s`)

## Files

- `.env.example`: required environment variables
- `docker-compose.yml`: LiteLLM + Postgres deployment
- `litellm_config.yaml`: model routing + default/upper-bound key policies
- `key_management_examples.sh`: helper commands for key create/update/info/delete

## 1) Configure env

Create `.env` from template and edit values:

`cp .env.example .env`

Required:

- `LITELLM_MASTER_KEY` (must start with `sk-`)
- `LITELLM_SALT_KEY`
- `POSTGRES_PASSWORD`
- `OPENROUTER_API_KEY`

Optional:

- `OPENROUTER_API_BASE` (defaults to `https://openrouter.ai/api/v1`)
- `OR_SITE_URL`
- `OR_APP_NAME`

## 2) Start services

From this directory:

`docker compose up -d`

Check health:

`docker compose ps`

LiteLLM endpoints:

- Proxy base URL: `http://localhost:4000`
- Admin UI: `http://localhost:4000/ui`

## 3) Generate keys with quota and expiration

Source helper script:

`source ./key_management_examples.sh`

Examples:

- Permanent key (no expiration): `generate_key_permanent`
- 1-week key (seconds): `generate_key_one_week`
- Update existing key limits: `update_key_limits sk-...`
- Inspect key: `get_key_info sk-...`
- List keys: `list_keys`
- Delete key: `delete_key sk-...`

## 4) Make a proxied OpenAI-compatible call

Replace `USER_KEY` first:

`USER_KEY=sk-...`

`curl -sS http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${USER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "or-gpt-4o",
    "messages": [{"role":"user","content":"Say hello in one short sentence."}]
  }'`

## Notes

- Keep `LITELLM_MASTER_KEY` private. It can create and manage all proxy keys.
- `duration` and `budget_duration` support units like `s`, `m`, `h`, `d`.
- To enforce org-wide policy, edit `litellm_settings.upperbound_key_generate_params`.
