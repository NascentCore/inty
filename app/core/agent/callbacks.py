"""
LangChain callback handlers for logging OpenAI API requests and responses
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class OpenAILoggingCallback(BaseCallbackHandler):
    """
    Custom callback handler for logging OpenAI API requests and responses
    """

    def __init__(
        self, agent_id: str = None, user_id: str = None, session_id: str = None
    ):
        self.agent_id = agent_id
        self.user_id = user_id
        self.session_id = session_id
        self.request_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None
        self.request_data = {}
        self.response_data = {}
        self.token_usage = {}

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Log when LLM starts"""
        self.start_time = time.time()

        # Extract request information
        self.request_data = {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "model": serialized.get("name", "unknown"),
            "prompts": prompts,
            "start_time": self.start_time,
            "kwargs": kwargs,
        }

        logger.info(f"=== OPENAI API REQUEST START ===")
        logger.info(f"Request ID: {self.request_id}")
        logger.info(f"Agent ID: {self.agent_id}")
        logger.info(f"User ID: {self.user_id}")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Model: {serialized.get('name', 'unknown')}")
        logger.info(
            f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}"
        )
        logger.info(f"Prompts Count: {len(prompts)}")

        # Log each prompt
        for i, prompt in enumerate(prompts):
            logger.info(f"Prompt {i+1} Length: {len(prompt)} characters")
            logger.info(f"Prompt {i+1} Preview: {prompt}")

        # Log additional parameters
        if kwargs:
            logger.info(
                f"Additional Parameters: {json.dumps(kwargs, default=str, indent=2)}"
            )

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Log new tokens as they arrive (for streaming)"""
        # For streaming responses, we might want to log tokens
        # But be careful not to spam the logs
        pass

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Log when LLM ends"""
        self.end_time = time.time()
        processing_time = self.end_time - self.start_time

        # Extract response information
        generations = response.generations
        llm_output = response.llm_output or {}

        # Extract token usage
        token_usage = llm_output.get("token_usage", {})
        self.token_usage = token_usage

        # Extract response content
        response_content = []
        for gen_list in generations:
            for gen in gen_list:
                response_content.append(gen.text)

        self.response_data = {
            "request_id": self.request_id,
            "response_content": response_content,
            "token_usage": token_usage,
            "end_time": self.end_time,
            "processing_time": processing_time,
            "llm_output": llm_output,
        }

        logger.info(f"=== OPENAI API RESPONSE END ===")
        logger.info(f"Request ID: {self.request_id}")
        logger.info(f"Processing Time: {processing_time:.3f} seconds")
        logger.info(f"Response Count: {len(response_content)}")

        # Log token usage
        if token_usage:
            logger.info(f"Token Usage: {json.dumps(token_usage, indent=2)}")

        # Log response content
        for i, content in enumerate(response_content):
            logger.info(f"Response {i+1} Length: {len(content)} characters")
            logger.info(
                f"Response {i+1} Preview: {content[:200]}{'...' if len(content) > 200 else ''}"
            )

        # Log complete request/response summary
        logger.info(f"=== OPENAI API SUMMARY ===")
        logger.info(f"Request ID: {self.request_id}")
        logger.info(f"Agent ID: {self.agent_id}")
        logger.info(f"User ID: {self.user_id}")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Total Processing Time: {processing_time:.3f} seconds")
        logger.info(f"Total Tokens Used: {token_usage.get('total_tokens', 'unknown')}")
        logger.info(f"Prompt Tokens: {token_usage.get('prompt_tokens', 'unknown')}")
        logger.info(
            f"Completion Tokens: {token_usage.get('completion_tokens', 'unknown')}"
        )

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Log when LLM errors"""
        self.end_time = time.time()
        processing_time = self.end_time - self.start_time if self.start_time else 0

        logger.error(f"=== OPENAI API ERROR ===")
        logger.error(f"Request ID: {self.request_id}")
        logger.error(f"Agent ID: {self.agent_id}")
        logger.error(f"User ID: {self.user_id}")
        logger.error(f"Session ID: {self.session_id}")
        logger.error(f"Error Type: {type(error).__name__}")
        logger.error(f"Error Message: {str(error)}")
        logger.error(f"Processing Time: {processing_time:.3f} seconds")
        logger.error(f"Additional kwargs: {kwargs}")

    def get_request_summary(self) -> Dict[str, Any]:
        """Get a summary of the request and response"""
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request": self.request_data,
            "response": self.response_data,
            "success": self.end_time is not None and not hasattr(self, "_error"),
        }


class StreamingOpenAILoggingCallback(OpenAILoggingCallback):
    """
    Enhanced callback handler for streaming responses
    """

    def __init__(
        self, agent_id: str = None, user_id: str = None, session_id: str = None
    ):
        super().__init__(agent_id, user_id, session_id)
        self.token_count = 0
        self.first_token_time = None

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Log new tokens as they arrive"""
        if self.first_token_time is None:
            self.first_token_time = time.time()
            time_to_first_token = self.first_token_time - self.start_time
            logger.info(f"=== STREAMING FIRST TOKEN ===")
            logger.info(f"Request ID: {self.request_id}")
            logger.info(f"Time to First Token: {time_to_first_token:.3f} seconds")

        self.token_count += 1

        # Log every 10th token to avoid spam
        if self.token_count % 10 == 0:
            logger.debug(f"Streaming Token #{self.token_count}: {token}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Log when streaming LLM ends"""
        super().on_llm_end(response, **kwargs)

        # Additional streaming-specific logging
        if self.first_token_time:
            total_streaming_time = self.end_time - self.first_token_time
            logger.info(f"Total Streaming Time: {total_streaming_time:.3f} seconds")
            logger.info(f"Total Tokens Streamed: {self.token_count}")


def create_openai_callback_handler(
    agent_id: str = None,
    user_id: str = None,
    session_id: str = None,
    streaming: bool = False,
) -> OpenAILoggingCallback:
    """
    Factory function to create appropriate callback handler

    Args:
        agent_id: The agent ID for logging context
        user_id: The user ID for logging context
        session_id: The session ID for logging context
        streaming: Whether this is for streaming responses

    Returns:
        Appropriate callback handler instance
    """
    if streaming:
        return StreamingOpenAILoggingCallback(agent_id, user_id, session_id)
    else:
        return OpenAILoggingCallback(agent_id, user_id, session_id)
