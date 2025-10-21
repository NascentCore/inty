package com.ai.inty.newchat.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.beans.MsgInfo
import com.ai.inty.newchat.data.ChatDataManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 聊天页面ViewModel
 * 独立管理每个Agent的聊天状态，不依赖全局状态
 */
class ChatViewModel(
    private val chatDataManager: ChatDataManager
) : ViewModel() {

    // 当前Agent ID
    private var _agentId: String? = null

    // 消息流 - 从数据管理器获取
    private var _messagesFlow: StateFlow<List<MsgInfo>>? = null
    val messagesFlow: StateFlow<List<MsgInfo>>
        get() = _messagesFlow ?: MutableStateFlow<List<MsgInfo>>(emptyList()).asStateFlow()

    // 输入文本 - 独立管理
    private val _inputText = MutableStateFlow("")
    val inputText: StateFlow<String> = _inputText.asStateFlow()

    // 发送状态 - 独立管理
    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    // 加载状态 - 独立管理
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    // 错误消息 - 独立管理
    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    init {
        // 监听错误事件
        viewModelScope.launch {
            chatDataManager.errorEvents.collect { errorMessage ->
                _errorMessage.value = errorMessage
            }
        }
    }

    /**
     * 设置Agent
     */
    fun setAgent(agentId: String) {
        _agentId = agentId
        _messagesFlow = chatDataManager.getMessagesFlow(agentId)

        // 设置数据管理器的活跃Agent
        chatDataManager.setActiveAgent(agentId)

        // 加载历史消息
        viewModelScope.launch {
            _isLoading.value = true
            chatDataManager.loadHistoryMessages(agentId, limit = 20, offset = 0)
            _isLoading.value = false
        }
    }

    /**
     * 发送消息
     */
    fun sendMessage() {
        val agentId = _agentId ?: return
        val content = _inputText.value.trim()
        if (content.isEmpty()) return

        viewModelScope.launch {
            _isSending.value = true
            val originalText = _inputText.value
            _inputText.value = ""

            val result = chatDataManager.sendMessage(agentId, content)
            if (result.isFailure) {
                // 发送失败，恢复输入内容
                _inputText.value = originalText
            }

            _isSending.value = false
        }
    }

    /**
     * 更新输入文本
     */
    fun updateInputText(text: String) {
        _inputText.value = text
    }

    /**
     * 重试消息
     */
    fun retryMessage(messageId: String) {
        val agentId = _agentId ?: return

        viewModelScope.launch {
            // 重新发送消息逻辑
            // 这里可以根据具体需求实现
        }
    }
}
