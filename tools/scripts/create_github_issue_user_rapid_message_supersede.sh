#!/usr/bin/env bash
# Create GitHub issue for companion user rapid-message supersede + partial stream.
# Requires gh auth with issues:write (Cloud Agent integration token cannot create issues).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BODY_FILE="${ROOT}/.agents/work_logs/2026-05-17/github-issue-user-rapid-message-supersede-body.md"
exec gh issue create --repo nascentcore/inty \
  --title "[Agentic companion] 用户连发消息应抢占上一轮 user-turn，并以 partial stream 并入下一轮上下文" \
  --label "agentic_companion,chat,backend,enhancement" \
  --assignee yxzhao6 \
  --body-file "${BODY_FILE}"
