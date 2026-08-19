# Package, module, and file organization

Guidelines for placing code in the right package and keeping boundaries clear.
Grounded in companion harness layout ([ARCH.md](/docs/imate/companion_harness/ARCH.md))
and the `system_messages.py` move from `companion/prompts/` to `prompting/`.

## Split by responsibility, not by call chain

- Keep **content assets** separate from **assembly logic**.
  - Example: `companion/prompts/*.md` are doctrine/capability seed files (what text exists).
  - Example: `prompting/system_messages.py` builds the system prefix (how text is composed into an LLM request).
- Do not park assembly code next to static assets just because one module calls the other.

## Document each package role in `__init__.py`

- The package docstring should state what belongs here and what does not.
- Example: `companion/prompts/` holds MD seeds only; `prompting/` holds system-message stack assembly (`bundle`, `tracks`, `system_messages`).

## Respect layer direction in imports

- Outer orchestration (turn pipeline, `prompt_stack`, `prompt_builder`) imports inner leaf packages (`prompting/`, `memory/`, `tools/`).
- Leaf packages may import shared context types (e.g. `companion.models`) but must not own turn orchestration.
- Match import style to layer crossing: prefer absolute imports across package boundaries
  (`from app.core.companion_harness.prompting.system_messages import ...`).

## Co-locate related assembly code

- Keep slice builders, bundle types, and track composers in the same leaf package when they form one assembly pipeline.
- Avoid leaf-to-leaf imports that skip the package that owns the concern (e.g. `tracks` importing from `companion/prompts` for slice helpers).

## Mirror source layout in tests

- Unit tests for a module live under the same relative path in `tests/`.
  - Example: `tests/.../prompting/test_system_messages.py` for `prompting/system_messages.py`.
- Cross-module integration tests stay near the orchestrator under test
  (e.g. `tests/.../companion/test_system_messages.py` for `prompt_stack` integration).

## Update docs and skills when paths move

- Update architecture docs (`ARCH.md`, `MEMORY_STORE.md`), module docstrings, and `.cursor/skills/` references in the same change.
- Run a repo search for old paths before merging; stale references confuse humans and agents.

## Prototype: clarity over backward compatibility

- Do not add re-export shims at old import paths unless explicitly required.
- Prefer one canonical path, update all callers, and verify with search (`rg`) for zero stale imports.

## Expect rename/modify merge conflicts on file moves

- When you move a file, other branches may still edit it at the old path (e.g. comment or TODO hygiene).
- Git often auto-merges content into the new path; conflicts are usually path differences, not conflicting design intent.
- After merge, run tests for affected modules.

## Three questions before placing new code

1. Is this a **content asset** or **assembly logic**?
2. Is it **leaf** (prompting, memory, tools) or **orchestration** (companion turn execution, loops)?
3. Should tests target **module contract** or **cross-module integration**?

Answer these before choosing a directory.
