package com.ai.intellimate.xb.navigation

object RoutesChat {
    /** 聊天页面路由，参数：agentId（角色ID）、showBoost（是否显示Boost弹窗）、isDeleted（是否已删除，可选） */
    const val ChatPage =
        "chat_page/{agentId}/{showBoost}?shouldAutoFocusInput={shouldAutoFocusInput}&isDeleted={isDeleted}&fromPage={fromPage}"

    /** 语音通话页面路由，参数：agentId（角色ID） */
    const val VoiceCall = "voice_call/{agentId}"

    /**
     * 构建聊天页面路由路径
     *
     * @param agentId 角色ID
     * @param showBoost 是否显示Boost弹窗
     * @param shouldAutoFocusInput 是否自动聚焦输入框
     * @param isDeleted 是否已删除（默认false，仅在从会话列表进入时传入）
     * @return 聊天页面路由路径
     */
    fun chatPage(
        agentId: String,
        showBoost: Boolean,
        shouldAutoFocusInput: Boolean = true,
        isDeleted: Boolean = false,
        fromPage: String? = null
    ) =
        "chat_page/${agentId}/${showBoost}?shouldAutoFocusInput=${shouldAutoFocusInput}&isDeleted=${isDeleted}&fromPage=${fromPage}"

    /**
     * 构建语音通话页面路由路径
     *
     * @param agentId 角色ID
     * @return 语音通话页面路由路径
     */
    fun voiceCall(agentId: String) = "voice_call/${agentId}"
}
