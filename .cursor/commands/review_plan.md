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

- Use alembic cli to generate database version files
- Sufficient testing that gurantees correctness of the changes
- Refactoring plan is well-organized according to best practices
- No excessive layers in the abstration hierarchy. The abstraction hierarchy has roughly 3 layers

## References

- When choosing from different options, consider the overall [companion harness design](/docs/imate/companion_harness/DESIGN.md)
