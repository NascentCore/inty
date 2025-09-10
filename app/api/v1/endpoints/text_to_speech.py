"""
Voice related API endpoints
"""

router = APIRouter(prefix="/text-to-speech", route_class=LoggerRoute)

@router.post(
    "/messages/{message_id}",
    tags=["inty", "voice"],
    summary="Generate speech for a chat message",
    description="Generate voice for a message"
)
async def generate_message_voice(...):
    # TODO: 将生成语音的 API /chats/agents/{agent_id}/messages/{message_id}/voice 转移到此处
    pass
