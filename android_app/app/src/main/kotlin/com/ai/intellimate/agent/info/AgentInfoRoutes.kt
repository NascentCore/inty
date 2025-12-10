package com.ai.intellimate.agent.info

object AgentInfoRoutes {
    const val AGENT_INFO = "agent_info"
    const val PHOTO_ALBUM = "photo_album"

    fun photoAlbum(agentId: String) = "$PHOTO_ALBUM/$agentId"
}
