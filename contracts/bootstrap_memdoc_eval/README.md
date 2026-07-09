# Bootstrap MemDoc eval scenarios

Repo-root-relative YAML consumed by `run_bootstrap_memdoc_eval.py`.

- `scenario_id`: unique matrix key; one fresh agent per `(scenario_id, policy)` cell
- `user_turns`: bootstrap-phase user script until `workspace_bootstrap_user_interactive_completed`
- `experience_profile`: optional round clarifying `companion_set_experience_profile`
- `golden_facts`: deterministic scorer markers
- `settled_turns`: fixed post-bootstrap USER_CHAT script for T2 checkpoints

Generated entirely by Cursor agent for Bootstrap MemDoc L1 eval (#3606).
