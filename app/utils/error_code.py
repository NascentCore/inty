"""
Error codes used in API responses to app (or client side).
The app side can use these codes to determine exact behaviors.
For example, app can recommend subscription when a free user reaches the limit.

Certain information is hidden from the app side to avoid leaking sensitive information,
and to avoid confusing users.

The app should be checking the error code, to determine if they need to show 
detailed error message for display.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    FREE_USER_IMG_GEN_LIMIT_EXCEEDED = "FREE_USER_IMG_GEN_LIMIT_EXCEEDED"
    FREE_USER_CHAT_LIMIT_EXCEEDED = "FREE_USER_CHAT_LIMIT_EXCEEDED"
    FREE_USER_AGENT_CREATION_LIMIT_EXCEEDED = "FREE_USER_AGENT_CREATION_LIMIT_EXCEEDED"
    FREE_USER_VOICE_GEN_LIMIT_EXCEEDED = "FREE_USER_VOICE_GEN_LIMIT_EXCEEDED"
