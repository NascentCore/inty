# Design an effective solution

Must be in plan mode, if not, switch to plan mode first.

Produce an abstract design that achieves the objective and fit into the existing architecture of the repo.

Avoid going into details of actual code changes, in order to avoid distractions. Try to work at highest level of abstraction possible.

## General instructions

- Think independently, be critical towards user's requests, suggestions, and other inputs.
- Absolutely understand the purpose, /grill-me if needed
- Absolutely understand the problem, /grill-me if needed
- Absolutely understand the objectives, /grill-me if needed
- Understand existing status-quo of the code base
- Come up with 1 sentence summary of your design
- Describe your conceptual design
- Define key class, functions with 1 sentence description and succinct doc string.
  - Describe how they interact to achieve the design objectives
  - Enum type has semantic of the values
- Keep scope focused on the core problem
- Only when the user explicitly requests configurability, use repo config mechanisms [`config.py`](/app/utils/config.py); cross-field moves see [move-config-entries skill](/.cursor/skills/move-config-entries/SKILL.md))

## Preferred architecture patterns

- Prefer composable architecture at each abstract layer
- Prefer hierarchical, i.e., higher-layer is inherently more abstract of the immediate layer

## Procedure

- If direction is not yet converged, run `/brainstorm` or `/grill-me` before proposing alternatives
- Start by clarifying the highest-level objectives, and then break down into logical hierarchy with each layer composed of orthogonal
  and loosely coupled concepts, and the higher-layer achieves its goals through composition of lower-layer components.
- Propose up to 3 alternative designs
- Identify the single most effective design after exploring a wide range of possible design option. List your rationale, and unselected options.

### Refactoring

When doing refactoring, follow the procedures below:

1. implement the new design in code with minimal changes to the existing code
2. test the new code
3. integrate the new code into the existing code
4. test the integrated code
5. (optional) delete the old code

## Antipatterns to avoid

- **Over engineering**: speculation, defensive programming, optionality, multiple alternatives, etc.
  - **No speculative knobs**: do not add new env vars, optional CLI flags, or extra optional parameters “just in case”;
  only add configurability the user explicitly requested.
  - **Do not add enable/disable knob for new features**: just implement the features.
- Shallow wrapper, eg: function of only 1 line of actual code
