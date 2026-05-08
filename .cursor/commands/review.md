# Review and Enhance

## Overview

Review the uncommited code changes made in the current conversation, fix/revise/enhance the changes, and finally call Cursor /commit command to commit changes.

## Steps

1. **Review**
   - Understand what the code does and its constraints (AGENTS.md, tests, existing patterns).
   - Critique architecture soundness.
   - Check for bugs.

2. **Enhance**
   - Propose architecture improvement to improve structural clarity

3. **Double check**
   - After edits: re-read the diff, run relevant tests, and fix any new broken tests.

## Checklist

- [ ] Intention is understood
- [ ] Confirm that changes match user intention, revise changes if needed
- [ ] Confirm that implementation architecture is sound, revise changes if needed
- [ ] Tests are added if needed
- [ ] Follows existing coding style and AGENTS.md, revise changes if needed
- [ ] Changes passed tests, revise changes if needed
- [ ] Invoke cursor command `/commit`
