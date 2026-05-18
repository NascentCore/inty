package com.inty.imate.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.core.utils.LogUtils
import com.inty.imate.chat.data.ChatMainRepository
import com.inty.imate.chat.data.ChatMessageRepository
import com.inty.imate.account.data.AuthRepository
import com.inty.imate.chat.data.InitChatOnboardingRepository
import com.inty.imate.chat.data.bean.AgentInfo
import com.inty.imate.chat.local.db.MessageEntity
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
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
    private val authRepository: AuthRepository,
) : ViewModel() {

    val isLoggedIn: StateFlow<Boolean> =
        authRepository.isLogin.stateIn(viewModelScope, SharingStarted.Eagerly, false)

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
        chatMainRepository.agentStatusLineUpdates
            .onEach { (agentId, text) ->
                val cur = _agent.value ?: return@onEach
                if (cur.id != agentId) return@onEach
                _agent.value = cur.copy(statusLine = text)
            }
            .launchIn(viewModelScope)
        viewModelScope.launch {
            onboardingRepository.onboarding.collect { onboarding ->
                _agent.value = onboarding.createdAgent
            }
        }
    }

    fun refreshAgentFromServer() {
        viewModelScope.launch {
            val id = agent.value?.id?.takeIf { it.isNotBlank() } ?: return@launch
            try {
                onboardingRepository.refreshCreatedAgentFromServer(id)
            } catch (e: Exception) {
                LogUtils.d("refreshAgentFromServer failed: ${e.message}")
            }
        }
    }

    fun onInputChange(text: String) {
        _inputText.value = text
    }

    fun setSettingsVisible(visible: Boolean) {
        _settingsVisible.value = visible
    }

    fun logout() {
        viewModelScope.launch { authRepository.logout() }
    }

    fun deleteAccount() {
        viewModelScope.launch {
            try {
                authRepository.deleteAccount()
            } catch (e: Exception) {
                GlobalErrorHandler.sendError(e)
            }
        }
    }

    fun sendImplicitUserSignedOnIfNeeded(agentId: String) {
        viewModelScope.launch {
            try {
                chatMessageRepository.sendImplicitUserSignedOnIfNeeded(agentId)
            } catch (e: Exception) {
                LogUtils.d("sendImplicitUserSignedOnIfNeeded failed: ${e.message}")
            }
        }
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
