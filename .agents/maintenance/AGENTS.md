# Regular maintenance tasks

**Maintenance tasks of the Inty monorepo**

- Format: each task is markdown file, file name includes priority, name of the task, for instance, `p1_enhance_tests.md`.
- Each task file list TODOs
  - You should pick up TODO as the unit of work
- Update the task file so the agents can pick up what's left since previous iteration.
  - Use the git-file-last-commit skill to find the most recent commit ID of the file,
    and use the commit ID as diff base to get the diffs on main branch.
    Use the diffs to guide updating the file.
