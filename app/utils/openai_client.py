"""
Wrapper of OpenAI API, used to wrap the OpenAI API with LangSmith.
"""

"""
Demo for using OpenAI SDK with LangSmith to track the usage of OpenAI API.
"""

import os
from openai import OpenAI
from langsmith import wrappers
from langsmith.wrappers._openai import TracingExtra

from app.core.config import global_config_loaded_from_config_yaml


_vanilla_openai_client = OpenAI(
    base_url=global_config_loaded_from_config_yaml.agent.base_url,
    api_key=global_config_loaded_from_config_yaml.agent.api_key,
)


def get_openai_client(labels: dict[str, str]):
    """
    Return an OpenAI client with LangSmith tracing.
    The ENV vars are required by langsmith.
    """
    # These env vars has no arguments inputable to langchina api
    assert os.getenv("LANGCHAIN_API_KEY"), "LANGCHAIN_API_KEY must be set"
    assert os.getenv("LANGSMITH_TRACING_V2"), "LANGSMITH_TRACING_V2 must be set"
    assert os.getenv("LANGSMITH_PROJECT"), "LANGSMITH_PROJECT must be set"
    # Create OpenAI client and wrap it with LangSmith
    tracing_extra: TracingExtra = {
        "metadata": labels,
        "tags": ["openai", "langsmith"],
    }
    _client = wrappers.wrap_openai(_vanilla_openai_client, tracing_extra=tracing_extra)

    return _client


if __name__ == "__main__":
    """
    Test the openai client.
    """
    from dotenv import load_dotenv

    load_dotenv()
    client = get_openai_client()
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )
    print(response)
