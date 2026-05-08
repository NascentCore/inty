---
name: git-file-last-commit
description: >-
  Resolves the commit hash of the most recent change to a given file path
  (optionally scoped to main). Use when updating spec files incrementally: take
  that commit as the diff base against main to list code or doc changes since
  the spec was last touched.
---

# Git: last commit for a file (spec diff base)

## Goal

- **Input**: one tracked path (for example a spec under `/docs/`).
- **Output**: a full (`%H`) or short (`%h`) commit id for the **latest commit that modified that path**.
- **Follow-up**: use that id as the left side of a diff against current `main` to drive incremental spec updates.

Run commands from the **repository root** unless you intentionally point `--git-dir` elsewhere.

## Core commands

### Latest commit touching the path (reachable from current `HEAD`)

```bash
git log -1 --format=%H -- path/to/file
```

Short hash:

```bash
git log -1 --format=%h -- path/to/file
```

### Scope to main (recommended for spec vs `main` workflows)

Use the integration branch name your team uses (`main` below); substitute `origin/main` after `git fetch` if you compare against remote.

```bash
git log -1 main --format=%H -- path/to/file
```

Remote tip (after `git fetch origin main`):

```bash
git log -1 origin/main --format=%H -- path/to/file
```

### Renames and moves (`--follow`)

If the spec or target file was renamed, ask Git to follow the path:

```bash
git log --follow -1 --format=%H -- path/to/current/file
```

`--follow` only works for a **single** path.

### First-parent history on main (optional)

When `main` carries merge commits and you want the linear "what landed on main" story:

```bash
git log -1 --first-parent main --format=%H -- path/to/file
```

## Incremental spec update: diff since that commit

1. Update refs if you compare to `origin/main`:

   ```bash
   git fetch origin main
   ```

2. Resolve the base commit for the spec file (example path):

   ```bash
   SPEC="/docs/example_spec.md"
   BASE=$(git log -1 origin/main --format=%H -- "$SPEC")
   ```

3. Show changes on `main` **after** that commit for arbitrary paths (code areas the spec describes). Compare the tree at `BASE` to the tree at the main tip (two explicit commits):

   ```bash
   git diff "${BASE}" origin/main -- path/inside/repo/
   ```

   Narrow to relevant subtrees or files; avoid dumping the whole repo unless intended.

4. If you only need whether anything changed:

   ```bash
   git diff --quiet "${BASE}" origin/main -- path/inside/repo/ && echo "no diff"
   ```

## Semantics check

- `git log -1 ... -- path` returns nothing if **no commit** in the queried history touches that path (wrong path, typo, or file only exists on another branch). Confirm with `git log -1 ... -- path` stderr / exit code or `git ls-tree` on the branch.
- The base commit is **the last edit to that path** on the queried branch range, not necessarily "the commit where the spec was written from scratch"; treat it as the last sync point for that file on that branch.
- `git diff "${BASE}" origin/main -- paths` compares the tree at `BASE` to the tree at `origin/main` for the listed paths (equivalent to two-dot range `BASE..origin/main` for this pair).

## Related repo docs

- Backend / workflow context: [`/AGENTS.md`](/AGENTS.md)
