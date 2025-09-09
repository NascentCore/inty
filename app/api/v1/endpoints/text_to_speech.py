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
    pass
