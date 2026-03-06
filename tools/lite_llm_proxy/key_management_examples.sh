#!/usr/bin/env bash

set -euo pipefail

LITELLM_BASE_URL="${LITELLM_BASE_URL:-http://localhost:4000}"
MASTER_KEY="${MASTER_KEY:-${LITELLM_MASTER_KEY:-}}"

if [[ -z "${MASTER_KEY}" ]]; then
  echo "Set MASTER_KEY (or LITELLM_MASTER_KEY) before running."
  return 1 2>/dev/null || exit 1
fi

generate_key_permanent() {
  curl -sS "${LITELLM_BASE_URL}/key/generate" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "key_alias": "customer-permanent",
      "models": ["or-gpt-4o"],
      "max_budget": 50,
      "budget_duration": "2592000s",
      "rpm_limit": 120,
      "tpm_limit": 240000
    }'
}

generate_key_one_week() {
  curl -sS "${LITELLM_BASE_URL}/key/generate" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "key_alias": "customer-1week",
      "models": ["or-gpt-4o"],
      "duration": "604800s",
      "max_budget": 20,
      "budget_duration": "604800s",
      "rpm_limit": 60,
      "tpm_limit": 120000
    }'
}

update_key_limits() {
  local key="${1:?usage: update_key_limits <key>}"
  curl -sS "${LITELLM_BASE_URL}/key/update" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"key\": \"${key}\",
      \"max_budget\": 100,
      \"budget_duration\": \"1209600s\",
      \"duration\": \"1209600s\",
      \"rpm_limit\": 180,
      \"tpm_limit\": 300000
    }"
}

get_key_info() {
  local key="${1:?usage: get_key_info <key>}"
  curl -sS "${LITELLM_BASE_URL}/key/info?key=${key}" \
    -H "Authorization: Bearer ${MASTER_KEY}"
}

list_keys() {
  curl -sS "${LITELLM_BASE_URL}/key/list" \
    -H "Authorization: Bearer ${MASTER_KEY}"
}

delete_key() {
  local key="${1:?usage: delete_key <key>}"
  curl -sS "${LITELLM_BASE_URL}/key/delete" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"keys\": [\"${key}\"]}"
}

test_chat_completion() {
  local user_key="${1:?usage: test_chat_completion <user_key>}"
  curl -sS "${LITELLM_BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${user_key}" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "or-gpt-4o",
      "messages": [{"role":"user","content":"Say hello in one short sentence."}]
    }'
}
