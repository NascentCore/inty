# Review plan in plan mode

If not in plan mode, do nothing and stop!

Review architecture of the pending changes' fitness to the [companion harness design](/docs/imate/companion_harness/DESIGN.md).

Make sure that the implementation plan meets the following objectives:

- The plan's problem to be solved are clearly defined and meaningful
- The plan's objectives are clear and reasonable
- The plan's logical design is sound
- The plan's implementation steps are sufficiently granular
  - Include data types definitions (with key doc string to describe the data type's role in the design) and core logics
- The plan's target state matches objectives

## Detailed review items

Check each item against the corresponding section in [plan.md](/.cursor/commands/plan.md):

- [ ] **Alembic** — plan includes alembic skill for new ORM models; no hand-written version files ([plan.md § Use alembic cli](/.cursor/commands/plan.md))
- [ ] **Testing** — plan includes tests at key junctures; smoke/regression coverage where applicable ([plan.md § Testing](/.cursor/commands/plan.md))
- [ ] **Refactoring** — refactoring steps follow implement → test → integrate → test → optional delete ([plan.md § Refactoring](/.cursor/commands/plan.md))
- [ ] **Layering** — no excessive abstraction; hierarchy has roughly 3 layers; prefer rewrite over wrapper stacking ([plan.md § Limited layering](/.cursor/commands/plan.md))
- [ ] **Architecture fitness** - fits the architecture design and common best practices (modularity, composability, encapsulation)

## References

- [plan.md](/.cursor/commands/plan.md) — implementation plan conventions
- When choosing from different options, consider the overall [companion harness design](/docs/imate/companion_harness/DESIGN.md)
