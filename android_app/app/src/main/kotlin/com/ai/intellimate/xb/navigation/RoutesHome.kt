package com.ai.intellimate.xb.navigation

object RoutesHome {

    const val AgentInfoPage = "agent_info_page/{agentId}"
    const val AgentPhotoAlbum = "agent_photo_album/{agentId}"
    const val RegInfoPage = "reg_info_page"

    fun agentInfPage(agentId: String) = "agent_info_page/${agentId}"

    fun agentPhotoAlbum(agentId: String) = "agent_photo_album/${agentId}"
}
