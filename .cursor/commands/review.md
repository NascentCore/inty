# Review change in the current conversation

## Overview

As a fellow team member, review and revise the pending changes in the current conversation.

## Instructions

### Review

- Understand what the code does
- Critique architecture
- Check for bugs
- Review based on [style rules](/.agents/guidelines/PY_STYLE_RULES.md)

### Enhance

- Propose architecture improvement to improve structural clarity

### Identify code smells

- If a simple changes requires scattered changes, that means
code that changes together are not grouped together
- If writing tests are complicated, that means interface is incoherent,
behaviors are not well abstracted
- If code is difficult to described in much shorter documentation,
that means the code lacks hierarchy.

## Checklist

- [ ] Intention is understood
- [ ] Confirm that changes match user intention
- [ ] Critique the architecture
- [ ] Tests are added if needed
- [ ] Reviwed code smells
- [ ] Changes passed tests, fix test failures if needed
