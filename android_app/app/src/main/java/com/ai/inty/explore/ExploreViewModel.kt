package com.ai.inty.explore

import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.utils.UnifiedStartupManager
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Explore页面ViewModel
 * 负责管理推荐agents的状态、分页加载、缓存等逻辑
 */
class ExploreViewModel : BaseViewModel() {
    
    private val repository = ExploreRepository()
    
    // 推荐agents列表
    val agentList = mutableStateListOf<AgentInfo>()
    
    // 加载状态
    private var currentPage = 1
    private var _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()
    
    private var hasMoreData = true
    
    // 是否已初始化缓存数据
    private var isCacheInitialized = false
    
    /**
     * 初始化缓存数据（立即同步加载，用于快速展示）
     */
    fun initializeCacheData() {
        if (isCacheInitialized) return
        
        // 从统一启动管理器获取预加载数据
        val preloadedAgents = UnifiedStartupManager.getCurrentRecommendedAgents()
        if (preloadedAgents.isNotEmpty()) {
            agentList.clear()
            agentList.addAll(preloadedAgents)
            isCacheInitialized = true
            EasyLog.log("ExploreViewModel - 使用预加载数据: ${preloadedAgents.size}个")
        } else {
            EasyLog.log("ExploreViewModel - 无缓存数据，等待网络加载")
        }
    }
    
    /**
     * 初始化加载推荐agents
     */
    fun getRecommendAgents() {
        EasyLog.log("ExploreViewModel - 开始加载推荐agents")
        
        // 第一步：立即初始化缓存数据（同步，快速展示）
        initializeCacheData()
        
        // 第二步：如果已有缓存数据，直接返回，避免重复加载
        if (agentList.isNotEmpty()) {
            EasyLog.log("ExploreViewModel - 已有缓存数据，跳过网络请求")
            return
        }
        
        // 第三步：如果没有缓存数据，进行网络请求
        currentPage = 1
        hasMoreData = true
        
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = repository.getRecommendAgents(useCache = false)
                
                // 使用网络数据
                result.networkAgents?.let { networkAgents ->
                    if (networkAgents.isNotEmpty()) {
                        agentList.clear()
                        agentList.addAll(networkAgents)
                        hasMoreData = result.hasMoreData
                        isCacheInitialized = true
                        EasyLog.log("ExploreViewModel - 网络数据加载成功: ${networkAgents.size}个")
                    }
                }
                
                // 处理网络错误
                result.networkError?.let { error ->
                    EasyLog.log("ExploreViewModel - 网络加载失败: $error", EasyLog.WARN)
                }
                
            } catch (e: Exception) {
                EasyLog.log("ExploreViewModel - getRecommendAgents异常: ${e.message}", EasyLog.ERROR)
            }
        }
    }
    
    /**
     * 强制刷新推荐agents
     */
    fun refreshRecommendAgents() {
        EasyLog.log("ExploreViewModel - 强制刷新推荐agents")
        currentPage = 1
        hasMoreData = true
        
        _isLoading.update { true }
        
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = repository.refreshRecommendAgents()
                
                when {
                    result.networkAgents != null -> {
                        agentList.clear()
                        agentList.addAll(result.networkAgents)
                        hasMoreData = result.hasMoreData
                        EasyLog.log("ExploreViewModel - 刷新成功: ${result.networkAgents.size}个")
                    }
                    result.networkError != null -> {
                        EasyLog.log("ExploreViewModel - 刷新失败: ${result.networkError}", EasyLog.ERROR)
                    }
                }
                
            } catch (e: Exception) {
                EasyLog.log("ExploreViewModel - refreshRecommendAgents异常: ${e.message}", EasyLog.ERROR)
            } finally {
                _isLoading.update { false }
            }
        }
    }
    
    /**
     * 加载更多推荐agents
     */
    fun loadMoreRecommendAgents() {
        if (!_isLoading.value && hasMoreData) {
            EasyLog.log("ExploreViewModel - 开始加载第${currentPage + 1}页")
            currentPage++
            
            _isLoading.update { true }
            
            viewModelScope.launch(Dispatchers.IO) {
                try {
                    val result = repository.loadMoreRecommendAgents(currentPage)
                    
                    when {
                        result.networkAgents != null -> {
                            if (result.networkAgents.isEmpty()) {
                                hasMoreData = false
                                EasyLog.log("ExploreViewModel - 第${currentPage}页数据为空，没有更多数据")
                            } else {
                                agentList.addAll(result.networkAgents)
                                hasMoreData = result.hasMoreData
                                EasyLog.log("ExploreViewModel - 追加第${currentPage}页数据: ${result.networkAgents.size}个，总计: ${agentList.size}个")
                            }
                        }
                        result.networkError != null -> {
                            EasyLog.log("ExploreViewModel - 第${currentPage}页加载失败: ${result.networkError}", EasyLog.ERROR)
                            // 如果加载失败，回退页码
                            if (currentPage > 1) {
                                currentPage--
                            }
                        }
                    }
                    
                } catch (e: Exception) {
                    EasyLog.log("ExploreViewModel - loadMoreRecommendAgents异常: ${e.message}", EasyLog.ERROR)
                    // 如果加载失败，回退页码
                    if (currentPage > 1) {
                        currentPage--
                    }
                } finally {
                    _isLoading.update { false }
                }
            }
        } else {
            EasyLog.log("ExploreViewModel - 跳过加载: isLoading=${_isLoading.value}, hasMoreData=$hasMoreData")
        }
    }
    
    /**
     * 监听预加载数据更新
     */
    fun startListeningPreloadUpdates() {
        viewModelScope.launch {
            // 监听统一启动管理器的预加载数据更新
            UnifiedStartupManager.recommendedAgents.collect { preloadedAgents ->
                if (preloadedAgents.isNotEmpty() && preloadedAgents != agentList.toList()) {
                    agentList.clear()
                    agentList.addAll(preloadedAgents)
                    isCacheInitialized = true
                    EasyLog.log("ExploreViewModel - 监听到预加载数据更新: ${preloadedAgents.size}个")
                } else if (preloadedAgents.isEmpty() && agentList.isNotEmpty()) {
                    // 监听数据清理（如用户登出）
                    clearData()
                    EasyLog.log("ExploreViewModel - 监听到数据清理")
                }
            }
        }
    }
    
    /**
     * 清空数据（用于用户登出等场景）
     */
    fun clearData() {
        agentList.clear()
        currentPage = 1
        hasMoreData = true
        _isLoading.update { false }
        isCacheInitialized = false
        EasyLog.log("ExploreViewModel - 清空数据")
    }
}
