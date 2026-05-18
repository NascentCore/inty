# Code smells

Critique the code when encounter the follow situations:

- If a simple changes requires scattered changes, that means
  code that changes together are not grouped together
- If writing tests are complicated, that means interface is incoherent,
  behaviors are not well abstracted
- If code is difficult to described in much shorter documentation,
  that means the code lacks hierarchy.
- Over engineering: speculation, defensive programming, optionality, multiple alternatives, etc.
  - **Speculative knobs**: do not add new env vars, optional CLI flags, or extra optional parameters “just in case”;
    only add configurability the user explicitly requested.
  - **Enable/disable knob for new features**: just implement the features.
