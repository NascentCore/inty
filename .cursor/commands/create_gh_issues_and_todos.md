# Create GitHub issues and add TODOs

Create github issue(s) to track the the work in current conversation,
and then add TODOs in appropriate code places (referencing the github issues) to tie the code with the created GitHub issue(s).

- Create TODOs for minor changes, they are picked up by the cursor automation.
- Create GitHub issues for large & complex follow-ups, also reference the issue in TODOs placed at appropriate code places.
- Do not reference issues in AGENTS.md or skills' MD files

- GitHub issues should be in Mandarin (中文简体）TODOs are in English for consistency
- When creating issues, apply labels to distinguish between other potential related issues, and increase structuredness.
- Make sure to reference issues in TODOs to allow agent to trace from code to github issues. GitHub issues serve as more complete background.

- When categorizing tasks:
  - Include P0/P1/P2/P3 priority:
    P0 for issues directly affect users and have no workaround
    P1 for important work requires constant attention
    P2 for secondary issues derived from P0 P1
    P3 for book keeping and speculative works
  - Include S0/S1/S2/S3 for severity:
    S0 for critical impact on core functionality
    S1 for substantial impcat
    S2 for minor impact
    S3 for trivial impact
