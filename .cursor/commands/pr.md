# Create PR

## Overview

Create a well-structured pull request: ensure changes are committed and pushed, then open a PR with a clear description, following this repo’s conventions (see AGENTS.md).

## Steps

1. **Prepare branch**
   - Ensure all changes are committed (with a one-line summary and optional body describing the request and approach).
   - Push branch to remote.
   - Verify branch is up to date with the base (e.g. main).

2. **Write PR title & description**
   - Summarize changes clearly in PR title; prefer 中文 for title and description when it does not affect correctness.
   - Include context and motivation; reference any `<TASK>_REQUESTS.md` or other planning docs for large changes.
   - List breaking changes, config/env changes, and migration steps if any.
   - Add screenshots or steps for UI/behavior changes if helpful.

3. **Create PR**
   - Create the PR with the above title and description.

## Repo conventions (AGENTS.md)

- Small changes: include the user’s original request in the commit message (e.g. in body) and a short note on how it was handled.
- Large or new features: write the request into a `docs/reqs/<TASK>_REQUESTS.md` in the same area and reference it in the commit/PR.
- Do not add a separate summary markdown file for the change.

## Checklist

- [ ] All intended changes committed and pushed
- [ ] PR title and description written (中文 preferred)
- [ ] Breaking/config/migration called out if any
- [ ] Related issues linked if any
- [ ] Manual testing / test steps noted if relevant
