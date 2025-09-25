package com.ai.inty.explore

import com.ai.inty.beans.AgentInfo
import com.ai.inty.net.IAgentApi
import com.ai.inty.utils.AgentCacheManager
import com.ai.inty.utils.AppStartupManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Explore数据仓库
 * 负责处理推荐agents的数据请求、缓存管理
 */
class ExploreRepository {
    
    private val agentApi: IAgentApi by lazy {
        TheRouter.get(IAgentApi::class.java)
            ?: throw IllegalStateException("IAgentApi not found in TheRouter")
    }
    
    // 用于推荐接口的sort seed
    private var sortSeed = IntySetting.sortSeed()
    
    /**
     * 获取推荐agents（第一页）
     * @param useCache 是否优先使用缓存数据
     * @return ExploreResult 包含缓存数据和网络数据
     */
    suspend fun getRecommendAgents(useCache: Boolean = true): ExploreResult {
        return withContext(Dispatchers.IO) {
            try {
                // 第一步：如果有缓存数据，先使用缓存数据快速展示
                val cachedAgents = if (useCache) {
                    AppStartupManager.cachedAgents.value
                } else {
                    emptyList()
                }
                
                // 第二步：后台静默刷新数据（无论是否有缓存）
                val networkResult = if (shouldUpdateFromNetwork()) {
                    loadAgentsFromNetwork(page = 1, pageSize = 10)
                } else {
                    null
                }
                
                ExploreResult(
                    cachedAgents = cachedAgents,
                    networkAgents = networkResult?.data?.list,
                    networkError = networkResult?.error,
                    hasMoreData = networkResult?.hasMore ?: true
                )
            } catch (e: Exception) {
                EasyLog.log("ExploreRepository - getRecommendAgents异常: ${e.message}", EasyLog.ERROR)
                ExploreResult(
                    cachedAgents = emptyList(),
                    networkAgents = null,
                    networkError = e.message,
                    hasMoreData = false
                )
            }
        }
    }
    
    /**
     * 刷新推荐agents（强制从网络获取）
     */
    suspend fun refreshRecommendAgents(): ExploreResult {
        // 重置sort seed
        sortSeed = sortSeed + 1
        IntySetting.updateSortSeed(sortSeed)
        
        return withContext(Dispatchers.IO) {
            try {
                val result = loadAgentsFromNetwork(page = 1, pageSize = 10)
                
                ExploreResult(
                    cachedAgents = emptyList(),
                    networkAgents = result.data?.list,
                    networkError = result.error,
                    hasMoreData = result.hasMore
                )
            } catch (e: Exception) {
                EasyLog.log("ExploreRepository - refreshRecommendAgents异常: ${e.message}", EasyLog.ERROR)
                ExploreResult(
                    cachedAgents = emptyList(),
                    networkAgents = null,
                    networkError = e.message,
                    hasMoreData = false
                )
            }
        }
    }
    
    /**
     * 加载更多推荐agents
     */
    suspend fun loadMoreRecommendAgents(page: Int): ExploreResult {
        return withContext(Dispatchers.IO) {
            try {
                val result = loadAgentsFromNetwork(page = page, pageSize = 10)
                
                ExploreResult(
                    cachedAgents = emptyList(),
                    networkAgents = result.data?.list,
                    networkError = result.error,
                    hasMoreData = result.hasMore
                )
            } catch (e: Exception) {
                EasyLog.log("ExploreRepository - loadMoreRecommendAgents异常: ${e.message}", EasyLog.ERROR)
                ExploreResult(
                    cachedAgents = emptyList(),
                    networkAgents = null,
                    networkError = e.message,
                    hasMoreData = false
                )
            }
        }
    }
    
    /**
     * 从网络加载agents数据
     */
    private suspend fun loadAgentsFromNetwork(page: Int, pageSize: Int): NetworkResult {
        return try {
            val result = agentApi.recommendAgents(
                page = page,
                pageSize = pageSize,
                sort_seed = sortSeed.toString()
            )
            
            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    val hasMore = agents.isNotEmpty() && agents.size >= pageSize
                    
                    // 缓存第一页数据
                    if (page == 1) {
                        AgentCacheManager.cacheAgents(agents)
                        AppStartupManager.updateCachedAgents(agents)
                    }
                    
                    NetworkResult(
                        data = result.data,
                        error = null,
                        hasMore = hasMore
                    )
                }
                is HttpResult.Failure -> {
                    NetworkResult(
                        data = null,
                        error = result.message,
                        hasMore = false
                    )
                }
            }
        } catch (e: Exception) {
            NetworkResult(
                data = null,
                error = e.message,
                hasMore = false
            )
        }
    }
    
    /**
     * 检查是否需要从网络更新数据
     */
    private fun shouldUpdateFromNetwork(): Boolean {
        return IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
    }
}

/**
 * Explore数据结果
 */
data class ExploreResult(
    val cachedAgents: List<AgentInfo>,
    val networkAgents: List<AgentInfo>?,
    val networkError: String?,
    val hasMoreData: Boolean
)

/**
 * 网络请求结果
 */
private data class NetworkResult(
    val data: com.ai.inty.beans.AgentInfoResponse?,
    val error: String?,
    val hasMore: Boolean
)
