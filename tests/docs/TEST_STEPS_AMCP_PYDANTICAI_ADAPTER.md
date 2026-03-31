# AMCP + PydanticAI adapter test steps

This document verifies the AMCP framework adapter for PydanticAI in `research/amcp`.

## Goal

Confirm AMCP policy can gate memory access inside a PydanticAI tool call:

1. Original purpose read is allowed.
2. Cross-purpose read without explicit consent is denied.
3. Cross-purpose read with all-owner consent is allowed.

## Commands

From repo root:

```bash
research/amcp/.venv/bin/python -m pip install -r research/amcp/requirements.txt
research/amcp/.venv/bin/python -m pytest -q research/amcp/test_pydanticai_amcp.py
```

## Expected result

- Pytest shows all AMCP adapter tests passing.
- Denied case surfaces as `UnexpectedModelBehavior` due to `ModelRetry` budget exhaustion.
