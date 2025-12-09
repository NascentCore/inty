package com.ai.intellimate.xb.navigation

object Routes {
    const val SplashLogin = "splash_login"
    const val HomeTab = "home_screen"

    const val ChatPage = "chat_page/{agentId}/{show}"
    const val Settings = "settings"
    const val VipCenter = "vip_center"
    const val CheckIn = "check_in"
    const val EditProfile = "ef"

    fun chatPage(agentId: String, showBoost: Boolean) = "chat_page/${agentId}/${showBoost}"
}
