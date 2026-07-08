# Run tests on compannion harness

Run the following tests one by one:

- CI tests
- Smoke tests
- REPL regression tests

Always reset `INTY_CONFIG_YAML` explicitly before each phase:

- CI / pytest phase: `export INTY_CONFIG_YAML=devops/config.yaml.test`
- Smoke / local Ops phase: choose and export the config that matches the running server, usually `devops/config.yaml.local` for companion harness smoke
- REPL regression phase: `export INTY_CONFIG_YAML=devops/config.yaml.regression_tests`

Do not rely on the current shell's previous `INTY_CONFIG_YAML`; regression config leaking into CI causes unrelated failures.

Investigate and fix all failed tests.

After all tests passed, update the associated PR with the test passed checkbox.
