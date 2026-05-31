#!/usr/bin/env bash
# Export GitHub issues as JSON for portfolio audit (github-issue-consolidate skill).
set -euo pipefail

STATE="open"
LIMIT="500"
REPO=""

usage() {
  echo "Usage: $0 [--state open|closed|all] [--limit N] [--repo owner/name]" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --state)
      STATE="${2:?}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:?}"
      shift 2
      ;;
    --repo)
      REPO="${2:?}"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      ;;
  esac
done

REPO_FLAG=()
if [[ -n "$REPO" ]]; then
  REPO_FLAG=(--repo "$REPO")
fi

gh issue list \
  "${REPO_FLAG[@]}" \
  --state "$STATE" \
  --limit "$LIMIT" \
  --json number,title,body,labels,state,createdAt,updatedAt,comments,assignees,milestone,closedAt \
  | jq '[.[] | {
      number,
      title,
      state,
      labels: [.labels[].name],
      createdAt,
      updatedAt,
      closedAt,
      assignees: [.assignees[].login],
      milestone: (.milestone.title // null),
      commentCount: (.comments | length),
      lastCommentAt: (if (.comments | length) > 0 then (.comments | max_by(.createdAt) | .createdAt) else null end),
      bodyPreview: (.body | if . == null then "" else .[0:240] end)
    }]'
