"""Ops-only API: agent-channel debug endpoints.

TODO(rename-channel-to-gateway): Rename routes/types to Gateway — endpoints expose bonded human
channels (weixin/wechat, telegram, sms-phone-number, etc.) for a companion scope.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.schemas.response import APIResponse
from app.services.agentic_channel.endpoints import list_endpoints_for_agent

router = APIRouter(prefix="/agent-channel", tags=["agent-channel"])


class AgentChannelEndpointRow(BaseModel):
    user_id: str = Field(description="Inty user id")
    agent_id: str = Field(description="Companion agent id")
    channel: str = Field(description="Runtime channel")
    channel_address: str = Field(description="Outbound routing key")
    channel_user_id: str = Field(description="Channel-side human id")


class AgentChannelEndpointsData(BaseModel):
    count: int
    endpoints: list[AgentChannelEndpointRow]


@router.get(
    "/endpoints",
    response_model=APIResponse[AgentChannelEndpointsData],
    include_in_schema=False,
)
async def list_agent_channel_endpoints(
    agent_id: str = Query(min_length=1),
) -> APIResponse[AgentChannelEndpointsData]:
    rows = await list_endpoints_for_agent(agent_id=agent_id)
    return APIResponse.success(
        data=AgentChannelEndpointsData(
            count=len(rows),
            endpoints=[
                AgentChannelEndpointRow(
                    user_id=row.user_id,
                    agent_id=row.agent_id,
                    channel=row.channel.value,
                    channel_address=row.channel_address,
                    channel_user_id=row.channel_user_id,
                )
                for row in rows
            ],
        )
    )
