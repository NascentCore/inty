package com.ai.intellimate.xb.navigation

object RoutesChat {
    /** 聊天页面路由，参数：agentId（角色ID）、showBoost（是否显示Boost弹窗） */
    const val ChatPage =
        "chat_page/{agentId}/{showBoost}?shouldAutoFocusInput={shouldAutoFocusInput}"

    /**
     * 构建聊天页面路由路径
     *
     * @param agentId 角色ID
     * @param showBoost 是否显示Boost弹窗
     * @return 聊天页面路由路径
     */
    fun chatPage(agentId: String, showBoost: Boolean, shouldAutoFocusInput: Boolean = true) =
        "chat_page/${agentId}/${showBoost}?shouldAutoFocusInput=${shouldAutoFocusInput}"
}
