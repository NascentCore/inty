package com.ai.intellimate.xb.navigation

object Routes {
    const val SplashLogin = "splash_login"
    const val HomeTab = "home_screen"

    const val ChatPage = "chat_page/{agentId}"
    const val Settings = "settings"
    const val VipCenter = "vip_center"
    const val ModifyProfile = "modify_profile"


    fun chatPage(agentId: String) = "chat_page/${agentId}"
}