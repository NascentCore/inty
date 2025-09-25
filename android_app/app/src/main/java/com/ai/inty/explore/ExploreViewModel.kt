package com.ai.inty.explore

import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseViewModel
import com.ai.inty.beans.AgentInfo
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
    
    /**
     * 初始化加载推荐agents
     */
    fun getRecommendAgents() {
        EasyLog.log("ExploreViewModel - 开始加载推荐agents")
        currentPage = 1
        hasMoreData = true
        
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = repository.getRecommendAgents(useCache = true)
                
                // 先使用缓存数据快速展示
                if (result.cachedAgents.isNotEmpty()) {
                    agentList.clear()
                    agentList.addAll(result.cachedAgents)
                    EasyLog.log("ExploreViewModel - 使用缓存数据快速展示: ${result.cachedAgents.size}个")
                }
                
                // 如果有网络数据，静默更新
                result.networkAgents?.let { networkAgents ->
                    if (networkAgents.isNotEmpty()) {
                        agentList.clear()
                        agentList.addAll(networkAgents)
                        hasMoreData = result.hasMoreData
                        EasyLog.log("ExploreViewModel - 静默更新网络数据: ${networkAgents.size}个")
                    }
                }
                
                // 处理网络错误
                result.networkError?.let { error ->
                    EasyLog.log("ExploreViewModel - 网络更新失败: $error", EasyLog.WARN)
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
     * 清空数据（用于用户登出等场景）
     */
    fun clearData() {
        agentList.clear()
        currentPage = 1
        hasMoreData = true
        _isLoading.update { false }
        EasyLog.log("ExploreViewModel - 清空数据")
    }
}
