---
name: move-config-entries
description: >-
  Move or rename Inty config fields in app/utils/config.py across schema, YAML,
  callers, tests, and legacy cleanup. Use when relocating config keys, nesting
  flat fields, renaming config paths, or removing duplicate app.features.* entries.
---

# Move config entries

Config moves are cross-cutting: schema, YAML, callers, tests, and docs must move together.

## Start Here

- Write the exact field map: `old.dotted.path` -> `new.dotted.path`.
- Choose one compatibility mode:
  - Hard cut: preferred when repo YAML can migrate in the same change.
  - Temporary dual-read: only when deployed config cannot flip atomically; remove it in the same branch or a named follow-up.
- Group fields by behavior, not by old prefix. Related timing fields often deserve nested models.

## Checklist

- [ ] 1. Schema: add nested models + fields on target parent
- [ ] 2. Validators: move or extract; update config_path strings in errors
- [ ] 3. Callers: grep old paths; switch to new paths
- [ ] 4. YAML: devops/config.yaml.*, config.yaml, test fixtures
- [ ] 5. Tests: schema tests + load_config fixtures
- [ ] 6. Legacy removal: delete old fields, reconcile, dead docs
- [ ] 7. Verify: grep + pytest

## Schema

- Add nested `BaseModel` classes under the target parent with `model_config = ConfigDict(extra="ignore")`.
- Put defaults and `Field(description=...)` on the new fields.
- Move validation onto the new model. Extract module-level `_normalize_*` / `_validate_*` helpers when reused.
- Error messages and `config_path` strings must name the new path only.
- Update helper-module docstrings/comments that mention the old path.

## Callers And YAML

Run focused greps from repo root:

```bash
rg 'app\.features\.<old_prefix>|features\.<old_field>|cfg\.app\.features\.<field>' \
  app backend tests tools --glob '*.py'
rg '<old_yaml_key>' devops docs .cursor/skills config.yaml
```

- Replace runtime accessors with the new path.
- Move overrides in `devops/config.yaml.*` and root `config.yaml`.
- Remove old YAML keys. With `extra="ignore"`, stale keys may silently do nothing.
- Match nesting to the Pydantic tree (YAML indent = model depth).

## Tests

- Add direct model tests for defaults and validation.
- Add `load_config` tests with YAML under the new path.
- Remove tests that only asserted legacy paths or reconcile sync; add harness-path equivalents.
- Fixture trap: empty `features:` parses as `null`; use `features: {}` when the block must exist.

```bash
uv run pytest tests/app/utils/test_config.py -q
```

## Cleanup

- Delete old fields, old validators, and any reconcile helpers.
- Delete or rewrite docs/skills that teach old paths.
- Run a final grep over runtime code, YAML, tests, docs, and skills.
- Run focused tests plus affected smoke tests.

## Guardrails

- Behavior config lives in YAML (`config.yaml` / `devops/config.yaml.*`); logging config may use env vars.
- No new env vars or optional flags unless explicitly requested.
- Do not edit `AGENTS.md`.
- Keep the diff to moving fields, validators, callers, YAML, and tests.

For the companion harness example, see [REFERENCE.md](REFERENCE.md).
