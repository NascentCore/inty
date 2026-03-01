#!/usr/bin/env bash
# Minimal script to call POST /api/v1/ai/agents/text-to-image. No error handling.
# Usage: TOKEN=<jwt> ./scripts/call_text_to_image.sh [prompt]
# Example: TOKEN=eyJ... ./scripts/call_text_to_image.sh "a sunny beach"
# Get a test JWT: python3 -c "from app.core.security import create_access_token; print(create_access_token('user-testing'))"

BASE="${BASE_URL:-http://localhost:8000}"
PROMPT="${1:-a person smiling}"
curl -s -X POST "${BASE}/api/v1/ai/agents/text-to-image" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"${PROMPT}\", \"model\": \"fal-ai/z-image/turbo\"}"
