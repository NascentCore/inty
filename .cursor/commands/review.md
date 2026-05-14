# Review and Enhance

## Overview

As a fellow team member, review and revise the pending changes in the current conversation, and commit in the end.

## Instructions

- Respond with 1 sentence summary, do not list what you did.

## Steps

1. **Review**
   - Understand what the code does and its constraints (AGENTS.md, tests, existing patterns).
   - Critique architecture soundness.
   - Check for bugs.
   - NO defensive programming.

2. **Enhance**
   - Propose architecture improvement to improve structural clarity
   - Simplify code

3. **Double check**
   - After edits: re-read the diff, run relevant tests, and fix any new broken tests.

4. **Commit (mandatory closure)**
   - Skip only when the user said not to commit, or there is nothing to commit.
   - Invoke `/commit` to commit changes

## Checklist

- [ ] Intention is understood
- [ ] Confirm that changes match user intention, revise changes if needed
- [ ] Confirm that implementation architecture is sound, revise changes if needed
- [ ] Tests are added if needed
- [ ] Changes passed tests, fix test failures if needed
- [ ] **Changes committed and pushed to remote**
