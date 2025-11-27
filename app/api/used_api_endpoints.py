# CREATED_BY_AGENT
"""当前真实流量使用的 API endpoint 列表快照。

该列表来自 2025-11-27 的后端调用统计，用于自动为未使用的接口
标记 `NOT_USED` tag，方便后续重构或下线。
"""

from typing import Final, FrozenSet, Mapping

USED_API_ENDPOINT_CALL_COUNTS: Final[Mapping[str, int]] = {
    "/api/v1/auth/guest": 5,
    "/api/v1/evaluation/user-analytics/user-today-stats": 4,
    "/evaluation/{path:path}": 3,
    "/api/v1/evaluation/user-analytics/user-daily-messages": 2,
    "/api/v1/evaluation/user-analytics/user-sessions": 1,
    "/api/v1/text-to-speech/list-voices": 1,
    "/api/v1/evaluation/user-analytics/session-messages": 1,
    "/api/v1/ai/agents/models/openrouter": 1,
    "/api/v1/chats/agents/{agent_id}/messages": 1800,
    "/api/v1/ai/agents/recommend": 1000,
    "/api/v1/chat/completions/{agent_id}": 643,
    "/api/v1/subscription/plans": 613,
    "/api/v1/chats/agents/{agent_id}/settings": 469,
    "/api/v1/users/me": 322,
    "/api/v1/ai/agents/me": 224,
    "/api/v1/version/check": 106,
    "/api/v1/chats/agents/{agent_id}/messages/{message_id}/voice": 85,
    "/api/v1/auth/google/login": 66,
    "/": 62,
    "/api/v1/chat/images/{agent_id}": 55,
    "/api/v1/chats/": 51,
    "/api/v1/ai/agents/{agent_id}": 43,
    "/api/v1/users/device/register": 28,
    "/api/v1/users/profile": 19,
    "/api/v1/subscription/webhook": 13,
    "/api/v1/ai/agents": 9,
    "/api/v1/ai/agents/text-to-image": 7,
}

USED_API_ENDPOINT_PATHS: Final[FrozenSet[str]] = frozenset(
    USED_API_ENDPOINT_CALL_COUNTS.keys()
)
