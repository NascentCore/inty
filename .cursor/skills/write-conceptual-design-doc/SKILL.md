---
name: conceptual design
description: >-
  Write design doc docs from codebase recon,
  not by copying existing doc wording. Covers doc tiers, code discovery order,
  ASCII diagrams, Epic pointers, and self-check against source. Use when the user
  asks to write or update DESIGN.md, architecture overview, companion harness
  design doc, or docs/companion_harness documentation from code.
---

Three-layer:

- The first layer is the problem statement, goals, non-goals, and requirements, both functional and non-functional.
- The next layer is the functional specification, which describes precisely how the system will work from an external perspective.
- The third and final layer is the technical specification, which describes the internals.

Each section should follow from the previous. The design doc should justify to the reader (and author) that the problem is understood, the requirements are necessary and sufficient, the functional spec meets the requirements, and the technical spec implements the functionality and non-functional requirements.

As a corollary, if one section has a fatal flaw, there is no need to read on. If the problem is misunderstood, then the functional spec is likely wrong. If the functional spec doesn't meet the requirements, then the implementation is moot.

End the design doc with a section of all of the key points.
