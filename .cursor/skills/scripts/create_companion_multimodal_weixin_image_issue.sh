#!/usr/bin/env bash
# Create GitHub tracking issue and replace ISSUE_TBD in companion-multimodal / weixin-inbound TODOs.
set -euo pipefail

REPO="NascentCore/inty"
BODY_FILE=".agents/work_logs/2026-06-09/companion-multimodal-weixin-image-github-issue-body.md"
TITLE="Companion multimodal user-turn + Weixin inbound image support"

cd "$(git rev-parse --show-toplevel)"

issue_url="$(gh issue create --repo "$REPO" --title "$TITLE" --body-file "$BODY_FILE")"
issue_num="${issue_url##*/}"
echo "Created: $issue_url (#$issue_num)"

rg -l 'ISSUE_TBD' --glob '*.py' app backend | while read -r f; do
  sed -i "s|https://github.com/NascentCore/inty/issues/ISSUE_TBD|https://github.com/NascentCore/inty/issues/${issue_num}|g" "$f"
done

echo "Updated TODO references to #${issue_num}"
