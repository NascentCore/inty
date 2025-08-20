"""
Demo for using OpenAI SDK with LangSmith to track the usage of OpenAI API.
"""

import os
from openai import OpenAI
from langsmith import wrappers
from dotenv import load_dotenv

load_dotenv()


print("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
print("LANGCHAIN_API_KEY", os.getenv("LANGCHAIN_API_KEY"))
print("LANGSMITH_TRACING_V2", os.getenv("LANGSMITH_TRACING_V2"))


def main():
    # Create OpenAI client and wrap it with LangSmith
    client = wrappers.wrap_openai(
        OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    )

    # Chat API example
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]

    print("Making chat completion request...")
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo", messages=messages
    )

    print(f"Response: {completion.choices[0].message.content}")

    # Completions API example (if you want to use the older API)
    print("\nMaking completions request...")
    completion = client.chat.completions.create(
        model="openai/gpt-3.5-turbo-instruct",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of Japan?"},
        ],
        max_tokens=50,
    )

    print(f"Response: {completion.choices[0].message.content}")


if __name__ == "__main__":
    main()
