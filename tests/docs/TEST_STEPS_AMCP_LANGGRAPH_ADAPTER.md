# AMCP + LangGraph adapter test steps

This document verifies the AMCP framework adapter for LangGraph in `research/amcp`.

## Goal

Confirm AMCP policy can gate memory access inside LangGraph flow:

1. Original purpose read is allowed and routes to allowed path.
2. Cross-purpose read without explicit consent is denied and routes to consent path.
3. Cross-purpose read with all-owner consent is allowed.

## Commands

From repo root:

```bash
research/amcp/.venv/bin/python -m pip install -r research/amcp/requirements.txt
research/amcp/.venv/bin/python -m pytest -q research/amcp/test_langgraph_amcp.py
research/amcp/.venv/bin/python research/amcp/langgraph_example.py --purpose coding_assistant
research/amcp/.venv/bin/python research/amcp/langgraph_example.py --purpose marketing_analytics --grant-all-owners
```

## Expected result

- Pytest shows all LangGraph adapter tests passing.
- Example command without grants prints a denied decision and missing owners.
- Example command with `--grant-all-owners` prints allowed decision and memory content.
