#!/usr/bin/env python3
"""
Test script to demonstrate LangChain callback functionality for OpenAI API logging
"""

import asyncio
import logging
from app.core.agent.callbacks import create_openai_callback_handler
from app.core.agent.agent import Agent
from app.core.config import settings

# Set up logging to see the callback output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_callbacks():
    """Test the callback functionality"""
    print("=== Testing LangChain Callback Functionality ===")

    # Create a test agent configuration
    agent_config = {
        "model": "gpt-3.5-turbo",
        "api_key": settings.agent.api_key,
        "base_url": settings.agent.base_url,
        "temperature": 0.7,
        "max_tokens": 100,
    }

    # Create a test agent
    test_agent = Agent(
        agent_id="test-agent-001",
        name="Test Agent",
        model_config=agent_config,
        description="A test agent for callback functionality",
        main_prompt="You are a helpful assistant. Keep responses brief.",
    )

    print(f"Created test agent: {test_agent.name}")

    # Test messages
    test_messages = {
        "messages": [
            {"role": "user", "content": "Hello! Can you tell me a short joke?"}
        ]
    }

    print("\n=== Testing Regular Chat with Callbacks ===")
    try:
        # Test regular chat
        response = await test_agent.chat(
            user_id="test-user-001",
            session_id="test-session-001",
            messages=test_messages,
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error in regular chat: {e}")

    print("\n=== Testing Streaming Chat with Callbacks ===")
    try:
        # Test streaming chat
        async for chunk, metadata in test_agent.chat_stream(
            user_id="test-user-001",
            session_id="test-session-002",
            messages=test_messages,
        ):
            if hasattr(chunk, "content"):
                print(f"Stream chunk: {chunk.content}", end="", flush=True)
    except Exception as e:
        print(f"Error in streaming chat: {e}")

    print("\n=== Callback Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_callbacks())
