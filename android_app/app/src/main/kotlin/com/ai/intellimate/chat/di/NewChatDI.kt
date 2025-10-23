package com.ai.intellimate.chat.di

import ai.sxwl.android.data.api.NetServiceMgr
import com.ai.intellimate.chat.data.ChatDataManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/**
 * newchat 模块内部的简易 DI 容器
 * 提供应用级单例的 ChatDataManager，确保 Chat 与 独立聊天页共享同一数据源
 */
object NewChatDI {

    // 应用级作用域，避免随页面销毁
    private val applicationScope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // 懒加载的单例 ChatDataManager
    val chatDataManager: ChatDataManager by lazy(LazyThreadSafetyMode.SYNCHRONIZED) {
        val chatApi = NetServiceMgr.getChatApi()
        val agentApi = NetServiceMgr.getAgentApi()
        ChatDataManager(chatApi, agentApi, applicationScope)
    }
}
