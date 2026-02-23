# Review and Enhance

## Overview

Review the code in context (current file, selection, or diff) and then propose and apply targeted enhancements.
Focus on correctness, maintainability, simplicity, and alignment with project conventions.

## Steps

1. **Review**
   - Understand what the code does and its constraints (AGENTS.md, tests, existing patterns).
   - Critique architecture soundness.
   - Check for bugs.

2. **Enhance**
   - Propose architecture improvement to improve clarity
   - Suggest and implement improvements: readability, structure, naming.
   - Prefer small, clear edits.
   - Avoid changing behavior unless the user asks.
   - After edits: re-read the diff, run relevant tests, and fix any new broken tests.
   - Detect duplicate code: when possible, refactor duplicate code into reusable helper functions.

## Checklist

- [ ] android_app/docs/CHANGE_LOGS.md updated for user-visible changes in android_app/
- [ ] docs/INTELLIMATE.md updated for user-visibule changes in android_app/
- [ ] User intention understood
- [ ] Implementation architecture understood
- [ ] Architecture revised if needed
- [ ] Follows project style and AGENTS.md
- [ ] Tests updated if behavior or contract changed
