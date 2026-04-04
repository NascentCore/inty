package com.ai.imate.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

enum class MessageRole {
    USER,
    OFFICIAL_ASSISTANT,
}

data class ChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: MessageRole,
    val content: String,
)

interface ChatRepository {
    val messages: StateFlow<List<ChatMessage>>
    suspend fun sendUserMessage(content: String, officialAssistantEnabled: Boolean)
    suspend fun clear()
}

class InMemoryChatRepository : ChatRepository {
    private val messagesState = MutableStateFlow(emptyList<ChatMessage>())
    override val messages: StateFlow<List<ChatMessage>> = messagesState.asStateFlow()

    override suspend fun sendUserMessage(content: String, officialAssistantEnabled: Boolean) {
        val userMessage = ChatMessage(role = MessageRole.USER, content = content)
        val updated = messagesState.value.toMutableList()
        updated.add(userMessage)
        if (officialAssistantEnabled) {
            updated.add(
                ChatMessage(
                    role = MessageRole.OFFICIAL_ASSISTANT,
                    content = "Official Assistant: I got it - $content",
                )
            )
        }
        messagesState.value = updated
    }

    override suspend fun clear() {
        messagesState.value = emptyList()
    }
}

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val input: String = "",
)

class ChatViewModel(private val chatRepository: ChatRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            chatRepository.messages.collect { messages ->
                _uiState.value = _uiState.value.copy(messages = messages)
            }
        }
    }

    fun updateInput(value: String) {
        _uiState.value = _uiState.value.copy(input = value)
    }

    fun sendMessage(officialAssistantEnabled: Boolean) {
        val content = _uiState.value.input.trim()
        if (content.isBlank()) {
            return
        }
        viewModelScope.launch {
            chatRepository.sendUserMessage(content = content, officialAssistantEnabled = officialAssistantEnabled)
            _uiState.value = _uiState.value.copy(input = "")
        }
    }

    fun clearMessages() {
        viewModelScope.launch {
            chatRepository.clear()
        }
    }

    companion object {
        fun factory(chatRepository: ChatRepository): ViewModelProvider.Factory {
            return object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    return ChatViewModel(chatRepository) as T
                }
            }
        }
    }
}
