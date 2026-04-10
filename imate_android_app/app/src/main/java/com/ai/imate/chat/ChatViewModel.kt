package com.ai.imate.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.imate.chat.data.ChatMainRepository
import com.ai.imate.chat.data.ChatMessageRepository
import com.ai.imate.chat.data.InitChatOnboardingRepository
import com.ai.imate.chat.data.bean.AgentInfo
import com.ai.imate.chat.local.db.MessageEntity
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.ExperimentalCoroutinesApi

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class ChatViewModel
@Inject
constructor(
    private val chatMessageRepository: ChatMessageRepository,
    private val chatMainRepository: ChatMainRepository,
    private val onboardingRepository: InitChatOnboardingRepository,
) : ViewModel() {

    private val _agent = MutableStateFlow<AgentInfo?>(null)
    val agent: StateFlow<AgentInfo?> = _agent.asStateFlow()

    val isChatWebSocketConnected: StateFlow<Boolean> = chatMainRepository.isChatWebSocketConnected

    /**
     * Once true, we no longer show the full-screen WebSocket loading UI: reconnects only flip
     * [isChatWebSocketConnected] briefly false and would otherwise swap the whole chat UI in/out.
     */
    private val _hasWebSocketConnectedAtLeastOnce = MutableStateFlow(false)
    val hasWebSocketConnectedAtLeastOnce: StateFlow<Boolean> = _hasWebSocketConnectedAtLeastOnce.asStateFlow()

    private val _inputText = MutableStateFlow("")
    val inputText: StateFlow<String> = _inputText.asStateFlow()

    private val _settingsVisible = MutableStateFlow(false)
    val settingsVisible: StateFlow<Boolean> = _settingsVisible.asStateFlow()

    val messages: Flow<PagingData<MessageEntity>> =
        agent
            .map { a -> a?.id?.takeIf { it.isNotBlank() } }
            .distinctUntilChanged()
            .filterNotNull()
            .flatMapLatest { agentId -> chatMessageRepository.getMessagesPagingFlow(agentId) }
            .cachedIn(viewModelScope)

    init {
        viewModelScope.launch {
            chatMainRepository.isChatWebSocketConnected.collect { connected ->
                if (connected) {
                    _hasWebSocketConnectedAtLeastOnce.value = true
                }
            }
        }
        viewModelScope.launch {
            onboardingRepository.onboarding.collect { onboarding ->
                _agent.value = onboarding.createdAgent
            }
        }
    }

    fun onInputChange(text: String) {
        _inputText.value = text
    }

    fun setSettingsVisible(visible: Boolean) {
        _settingsVisible.value = visible
    }

    fun sendMessage() {
        val agentId = agent.value?.id?.takeIf { it.isNotBlank() } ?: return
        val raw = inputText.value
        val trimmedEnd = raw.trimEnd()
        if (trimmedEnd.isEmpty()) return
        viewModelScope.launch {
            try {
                chatMessageRepository.sendTextViaWebSocket(agentId, trimmedEnd)
                _inputText.value = ""
            } catch (e: Exception) {
                GlobalErrorHandler.sendError(e)
            }
        }
    }
}
