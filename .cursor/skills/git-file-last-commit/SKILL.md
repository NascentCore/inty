---
name: git-file-last-commit
description: >-
  Gets the latest commit hash that touched a path on main; diff that commit to
  origin/main to update specs incrementally.
---

# Git file last commit (spec diff base)

```bash
git fetch origin main   # optional

BASE=$(git log -1 origin/main --format=%H -- path/to/spec.md)
git diff "$BASE" origin/main -- path/to/code/
```

Rename history: same but `git log --follow -1` instead of `git log -1`.
