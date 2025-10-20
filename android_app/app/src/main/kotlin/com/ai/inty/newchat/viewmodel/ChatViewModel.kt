package com.ai.inty.newchat.viewmodel

import androidx.lifecycle.ViewModel
import com.ai.inty.beans.MsgInfo
import com.ai.inty.newchat.data.ChatDataManager
import kotlinx.coroutines.flow.StateFlow

/**
 * 聊天页面ViewModel
 * 使用全局状态管理，确保数据一致性
 */
class ChatViewModel(
    private val globalChatViewModel: GlobalChatViewModel,
    private val chatDataManager: ChatDataManager
) : ViewModel() {

    // 当前Agent ID
    private var _agentId: String? = null

    // 消息流 - 从全局管理器获取
    private var _messagesFlow: StateFlow<List<MsgInfo>>? = null
    val messagesFlow: StateFlow<List<MsgInfo>>
        get() = _messagesFlow ?: chatDataManager.getMessagesFlow(_agentId ?: "")

    // 输入文本 - 从全局状态获取
    val inputText: StateFlow<String> = globalChatViewModel.inputText

    // 发送状态 - 从全局状态获取
    val isSending: StateFlow<Boolean> = globalChatViewModel.isSending

    // 加载状态 - 从全局状态获取
    val isLoading: StateFlow<Boolean> = globalChatViewModel.isLoading

    val errorMessage: StateFlow<String?> = globalChatViewModel.errorMessage

    /**
     * 设置Agent
     */
    fun setAgent(agentId: String) {
        _agentId = agentId
        _messagesFlow = chatDataManager.getMessagesFlow(agentId)

        // 设置全局活跃Agent
        globalChatViewModel.setActiveAgent(agentId)
    }

    /**
     * 发送消息 - 委托给全局管理器
     */
    fun sendMessage() {
        globalChatViewModel.sendMessage()
    }

    /**
     * 更新输入文本 - 委托给全局管理器
     */
    fun updateInputText(text: String) {
        globalChatViewModel.updateInputText(text)
    }

    /**
     * 重试消息
     */
    fun retryMessage(messageId: String) {
        globalChatViewModel.retryMessage(messageId)
    }
}
