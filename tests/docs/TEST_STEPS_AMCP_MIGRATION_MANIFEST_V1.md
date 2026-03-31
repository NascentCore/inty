# AMCP Migration Manifest v0.1 test steps

This document verifies `research/amcp/migration.py` and its test suite.

## Goal

Confirm AMCP migration v0.1 behavior:

1. Export builds a verifiable manifest (`record_count`, `grant_count`, `bundle_sha256`).
2. Import validates manifest-bundle consistency.
3. Import quarantines grants that mismatch target runner.
4. Activation writes accepted memories/grants to target custodian.
5. Tampered envelope is rejected.

## Commands

From repo root:

```bash
research/amcp/.venv/bin/python -m pytest -q research/amcp/test_migration_manifest.py
```

## Expected result

- Pytest reports all migration-manifest tests passing.
- Manifest mismatch/tamper test raises `ValueError` as expected.

