# Review code changes

Review the pending changes.

Review architecture of the pending changes' fitness to the [companion harness design](/docs/imate/companion_harness/DESIGN.md)

## Instructions

### Review

- Understand what the code does
- Critique architecture
- Check for bugs

### Enhance

- Propose architecture improvement to improve structural clarity
- Propose wholistic solution instead of duct-tape fixes

### Identify code smells

- If a simple changes requires scattered changes, that means
code that changes together are not grouped together
- If writing tests are complicated, that means interface is incoherent,
behaviors are not well abstracted
- If code is difficult to described in much shorter documentation,
that means the code lacks hierarchy.
- If you noticed refactoring opporutnity, add TODOs to code places that the refactoring should be applied.

## Alembic version files

- Skip reviewing these files

## GitHub issues & TODOs (followups)

- Update TODOs and their referenced GitHub issues if needed
- Add TODO for minor followups that are not required in this change, but is required according to larger-scope repo guidelines
- Create GitHub issues and add TODOs to track complex follow-ups
- Comment on discovered GitHub issues if changes are made advanced the issues' progress

## Data types

- Do not use dict in passing data between components
- Use `dataclass` for internal data structure (not facing users or external services)
- Use `Pydantic` models for interfacing with externals (users & external services like 3rd party http, cloud service etc.)

## References

- Consider [style rules](/.agents/guidelines/PY_STYLE_RULES.md)

## Checklist

- [ ] Intention is understood
- [ ] Confirm that changes match user intention
- [ ] Critique the architecture
- [ ] Tests are added if needed
- [ ] Reviwed code smells
- [ ] Changes passed tests, fix test failures if needed
- [ ] Referenced GitHub issues updated
