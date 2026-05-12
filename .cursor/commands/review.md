# Review and Enhance

## Overview

Review uncommitted changes from the current conversation, fix or enhance them, **run verification**, then **`/commit`** unless the user explicitly asked not to commit.

## TL;DR (do not stop early)

Agents often stop after tests; **review is not done until `/commit` runs** (or the user said no git commit).

1. Review code + architecture
2. Enhance if warranted
3. Re-read diff, run relevant tests
4. **`/commit`** (see [`/.cursor/commands/commit.md`](/.cursor/commands/commit.md))

## Steps

1. **Review**
   - Understand what the code does and its constraints (AGENTS.md, tests, existing patterns).
   - Critique architecture soundness.
   - Check for bugs.

2. **Enhance**
   - Propose architecture improvement to improve structural clarity

3. **Double check**
   - After edits: re-read the diff, run relevant tests, and fix any new broken tests.

4. **Commit (mandatory closure)**
   - If the task was to implement or fix code, invoke Cursor command **`/commit`** after tests pass.
   - Skip only when the user said not to commit, or there is nothing to commit.

## Checklist

- [ ] Intention is understood
- [ ] Confirm that changes match user intention, revise changes if needed
- [ ] Confirm that implementation architecture is sound, revise changes if needed
- [ ] Tests are added if needed
- [ ] Follows existing coding style and AGENTS.md, revise changes if needed
- [ ] Changes passed tests, revise changes if needed
- [ ] **Invoked `/commit`**
- [ ] **git push to remote**
