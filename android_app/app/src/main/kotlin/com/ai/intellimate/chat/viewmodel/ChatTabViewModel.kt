package com.ai.inty.chat.viewmodel

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.AgentInfo
import androidx.lifecycle.viewModelScope
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.ai.inty.chat.paging.ChatPagingRepository
import com.ai.inty.utils.UnifiedStartupManager
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/** ChatTab页面ViewModel 负责管理聊天agents的Paging数据流、刷新、缓存等逻辑 独立于ExploreTab，使用chatAgents API */
class ChatTabViewModel : BaseVM() {

    private val pagingRepository = ChatPagingRepository()

    // Paging数据流
    private val _agentsFlow = MutableStateFlow<Flow<PagingData<AgentInfo>>?>(null)

    // 是否已初始化
    private var isInitialized = false

    /** 初始化Paging数据流 */
    fun initializePagingData() {
        if (isInitialized) return

        // 创建初始数据流（优先使用缓存）
        val initialFlow =
            pagingRepository.getInitialChatAgents().cachedIn(viewModelScope) // 在ViewModel作用域内缓存

        _agentsFlow.value = initialFlow
        isInitialized = true

    }

    /** 获取聊天agents的Paging数据流 */
    fun getChatAgentsFlow(): Flow<PagingData<AgentInfo>>? {
        if (!isInitialized) {
            initializePagingData()
        }
        return _agentsFlow.value
    }

    /** 监听预加载数据更新 */
    fun startListeningPreloadUpdates() {
        viewModelScope.launch {
            // 监听统一启动管理器的预加载数据更新
            UnifiedStartupManager.chatAgents.collect { preloadedAgents ->
                if (preloadedAgents.isEmpty()) {
                    // 监听数据清理（如用户登出）
                    clearData()
                } else if (!isInitialized) {
                    // 如果还未初始化且有预加载数据，则初始化
                    initializePagingData()
                }
            }
        }
    }

    /** 清空数据（用于用户登出等场景） */
    fun clearData() {
        _agentsFlow.value = null
        isInitialized = false
    }
}
