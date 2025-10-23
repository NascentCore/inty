package com.ai.inty.newchat.viewmodel

import ai.sxwl.android.data.api.model.MsgInfo
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.newchat.data.ChatDataManager
import com.ai.inty.newchat.data.ErrorEvent
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
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

    // 固定实例的消息流，避免 Compose 绑定到临时空 Flow
    private val _messages = MutableStateFlow<List<MsgInfo>>(emptyList())
    val messagesFlow: StateFlow<List<MsgInfo>> = _messages.asStateFlow()

    private var messagesCollectJob: Job? = null

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

    // 最近一次发送的本地消息ID
    private val _lastSentLocalMessageId = MutableStateFlow<String?>(null)
    val lastSentLocalMessageId: StateFlow<String?> = _lastSentLocalMessageId.asStateFlow()

    // UI 层错误事件（仅匹配最近一次发送）
    private val _uiErrorEvents = MutableSharedFlow<String>(replay = 0, extraBufferCapacity = 16)
    val uiErrorEvents: SharedFlow<String> = _uiErrorEvents.asSharedFlow()

    /**
     * 设置Agent
     */
    fun setAgent(agentId: String) {
        // 如果已经是同一个Agent，不需要重新加载
        if (_agentId == agentId) return

        _agentId = agentId
        val source = chatDataManager.getMessagesFlow(agentId)

        // 设置数据管理器的活跃Agent
        chatDataManager.setActiveAgent(agentId)

        // 检查是否已经有消息数据，如果没有才加载历史消息
        val currentMessages = source.value
        if (currentMessages.isEmpty()) {
            viewModelScope.launch {
                _isLoading.value = true
                chatDataManager.loadHistoryMessages(agentId, limit = 20, offset = 0)
                _isLoading.value = false
            }
        }

        // 切换源并收集到固定 StateFlow 中
        messagesCollectJob?.cancel()
        messagesCollectJob = viewModelScope.launch {
            source.collect { list ->
                _messages.value = list
            }
        }

        // 启动错误事件收集（仅处理当前agent且匹配最近一次发送的消息ID）
        viewModelScope.launch {
            chatDataManager.errorEvents.collect { event: ErrorEvent ->
                val currentAgent = _agentId
                val lastLocalId = _lastSentLocalMessageId.value
                if (currentAgent != null &&
                    event.agentId == currentAgent &&
                    lastLocalId != null &&
                    event.localMessageId == lastLocalId
                ) {
                    _uiErrorEvents.emit(event.message)
                }
            }
        }
    }

    /**
     * 检查是否已经设置了Agent
     */
    fun isAgentSet(): Boolean {
        return _agentId != null
    }

    /**
     * 获取当前Agent ID
     */
    fun getCurrentAgentId(): String? {
        return _agentId
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
            } else {
                _lastSentLocalMessageId.value = result.getOrNull()?.id
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
