# Review plan in plan mode

Do nothing and stop if not in plan mode!

Review and revise the plan:

- The plan addresses the user request(s)
- The plan makes sound designs
- The plan is straightforward

## Use alembic cli

- After adding new models in orm/, use alembic skill to create new version file
- Never generate alembic version file

## Testing

- Plan should include writing and running tests.

## Refactoring or reorganize code

The implementation plan should following the following overall procedures:
1. implement the new design in code with minimal changes to the existing code
2. test the new code
2. integrate the new code into the existing code
3. tests: unit tests, smoke tests, manual tests
4. delete the old code
