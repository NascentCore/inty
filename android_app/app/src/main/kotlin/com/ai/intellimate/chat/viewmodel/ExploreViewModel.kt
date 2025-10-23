package com.ai.intellimate.chat.viewmodel

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.chat.data.ChatDataManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Explore页面ViewModel
 * 负责管理探索页面的Agent列表
 */
class ExploreViewModel(
    private val chatDataManager: ChatDataManager
) : ViewModel() {

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
}
