# Review plan in plan mode

If not in plan mode, do nothing and stop!

Review and revise the implementation plan:

- The plan's objectives are clear and reasonable
- The plan's logical design is sound
- The plan's implementation steps are sufficiently granular
  - Include data types definitions (with key doc string to describe the data type's role in the design) and core logics
- The plan's target state matches objectives

Review architecture of the pending changes' fitness to the [companion harness design](/docs/companion_harness/DESIGN.md)

## Use alembic cli to generate database version files

- After adding new models in orm/, use alembic skill to create new version file
- Never generate alembic version file

## Testing

- Plan should include testing.
- Tests are done at the key juncture between procedures of the plan.
- Complex featuers should have smoke tests to cover the end-to-end process.
- User-facing changes should have manual tests.

## Refactoring

When refactoring, follow the procedures below:

1. implement the new design in code with minimal changes to the existing code
2. test the new code
2. integrate the new code into the existing code
3. test the integrated code
4. (optional) delete the old code

## Limited layering

Limit the the number of layers in implementing a complex feature:

- When extending behaviors, prefer rewriting a new function and remove the old one, over extending the existing function and wrap them behind a new function with "more specific interface" or naming. The former sheds the unnecessary complexity, and the latter merely hides and accumlates unnecessary complexity.

## References

- When choosing from different options, consider the overall [companion harness design](/docs/companion_harness/DESIGN.md)
