# Review plan in plan mode

If not in plan mode, do nothing and stop!

Review and revise the plan:

- The plan addresses the user request(s)
- The plan makes sound designs
- The plan's implementation procedure is well organized

## Guidelines

- Use Test-driven development (TDD) to write code.

## Use alembic cli to generate database version files

- After adding new models in orm/, use alembic skill to create new version file
- Never generate alembic version file

## Testing

- Plan should include writing and running tests.
- Tests are done at the key juncture between procedures of the plan.

## Refactoring or reorganize code

The implementation plan should following the following overall procedures:
1. implement the new design in code with minimal changes to the existing code
2. test the new code
2. integrate the new code into the existing code
3. tests: unit tests, smoke tests, manual tests
4. delete the old code

## Data types

- Do not use dict in passing data between components
- Use `dataclass` for internal data structure (not facing users or external services)
- Use `Pydantic` models for interfacing with externals (users & external services like 3rd party http, cloud service etc.)

## Limited layering

Limit the the number of layers in implementing a complex feature:

- When extending behaviors, prefer rewriting a new function and remove the old one, over extending the existing function and wrap them behind a new function with "more specific interface". The former sheds the unnecessary complexity, and the latter merely hides unnecessary complexity.

## Antipatterns to avoid

- **Over engineering**: speculation, defensive programming, optionality, multiple alternatives, etc.
  - **No speculative knobs**: do not add new env vars, optional CLI flags, or extra optional parameters “just in case”;
  only add configurability the user explicitly requested.
  - **Do not add enable/disable knob for new features**: just implement the features.
- Shallow wrapper, eg: function of only 1 line of actuall code
