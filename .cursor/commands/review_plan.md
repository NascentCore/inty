# Review plan in plan mode

If not in plan mode, do nothing and stop!

Review and revise the plan:

- The plan's objectives are reasonable
- The plan's logical design is sound
- The plan's implementation steps are sufficiently granular

## Use alembic cli to generate database version files

- After adding new models in orm/, use alembic skill to create new version file
- Never generate alembic version file

## Testing

- Plan should include writing and running tests.
- Tests are done at the key juncture between procedures of the plan.

## Refactoring

When refactoring, the implementation plan should following the following overall procedures:

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
