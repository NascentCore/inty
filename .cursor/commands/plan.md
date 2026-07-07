# Plan implementation

Must be in plan mode, if not, switch to plan mode first.

Add implementation details to a high-level design provided in the plan file.

The implementation details are handed off to a less intelligent subagent.

The major work is to fill in details given a sound and clear design.
So that the less intelligent subagent can focus on implementation,
not to lost objective and create unmaintainable code.

## Scoping

- Start with core & minimal plans
- Create github issues and add TODOs in code places, when the available information is not sufficient for a clear & concrete design.

## For [companion harness](/app/core/companion_harness/)

- Read [companion harness design](/docs/imate/companion_harness/DESIGN.md)
- Focus on architecture soundness, do not do duct-tape fixes

## Conventions

- Class & domain name: camel case like OutputQueue
- mechanism process: snake case like drain_output_queue
- Types/kinds and any enum-like semantic should use enum type, not str/integer or other primitive types

## Use alembic cli to generate database version files

- After adding new models in orm/, use alembic skill to create new version file
- Never generate alembic version file

## Testing

- Plan should include testing.
- Tests are done at the key juncture between procedures of the plan.
- Complex features should have smoke tests to cover the end-to-end process.
- User-facing changes should have regression tests added to repl regression tests,
  as repl regression tests are the only client we can reliably test.
  Weixin/WeChat Telegram are difficult to test in code.

## Refactoring

When refactoring, follow the procedures below:

1. implement the new design in code with minimal changes to the existing code
2. test the new code
3. integrate the new code into the existing code
4. test the integrated code
5. (optional) delete the old code

## Limited layering

Limit the number of layers in implementing a complex feature:

- When extending behaviors, prefer rewriting a new function and remove the old one, over extending the existing function and wrap them behind a new function with "more specific interface" or naming. The former sheds the unnecessary complexity, and the latter merely hides and accumulates unnecessary complexity.

## Comments for data types

- Add comments to describe data type and its fields semantic and designated usage scenarios, add member documentation on top of each field, not in data type docstring
