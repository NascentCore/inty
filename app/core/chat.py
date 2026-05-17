import json
import time
import uuid

from sqlalchemy.ext.asyncio.session import AsyncSession

from loguru import logger


async def generate_chat_stream(
    agent,
    messages: dict,
    user_id: str,
    session_id: str,
    chat_id: str,
    model_name: str,
    db_session: AsyncSession = None,
    agent_id: str = None,
    last_user_message: str = None,
):
    """
    Generate streaming chat response (async version)
    """
    try:
        # Use Agent's async chat_stream method
        async for message_chunk, metadata in agent.chat_stream(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            db_session=db_session,
        ):
            # Check message chunk type, only send AI messages
            if hasattr(message_chunk, "content") and message_chunk.content:
                chunk_data = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "created": int(
                        time.time()
                    ),  # pyright: ignore[reportUndefinedVariable]
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": message_chunk.content,
                            },
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

        # Send end marker
        end_chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Streaming chat failed: {str(e)}")
        error_chunk = {
            "error": {
                "message": f"Chat failed: {str(e)}",
                "type": "server_error",
            }
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
