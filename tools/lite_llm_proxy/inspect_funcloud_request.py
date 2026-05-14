#!/usr/bin/env python3
"""
Inspect URL and headers that LiteLLM sends to Funcloud for anthropic/ model.

Run from repo root with FUNCLOUD_API_KEY set. No network call is made; we only
reproduce the same URL and headers that litellm/llms/anthropic uses.

Findings (from litellm code):
- URL: api_base is used as-is. Config uses api_base: https://api.funcloud.ai/v1/official/v1/messages
- Auth: AnthropicModelInfo.get_anthropic_headers() sets headers["x-api-key"] = api_key
  (unless api_key is OAuth sk-ant-oat*, then it sets Authorization: Bearer).
  Funcloud requires Authorization: Bearer and rejects x-api-key (70602).
- Working curl: POST https://api.funcloud.ai/v1/official/v1/messages
  with Content-Type, anthropic-version: 2023-06-01, Authorization: Bearer $FUNCLOUD_API_KEY
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    api_key = os.environ.get("FUNCLOUD_API_KEY")
    if not api_key:
        print(
            "Set FUNCLOUD_API_KEY to inspect (key will be redacted in output).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Same values as tools/lite_llm_proxy/config.yaml
    api_base = "https://api.funcloud.ai/v1/official/v1/messages"
    model = "us.anthropic.claude-opus-4-20250514-v1:0"

    # LiteLLM Anthropic path: get_anthropic_headers() in common_utils.py
    # builds headers; for non-OAuth key it sets x-api-key, not Authorization.
    is_oauth = api_key.startswith("sk-ant-oat")
    if is_oauth:
        auth_header = f"Authorization: Bearer {api_key[:20]}..."
    else:
        auth_header = None
    x_api_key = (
        None if is_oauth else (api_key[:20] + "..." if len(api_key) > 20 else api_key)
    )

    print("URL (api_base) sent to Funcloud:")
    print(f"  {api_base}")
    print()
    print("Headers LiteLLM sends by default (anthropic handler):")
    print("  Content-Type: application/json")
    print("  Accept: application/json")
    print("  anthropic-version: 2023-06-01")
    if auth_header:
        print(f"  {auth_header}")
    else:
        print(f"  x-api-key: {x_api_key}")
    print()
    print("Working curl uses Authorization: Bearer (not x-api-key).")
    print(
        "So config must set extra_headers: { Authorization: os.environ/FUNCLOUD_AUTH_HEADER }"
    )
    print("with start.sh exporting FUNCLOUD_AUTH_HEADER='Bearer $FUNCLOUD_API_KEY'.")


if __name__ == "__main__":
    main()
