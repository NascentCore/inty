# Plan implementation

Must be in plan mode, if not, swith to plan mode first.

Draft a solid implementation plan for a sound and clear design.

## Scoping

- Start with core & minimal, and create github issues and add TODOs in code places, whenever run into situations where the available information is not sufficient for a clear & concrete design.

## For [companion harness](/app/core/companion_harness/)

When working on [companion harness](/app/core/companion_harness/)

- Read [companion harness design](/docs/imate/companion_harness/DESIGN.md)
- Focus on architecture soundness, do not do duct-tape

## Conventions

- Class & domain name: camel case like OutputQueue
- mechanism process: snake case like drain_output_queue

## Use alembic cli to generate database version files

- After adding new models in orm/, use alembic skill to create new version file
- Never generate alembic version file

## Testing

- Plan should include testing.
- Tests are done at the key juncture between procedures of the plan.
- Complex featuers should have smoke tests to cover the end-to-end process.
- User-facing changes should have regression tests added to repl regression tests,
  as repl regression tests are the only client we can reliably test.
  Weixin/WeChat Telegram are difficult to test in code.

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
