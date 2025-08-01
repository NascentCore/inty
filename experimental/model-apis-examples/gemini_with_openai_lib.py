import argparse
from enum import Enum
from enum import StrEnum
import json
import os
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion


def parse_args():
    parser = argparse.ArgumentParser(description='Chat with AI models')
    parser.add_argument('--provider', 
                       choices=['google', 'openrouter'], 
                       default='openrouter',
                       help='AI provider to use')
    parser.add_argument('--model',
                       default='google/gemini-2.5-flash',
                       help='AI model to use')
    return parser.parse_args()


class ProviderEnum(StrEnum):
    google = 'google'
    openrouter = 'openrouter'


args = parse_args()
print(args.provider == ProviderEnum.google.value)
print(ProviderEnum.google.value)
if args.provider == ProviderEnum.google.value:
    api_key = os.getenv("GEMINI_API_KEY")
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
else:
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1"


print(f"Using provider: {args.provider}")
print(f"Using api key: {api_key}")
print(f"Using base url: {base_url}")
print(f"Using model: {args.model}")

client = OpenAI(
    # You can set api_key directly here, where you can read from different env vars.
    # api_key=os.getenv("GEMINI_API_KEY"),
    # If you want to OpenAI to read env var directly, you need to set OPENAI_API_KEY in your env
    # As OPENAI_API_KEY is the env var read by OpenAI SDK.

    # Gemini base URL
    # base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key=api_key,
    base_url=base_url
)

response: ChatCompletion = client.chat.completions.create(
    model=args.model,
    # This is the only way to control reasoning for gemini-2.5-flash.
    # Remove this parameter to disable reasoning when calling gemini-2.5-flash.
    reasoning_effort="low",
    max_completion_tokens=4096,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a plot summary of a novel on AI causing human extinction"
        }
    ],
    # extra_body={
    #   'extra_body': {
    #     "google": {
    #       "thinking_config": {
    #         # This does not seem to work, setting >0 value does not make it do reasoning or thinking.
    #         "thinking_budget": 1024,
    #         # This also does not seem to work, turn it to False will not make it not include reasoning details
    #         # (if reasoning_effort is set to one of "low", "medium", "high").
    #         "include_thoughts": True
    #       }
    #     }
    #   }
    # }
)

# Pretty print response
response_dict = response.model_dump()
print(json.dumps(response_dict, indent=4))
