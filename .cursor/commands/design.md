# Design an effective solution

- Absolutely understand the purpose, /grill-me if needed
- Absolutely understand the problem, /grill-me if needed
- Absolutely be crystal clear about the objectives, /grill-me if needed
- Understand existing status-quo of the code base
- Come up with 1 sentence conceptual design
- Give bullet points of detailed design
- Define concepts (keep reference to existing ones)
- Define key class, functions with 1 sentence description and succinct doc string.
  - Describe how they interact to achieve the design objectives
  - Enum type has semantic of the values
- Keep scope focused on the core problem
- Think independently, be critical towards user's requests, suggestions, and other inputs.

## Procedure

- Identify the single most effective design after exploring a wide range of possible deisng option. List your rationale, and unselected options.
- Start by clarifying the highest-level objective, and then break down into logical hierarchy with each layer composed of orthogonal
  and loosely coupled concepts, and the higher-layer achieves its goals through composition of lower-layer components.

## Antipatterns to avoid

- **Over engineering**: speculation, defensive programming, optionality, multiple alternatives, etc.
  - **No speculative knobs**: do not add new env vars, optional CLI flags, or extra optional parameters “just in case”;
  only add configurability the user explicitly requested.
  - **Do not add enable/disable knob for new features**: just implement the features.
- Shallow wrapper, eg: function of only 1 line of actuall code
