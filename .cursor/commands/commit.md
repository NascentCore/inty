# Git Commit Current Changes

## Overview

Git commit changes in the current conversation.

Use [Scoped Commits](https://scopedcommits.com/) to draft commit message.

```
<scope>: <description>

[optional body]

[optional trailer(s)]
```

Example:

```
auth: fix login bug

This commit fixes the login bug by...

issues/3211
```

## Steps

1. **Write 1 sentence commit title**
2. **Write bullet points of changes**
3. **Git commit changes made in current conversation**
   3.1. In `cmd-k` mode, commit all changes
4. **Summary**: output commit title to user
5. git push to remote

## Checklist

- [ ] 1 sentence commit title
- [ ] bullet points description
- [ ] git commit changes in current conversation
- [ ] the commit is pushed to remote
