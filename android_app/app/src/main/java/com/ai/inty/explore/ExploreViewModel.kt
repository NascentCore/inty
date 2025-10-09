package com.ai.inty.explore

import androidx.lifecycle.viewModelScope
import androidx.paging.PagingData
import androidx.paging.cachedIn
import com.ai.inty.base.BaseViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.utils.FirebaseManager
import com.ai.inty.utils.UnifiedStartupManager
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/** Explore页面ViewModel 负责管理推荐agents的Paging数据流、刷新、缓存等逻辑 */
class ExploreViewModel : BaseViewModel() {

    private val pagingRepository = ExplorePagingRepository()

    // Paging数据流
    private val _agentsFlow = MutableStateFlow<Flow<PagingData<AgentInfo>>?>(null)

    // 是否已初始化
    private var isInitialized = false

    // 保存滚动位置
    private val _savedFirstVisibleIndex = MutableStateFlow(0)
    val savedFirstVisibleIndex = _savedFirstVisibleIndex
    private val _savedFirstVisibleOffset = MutableStateFlow(0)
    val savedFirstVisibleOffset = _savedFirstVisibleOffset

    /** 初始化Paging数据流 */
    fun initializePagingData() {
        if (isInitialized) return

        EasyLog.log("ExploreViewModel - 初始化Paging数据流")

        // Firebase Analytics - 记录探索页面访问
        FirebaseManager.logEvent(
            "explore_page_view",
            mapOf(
                "page_type" to "recommendations",
                "is_initial_load" to true,
            ),
        )

        // 创建初始数据流（优先使用缓存）
        val initialFlow =
            pagingRepository
                .getInitialRecommendAgents()
                .cachedIn(viewModelScope) // 在ViewModel作用域内缓存

        _agentsFlow.value = initialFlow
        isInitialized = true

        EasyLog.log("ExploreViewModel - Paging数据流初始化完成")
    }

    /** 获取推荐agents的Paging数据流 */
    fun getRecommendAgentsFlow(): Flow<PagingData<AgentInfo>>? {
        if (!isInitialized) {
            initializePagingData()
        }
        return _agentsFlow.value
    }

    /** 强制刷新推荐agents 简化策略：直接使用Paging的刷新机制，让Paging处理状态 */
    fun refreshRecommendAgents() {
        EasyLog.log("ExploreViewModel - 强制刷新推荐agents")

        viewModelScope.launch {
            try {
                // 直接创建新的刷新数据流，让Paging处理状态
                val refreshFlow = pagingRepository.refreshRecommendAgents().cachedIn(viewModelScope)

                _agentsFlow.value = refreshFlow
                EasyLog.log("ExploreViewModel - 刷新数据流创建成功")
            } catch (e: Exception) {
                EasyLog.log(
                    "ExploreViewModel - refreshRecommendAgents异常: ${e.message}",
                    EasyLog.ERROR,
                )
            }
        }
    }

    fun saveScrollPosition(index: Int, offset: Int) {
        _savedFirstVisibleIndex.value = index
        _savedFirstVisibleOffset.value = offset
    }

    /** 监听预加载数据更新 */
    fun startListeningPreloadUpdates() {
        viewModelScope.launch {
            // 监听统一启动管理器的预加载数据更新
            UnifiedStartupManager.recommendedAgents.collect { preloadedAgents ->
                if (preloadedAgents.isEmpty()) {
                    // 监听数据清理（如用户登出）
                    clearData()
                    EasyLog.log("ExploreViewModel - 监听到数据清理")
                } else if (!isInitialized) {
                    // 如果还未初始化且有预加载数据，则初始化
                    initializePagingData()
                    EasyLog.log("ExploreViewModel - 监听到预加载数据，初始化Paging: ${preloadedAgents.size}个")
                }
            }
        }
    }

    /** 获取缓存的agents列表（用于ChatTab显示） */
    fun getCachedAgentsList(): List<AgentInfo> {
        return UnifiedStartupManager.getCurrentRecommendedAgents()
    }

    /** 清空数据（用于用户登出等场景） */
    fun clearData() {
        _agentsFlow.value = null
        isInitialized = false
        EasyLog.log("ExploreViewModel - 清空Paging数据")
    }
}
