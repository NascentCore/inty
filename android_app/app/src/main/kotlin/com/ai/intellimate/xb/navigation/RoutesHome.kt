package com.ai.intellimate.xb.navigation

object RoutesHome {

    const val AgentInfoPage = "agent_info_page/{agentId}"
    const val AgentPhotoAlbum = "agent_photo_album/{agentId}"

    fun agentInfPage(agentId: String) = "agent_info_page/${agentId}"

    fun agentPhotoAlbum(agentId: String) = "agent_photo_album/${agentId}"
}
