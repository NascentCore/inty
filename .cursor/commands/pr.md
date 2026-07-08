# Create PR

Create a pull request for the current working branch

## Instructions

1. **Prepare branch**
   - Ensure all changes are committed
   - Ensure the working branch is up to date with the remote main branch.
   - Ensure the working branch is pushed to remote.

2. **Write PR title & description**
   - 输出中文 (output in Mandarin)
   - Summarize changes clearly in PR title
   - In PR description:
     - Describe changed behaviors from the user's perspective.
     - Include context and motivation.
     - **Link GitHub issues in the PR body** — `Closes #NNNN` when this PR completes an issue or accepted slice; `Refs #NNNN` for partial progress, epics, or follow-ups. Do not rely on a separate gate-doc issue table.
     - After merge, record slice progress as a **comment on each linked issue** (PR link, checklist delta, verification). Do not duplicate per-issue status in `COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`.

3. **Create PR**
   - Create the PR with the above title and description.
   - Enable auto-merge.

## Checklist

- [ ] All intended changes committed
- [ ] Working branch rebased and pushed
- [ ] PR title and description written
- [ ] PR is created on GitHub
- [ ] PR auto-merge is enabled

## Output

Just the PR URL, and title. Do not include anything else.
