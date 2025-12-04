package com.ai.intellimate.explore.special

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.AgentInfo
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 主题详情页面 ViewModel
 */
class SpecialDetailVM : BaseVM() {
    
    private val _themeTitle = MutableStateFlow("")
    val themeTitle: StateFlow<String> = _themeTitle.asStateFlow()
    
    private val _eventDescription = MutableStateFlow("")
    val eventDescription: StateFlow<String> = _eventDescription.asStateFlow()
    
    private val _isEventExpanded = MutableStateFlow(false)
    val isEventExpanded: StateFlow<Boolean> = _isEventExpanded.asStateFlow()
    
    private val _agents = MutableStateFlow<List<AgentInfo>>(emptyList())
    val agents: StateFlow<List<AgentInfo>> = _agents.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    fun setThemeId(themeId: String) {
        viewModelScope.launch {
            // TODO: 从 API 获取主题数据
            // 暂时使用模拟数据
            _themeTitle.value = "# Merry Christmas"
            _eventDescription.value = "Ready for some holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly, cheerful, and here to light up your winter feed. Come take a look and get into the festive spirit!"
            loadAgents(themeId)
        }
    }
    
    fun setThemeData(title: String, description: String, agents: List<AgentInfo>) {
        _themeTitle.value = title
        _eventDescription.value = description
        _agents.value = agents
    }
    
    fun toggleEventExpanded() {
        _isEventExpanded.value = !_isEventExpanded.value
    }
    
    private fun loadAgents(themeId: String) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                // TODO: 从 API 获取主题下的角色列表
                // 暂时使用空列表
                _agents.value = emptyList()
            } catch (e: Exception) {
                // 错误处理
            } finally {
                _isLoading.value = false
            }
        }
    }
}
