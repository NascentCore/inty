package com.ai.intellimate.explore

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentConstants
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AgentInfoResponse
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.utils.UnifiedStartupManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Explore接口调用结果回调 用于将接口调用情况传递给ViewModel进行事件上报 */
interface ExploreFetchCallback {
    suspend fun onSuccess(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        agentsCount: Int,
        sortSeed: Int,
    )

    suspend fun onFailure(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        errorMessage: String,
        sortSeed: Int,
    )

    suspend fun onException(
        page: Int,
        pageSize: Int,
        responseTime: Long,
        exception: Exception,
        sortSeed: Int,
    )
}

/** Explore页面的Paging数据源 负责处理推荐agents的分页加载、缓存管理 */
class ExplorePagingSource(
    private val useCache: Boolean = true,
    private val sortSeed: Int = IntySetting.sortSeed(),
    private val cacheProvider: RecommendedAgentCacheProvider? = null,
    private val fetchCallback: ExploreFetchCallback? = null,
) : PagingSource<Int, AgentInfo>() {

    companion object {
        private const val PAGE_SIZE = UiConfigs.Explore.PAGE_SIZE
        private const val INITIAL_PAGE = UiConfigs.Explore.INITIAL_PAGE
    }

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, AgentInfo> {
        return withContext(Dispatchers.IO) {
            try {
                val page = params.key ?: INITIAL_PAGE
                val pageSize = params.loadSize.coerceAtMost(PAGE_SIZE)

                if (page == INITIAL_PAGE && useCache && cacheProvider != null) {
                    val cachedAgents = cacheProvider.getCachedRecommendedAgents()
                    if (cachedAgents.isNotEmpty()) {
                        val validCachedAgents = cachedAgents.filter { agent ->
                            agent.id.isNotEmpty() &&
                                    !AgentConstants.isIntelliMateAgent(agent.id, agent.name)
                        }

                        if (validCachedAgents.isNotEmpty()) {
                            if (cacheProvider.shouldUpdateFromNetwork()) {
                                loadFromNetworkAsync(page, pageSize)
                            }

                            return@withContext LoadResult.Page(
                                data = validCachedAgents,
                                prevKey = null,
                                nextKey = page + 1,
                            )
                        }
                    }
                }

                if (!UnifiedStartupManager.isUserAccountReady()) {
                    var waitTime = 0
                    while (!UnifiedStartupManager.isUserAccountReady() && waitTime < 5000) {
                        delay(100)
                        waitTime += 100
                    }

                    if (!UnifiedStartupManager.isUserAccountReady()) {
                        LogUtils.w("ExplorePagingSource - 用户账户未就绪，返回空数据但允许重试")
                        return@withContext LoadResult.Page(
                            data = emptyList(),
                            prevKey = null,
                            nextKey = INITIAL_PAGE,
                        )
                    }
                }

                val result = loadFromNetwork(page, pageSize)

                when (result) {
                    is NetworkResult.Success -> {
                        val agents = result.data.list ?: emptyList()
                        val validAgents = agents.filter { agent ->
                            agent.id.isNotEmpty() &&
                                    !AgentConstants.isIntelliMateAgent(agent.id, agent.name)
                        }

                        val hasMore = if (result.data.totalPages > 0) {
                            page < result.data.totalPages
                        } else {
                            val estimatedLoadedCount = (page - 1) * pageSize + agents.size
                            estimatedLoadedCount < result.data.total
                        }

                        if (page == INITIAL_PAGE && validAgents.isNotEmpty() && cacheProvider != null) {
                            cacheProvider.cacheRecommendedAgents(validAgents)
                            cacheProvider.refreshRecommendedAgents()
                        }

                        LoadResult.Page(
                            data = validAgents,
                            prevKey = if (page == INITIAL_PAGE) null else page - 1,
                            nextKey = if (hasMore) page + 1 else null,
                        )
                    }
                    is NetworkResult.Error -> {
                        LogUtils.e("ExplorePagingSource - 网络加载失败: ${result.error}")
                        LoadResult.Error(Exception(result.error))
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ExplorePagingSource - 加载异常: ${e.message}")
                LoadResult.Error(e)
            }
        }
    }

    override fun getRefreshKey(state: PagingState<Int, AgentInfo>): Int? {
        return state.anchorPosition?.let { anchorPosition ->
            state.closestPageToPosition(anchorPosition)?.prevKey?.plus(1)
                ?: state.closestPageToPosition(anchorPosition)?.nextKey?.minus(1)
        }
    }

    private suspend fun loadFromNetwork(page: Int, pageSize: Int): NetworkResult {
        val startTime = System.currentTimeMillis()
        return try {
            val result =
                NetServiceMgr.getAgentApi()
                    .exploreAgents(
                        page = page,
                        pageSize = pageSize,
                        sort_seed = sortSeed.toString(),
                    )

            val responseTime = System.currentTimeMillis() - startTime

            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    val validAgents = agents.filter { agent ->
                        agent.id.isNotEmpty() &&
                                !AgentConstants.isIntelliMateAgent(agent.id, agent.name)
                    }

                    fetchCallback?.onSuccess(
                        page,
                        pageSize,
                        responseTime,
                        validAgents.size,
                        sortSeed
                    )
                    NetworkResult.Success(result.data)
                }
                is HttpResult.Failure -> {
                    fetchCallback?.onFailure(page, pageSize, responseTime, result.message, sortSeed)
                    NetworkResult.Error(result.message)
                }
            }
        } catch (e: Exception) {
            val responseTime = System.currentTimeMillis() - startTime
            fetchCallback?.onException(page, pageSize, responseTime, e, sortSeed)

            NetworkResult.Error(e.message ?: "Network error")
        }
    }

    private fun loadFromNetworkAsync(page: Int, pageSize: Int) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val result = loadFromNetwork(page, pageSize)
                if (result is NetworkResult.Success) {
                    val agents = result.data.list ?: emptyList()
                    val validAgents = agents.filter { agent ->
                        agent.id.isNotEmpty() &&
                                !AgentConstants.isIntelliMateAgent(agent.id, agent.name)
                    }
                    if (validAgents.isNotEmpty() && cacheProvider != null) {
                        cacheProvider.cacheRecommendedAgents(validAgents)
                        cacheProvider.refreshRecommendedAgents()
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ExplorePagingSource - 后台刷新失败: ${e.message}")
            }
        }
    }
}

sealed class NetworkResult {
    data class Success(val data: AgentInfoResponse) : NetworkResult()

    data class Error(val error: String) : NetworkResult()
}
