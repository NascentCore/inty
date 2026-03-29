# TEST_STEPS_REPO_AGENT_PHASE1_CLI

## 1. Test Goal

Validate the Phase 1 `repo_agent` bootstrap can present itself directly to users
via CLI without external wrappers.

## 2. Success Criteria

Pass when all conditions are met:

1. `repo_agent` skeleton files exist under `identity/`, `self_model/`, `governance/`, and `memory/`.
2. CLI commands `whoami`, `capabilities`, `boundaries`, and `status` execute successfully.
3. CLI output includes mission/persona/constitution summaries and governance gate data.
4. CLI output is deterministic for same input (`status` command).

## 3. Test Commands

Run at repository root:

1. `test -f repo_agent/identity/mission.md`
2. `test -f repo_agent/self_model/capabilities.yaml`
3. `test -f repo_agent/governance/change_policy.yaml`
4. `test -f repo_agent/memory/decision_log.md`
5. `/workspace/.venv/bin/python -m repo_agent whoami`
6. `/workspace/.venv/bin/python -m repo_agent capabilities`
7. `/workspace/.venv/bin/python -m repo_agent boundaries`
8. `/workspace/.venv/bin/python -m repo_agent status`
9. `cmp <(/workspace/.venv/bin/python -m repo_agent status) <(/workspace/.venv/bin/python -m repo_agent status)`

## 4. Expected Results

1. File checks return exit code 0.
2. `whoami` prints mission, persona, and constitution snippets.
3. `capabilities` prints enabled capability IDs from `capabilities.yaml`.
4. `boundaries` prints deny/high-risk/allowed path policy and release gates.
5. `status` prints current phase and immediate next actions for rollout.
6. `cmp` returns exit code 0, proving deterministic `status` output.
