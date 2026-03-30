# AMCP minimal protocol test steps

This test guide verifies the `research/amcp` reference implementation.

## Goal

Confirm policy behavior:

1. Original purpose + same runner => allow.
2. Cross-purpose without explicit consent => deny.
3. Cross-purpose with only one co-owner consent => deny.
4. Cross-purpose with all co-owners consent => allow.
5. Revocation by one co-owner => deny again.

## Commands

From repo root:

```bash
source .venv/bin/activate
python research/amcp/main.py self-test
python research/amcp/main.py demo
python research/amcp/main.py export-demo --output /tmp/amcp_bundle.json
python -m json.tool /tmp/amcp_bundle.json >/dev/null
```

## Expected result

- `self-test` prints `AMCP self-test passed.`
- `demo` includes both `allowed=True` and `allowed=False` lines.
- Export command writes a valid JSON bundle with `protocol = "amcp"`.
