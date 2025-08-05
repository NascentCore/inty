"""
Error codes for API responses.
The App side can use these codes to determine exact behaviors.
For example, app can recommend subscription when a free user reaches the limit.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    FREE_USER_IMG_GEN_LIMIT_EXCEEDED = "FREE_USER_IMG_GEN_LIMIT_EXCEEDED"
    FREE_USER_CHAT_LIMIT_EXCEEDED = "FREE_USER_CHAT_LIMIT_EXCEEDED"
    FREE_USER_AGENT_CREATION_LIMIT_EXCEEDED = "FREE_USER_AGENT_CREATION_LIMIT_EXCEEDED"
    FREE_USER_VOICE_GEN_LIMIT_EXCEEDED = "FREE_USER_VOICE_GEN_LIMIT_EXCEEDED"
