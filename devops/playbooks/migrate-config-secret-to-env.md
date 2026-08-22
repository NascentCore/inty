<!-- CREATED_BY_AGENT -->

# Playbook: migrate config secret to env + GitHub Environment secret

Template for moving a secret from `devops/config.yaml.*` into a runtime env var injected by CI/CD. Replace placeholders before executing.

| Placeholder | Example (OpenRouter backend prod) |
|-------------|-----------------------------------|
| `<SECRET_NAME>` | OpenRouter API key |
| `<ENV_VAR>` | `OPENROUTER_API_KEY` |
| `<CONFIG_YAML_PATH>` | `devops/config.yaml.prod` |
| `<CONFIG_FIELD_PATH>` | `agent.api_key` |
| `<CONSUMER_SERVICE>` | `inty-backend-prod` |
| `<OTHER_CONSUMERS>` | `inty-ops-prod` (still on YAML until migrated) |
| `<WORKFLOW_FILE>` | `.github/workflows/build_and_deploy_backend.yml` |
| `<GITHUB_ENVIRONMENT>` | `prod` |
| `<1PASSWORD_ITEM>` | OpenRouter IntelliMate prod |
| `<SMOKE_COMMAND>` | chat WebSocket smoke / health check |
| `<FOLLOWUP_ISSUE_OPS>` | issues/3896 |
| `<FOLLOWUP_ISSUE_REMOVE_YAML>` | issues/3897 |

---

## Step 1 — Follow-up issues

**Objective**
- Track multi-consumer migrations and YAML field removal before disabling legacy secrets.

**Changes**
- Create issue for each remaining consumer still reading YAML (`<OTHER_CONSUMERS>`).
- Create issue to remove `<CONFIG_FIELD_PATH>` from all `config.yaml.*` after all envs inject `<ENV_VAR>`.
- Use `TODO(issues/<number>)` in code and YAML comments.

**Verification**
- Issue URLs accessible; ops-migration issue marked prerequisite for legacy secret disable/delete.

---

## Step 2 — Env override in config

**Objective**
- Runtime resolves secret from `<ENV_VAR>` without changing every call site.

**Changes**
- Add `<ENV_VAR>` constant and `AgentConfig` (or relevant model) validator: non-empty env overrides YAML.
- Mark YAML field `DEPRECATED`; reference remove-YAML issue.
- Add pytest: YAML only, env overrides, empty env no override, missing both fails validation.

**Verification**
- `uv run pytest tests/app/utils/test_config.py -q -k <filter>` passes.

---

## Step 3 — Shared YAML transition comments

**Objective**
- Single shared config file documents who uses env vs YAML during migration.

**Changes**
- Update `<CONFIG_YAML_PATH>` comments at `<CONFIG_FIELD_PATH>`:
  - `<CONSUMER_SERVICE>` uses `<ENV_VAR>` env override.
  - `<OTHER_CONSUMERS>` still use YAML value.
  - `TODO(issues/…)` for ops migration and YAML removal.
- Do not duplicate config files unless consumers cannot share one file.

**Verification**
- Comments list all consumers and follow-up issue numbers.
- Config values unchanged except comments (until all consumers migrated).

---

## Step 4 — Workflow inject secret

**Objective**
- `<GITHUB_ENVIRONMENT>` supplies `<ENV_VAR>` at container start.

**Changes**
- `<WORKFLOW_FILE>`: add `--env <ENV_VAR>=${{ secrets.<ENV_VAR> }}` to `docker run`.
- Update manual rebuild docs (e.g. `DEPLOYMENT_STATE.md`) with same env line; no real secret values.

**Verification**
- Workflow diff shows single new `--env` for target service only.
- Job `environment:` matches `<GITHUB_ENVIRONMENT>`.

---

## Step 5 — Local verification

**Objective**
- Prove env override and image bake before writing GitHub secret.

**Changes**
- `export <ENV_VAR>='<from <1PASSWORD_ITEM>>'` in shell only.
- Run unit tests and config import with `INTY_CONFIG_YAML=<CONFIG_YAML_PATH>`.
- Build image with same `CONFIG_FILE`; optional `--entrypoint python` import smoke (no `/start.sh`).
- Run `<SMOKE_COMMAND>` if external API call required.
- Unset env; do not commit secrets.

**Verification**
- Tests pass; resolved config equals env value, not YAML legacy value.
- Smoke succeeds; provider dashboard shows usage on new key label.
- `git diff` contains no secret material.

---

## Step 6 — GitHub secret and deploy

**Objective**
- Production `<CONSUMER_SERVICE>` runs on new secret.

**Changes**
- GitHub Settings → Environments → `<GITHUB_ENVIRONMENT>` → secret `<ENV_VAR>` from `<1PASSWORD_ITEM>`.
- Merge PR; `workflow_dispatch` deploy with `<GITHUB_ENVIRONMENT>`.
- Record image digest before deploy for rollback.

**Verification**
- Container env has `<ENV_VAR>` set (do not log value).
- `<SMOKE_COMMAND>` / prod URL succeeds.
- Provider usage attributes spend to new key.

**Rollback**
- Redeploy previous digest or manual `docker run` with env; ops consumers unaffected if not redeployed.

---

## Step 7 — Legacy secret retirement gate

**Objective**
- Disable/delete old secret only when no consumer reads it.

**Changes**
- Complete `<FOLLOWUP_ISSUE_OPS>` for each `<OTHER_CONSUMERS>`.
- Replace YAML legacy value with `__SET_VIA_<ENV_VAR>__` placeholder; redeploy all services baking that config.
- Observe provider usage 24h zero on legacy key → disable → 24h → delete.
- Update post-mortem / incident doc with dates.

**Verification**
- All consumers on env; repo and current images free of legacy secret.
- Legacy key deleted; prod healthy.

---

## Step 8 — Remove YAML field (follow-up)

**Objective**
- Delete transitional YAML field and override shim.

**Changes**
- Implement `<FOLLOWUP_ISSUE_REMOVE_YAML>`: remove field from all configs, remove override, single env resolver.

**Verification**
- `rg '<CONFIG_FIELD_PATH>|sk-…' devops/` clean for production paths.
