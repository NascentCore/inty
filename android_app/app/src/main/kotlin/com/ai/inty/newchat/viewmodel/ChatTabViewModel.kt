package com.ai.inty.newchat.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.beans.AgentInfo
import com.ai.inty.newchat.data.ChatDataManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * ChatViewModel 缓存
 * 用于管理每个Agent的ChatViewModel实例
 */
private val chatViewModelCache = mutableMapOf<String, ChatViewModel>()

/**
 * ChatTab页面ViewModel
 * 负责管理ChatTab的状态，包括当前页面位置和Agent列表
 */
class ChatTabViewModel(
    private val chatDataManager: ChatDataManager
) : ViewModel() {

    // 当前页面位置
    private val _currentPage = MutableStateFlow(0)
    val currentPage: StateFlow<Int> = _currentPage.asStateFlow()

    // Agent列表
    private val _agents = MutableStateFlow<List<AgentInfo>>(emptyList())
    val agents: StateFlow<List<AgentInfo>> = _agents.asStateFlow()

    // 加载状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    // 错误状态
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        loadAgents()
    }

    /**
     * 加载Agent列表
     */
    private fun loadAgents() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            try {
                val result = chatDataManager.getExploreAgents()
                if (result.isSuccess) {
                    _agents.value = result.getOrNull() ?: emptyList()
                } else {
                    _error.value = result.exceptionOrNull()?.message ?: "加载失败"
                }
            } catch (e: Exception) {
                _error.value = e.message ?: "加载失败"
            } finally {
                _isLoading.value = false
            }
        }
    }

    /**
     * 设置当前页面
     */
    fun setCurrentPage(page: Int) {
        _currentPage.value = page
    }

    /**
     * 刷新Agent列表
     */
    fun refreshAgents() {
        loadAgents()
    }

    /**
     * 获取或创建ChatViewModel实例
     * 使用缓存确保实例持久化
     */
    fun getChatViewModel(agentId: String): ChatViewModel {
        return chatViewModelCache.getOrPut(agentId) {
            ChatViewModel(chatDataManager).also {
                // 设置Agent，确保数据加载
                it.setAgent(agentId)
            }
        }
    }

    /**
     * 清理指定Agent的ChatViewModel缓存
     */
    fun clearChatViewModel(agentId: String) {
        chatViewModelCache.remove(agentId)
    }

    /**
     * 清理所有ChatViewModel缓存
     */
    fun clearAllChatViewModels() {
        chatViewModelCache.clear()
    }
}
