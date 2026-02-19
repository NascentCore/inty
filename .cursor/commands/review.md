# Review and Enhance

## Overview

Review the code in context (current file, selection, or diff) and then propose and apply targeted enhancements. Focus on correctness, maintainability, and alignment with project conventions.

## Steps

1. **Review**
   - Understand what the code does and its constraints (AGENTS.md, tests, existing patterns).
   - Check for bugs, edge cases, error handling, and security/sensitivity (e.g. no leaked secrets).
   - Note duplication, unclear names, magic constants, and missing tests or docs.

2. **Enhance**
   - Suggest and implement improvements: readability, structure, naming, tests, and docs.
   - Prefer small, clear edits.
   - Avoid changing behavior unless the user asks.
   - After edits: re-read the diff, run relevant tests, and fix any new broken tests.

## Checklist

- [ ] Behavior and edge cases understood
- [ ] No unintended side effects or API changes
- [ ] Follows project style and AGENTS.md
- [ ] Tests/docs updated if behavior or contract changed
