package com.ai.inty.newchat.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.beans.MsgInfo
import com.ai.inty.newchat.data.ChatDataManager
import com.ai.inty.newchat.data.MessageEvent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 全局聊天ViewModel
 * 负责管理全局聊天状态，实现多UI数据同步
 */
class GlobalChatViewModel(
    private val chatDataManager: ChatDataManager
) : ViewModel() {

    // 当前活跃的Agent
    private val _activeAgentId = MutableStateFlow<String?>(null)
    val activeAgentId: StateFlow<String?> = _activeAgentId.asStateFlow()

    // 当前Agent的chatMessages消息流
    private var _currentMessagesFlow: StateFlow<List<MsgInfo>>? = null
    val currentMessagesFlow: StateFlow<List<MsgInfo>>
        get() = _currentMessagesFlow ?: MutableStateFlow<List<MsgInfo>>(emptyList()).asStateFlow()

    // 输入文本
    private val _inputText = MutableStateFlow("")
    val inputText: StateFlow<String> = _inputText.asStateFlow()

    // 发送状态
    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    // 加载状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    // 错误消息
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
     * 设置当前活跃的Agent
     */
    fun setActiveAgent(agentId: String) {
        _activeAgentId.value = agentId
        _currentMessagesFlow = chatDataManager.getMessagesFlow(agentId)

        // 设置全局活跃Agent
        chatDataManager.setActiveAgent(agentId)

        // 加载当前agent最新的一页chatMessages
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
        val agentId = _activeAgentId.value ?: return
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
     * 重试发送失败的消息
     */
    fun retryMessage(messageId: String) {
        val agentId = _activeAgentId.value ?: return

        viewModelScope.launch {
            // 重新发送消息逻辑
            // 这里可以根据具体需求实现
        }
    }

    /**
     * 加载更多历史消息（分页）
     */
    fun loadMoreHistory() {
        val agentId = _activeAgentId.value ?: return
        val currentMessages = _currentMessagesFlow?.value ?: emptyList()

        viewModelScope.launch {
            _isLoading.value = true
            chatDataManager.loadHistoryMessages(agentId, limit = 20, offset = currentMessages.size)
            _isLoading.value = false
        }
    }

    /**
     * 监听消息事件
     */
    fun observeMessageEvents() {
        viewModelScope.launch {
            chatDataManager.messageEvents.collect { event ->
                when (event) {
                    is MessageEvent.MessageAdded -> {
                        // 消息已通过StateFlow自动更新
                    }

                    is MessageEvent.MessageUpdated -> {
                        // 消息已通过StateFlow自动更新
                    }

                    is MessageEvent.MessagesUpdated -> {
                        // 消息已通过StateFlow自动更新
                    }

                    is MessageEvent.MessageDeleted -> {
                        // 处理消息删除
                    }
                }
            }
        }
    }
}
