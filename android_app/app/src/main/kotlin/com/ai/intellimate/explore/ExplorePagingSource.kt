package com.ai.intellimate.explore

import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentConstants
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AgentInfoResponse
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.PagingSource
import androidx.paging.PagingState
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

    private val agentApi: IAgentApi by lazy { NetServiceMgr.getAgentApi() }

    companion object {
        // 使用统一的常量
        private const val PAGE_SIZE = ExploreConstants.PAGE_SIZE
        private const val INITIAL_PAGE = ExploreConstants.INITIAL_PAGE
    }

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, AgentInfo> {
        return withContext(Dispatchers.IO) {
            try {
                val page = params.key ?: INITIAL_PAGE
                val pageSize = params.loadSize.coerceAtMost(PAGE_SIZE)

                // 第一页特殊处理：优先使用缓存数据
                if (page == INITIAL_PAGE && useCache && cacheProvider != null) {
                    val cachedAgents = cacheProvider.getCachedRecommendedAgents()
                    if (cachedAgents.isNotEmpty()) {
                        // 过滤掉id为空的agent，避免key重复问题
                        val validCachedAgents = cachedAgents.filter { it.id.isNotEmpty() }

                        if (validCachedAgents.isNotEmpty()) {
                            // 如果有缓存数据，返回缓存数据，同时后台加载网络数据
                            if (cacheProvider.shouldUpdateFromNetwork()) {
                                // 后台静默刷新，不阻塞UI
                                loadFromNetworkAsync(page, pageSize)
                            }

                            // 关键修复：即使缓存数据不足一页，也假设有更多数据
                            // 这样Paging会继续尝试加载下一页，确保分页功能正常
                            // 但是要确保缓存数据不为空，避免无限循环
                            return@withContext LoadResult.Page(
                                data = validCachedAgents,
                                prevKey = null,
                                nextKey = if (validCachedAgents.isNotEmpty()) page + 1 else null,
                            )
                        }
                    }
                }

                // 检查用户账户是否已就绪，如果未就绪则等待或返回空数据
                if (!UnifiedStartupManager.isUserAccountReady()) {

                    // 等待用户账户就绪，最多等待5秒（增加等待时间，给登录流程更多时间）
                    var waitTime = 0
                    while (!UnifiedStartupManager.isUserAccountReady() && waitTime < 5000) {
                        delay(100)
                        waitTime += 100
                    }

                    if (!UnifiedStartupManager.isUserAccountReady()) {
                        // 如果账户仍未就绪，返回空数据，但设置 nextKey 以便后续重试
                        // 这样当账户就绪后，Paging 可以自动重试加载
                        LogUtils.w("ExplorePagingSource - 用户账户未就绪，返回空数据但允许重试")
                        return@withContext LoadResult.Page(
                            data = emptyList(),
                            prevKey = null,
                            nextKey = INITIAL_PAGE, // 设置 nextKey，允许后续重试
                        )
                    }
                }

                // 从网络加载数据
                val result = loadFromNetwork(page, pageSize)

                when (result) {
                    is NetworkResult.Success -> {
                        val agents = result.data.list ?: emptyList()
                        // 过滤掉id为空的agent，避免key重复问题
                        // 同时过滤掉 IntelliMate agent
                        val validAgents =
                            agents.filter { agent ->
                                agent.id.isNotEmpty() &&
                                        !AgentConstants.isIntelliMateAgent(agent.id, agent.name)
                            }
                        val hasMore = validAgents.isNotEmpty() && validAgents.size >= pageSize

                        // 缓存第一页数据
                        if (
                            page == INITIAL_PAGE &&
                                validAgents.isNotEmpty() &&
                                cacheProvider != null
                        ) {
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
        // 返回最近访问的页面，用于刷新时定位
        return state.anchorPosition?.let { anchorPosition ->
            state.closestPageToPosition(anchorPosition)?.prevKey?.plus(1)
                ?: state.closestPageToPosition(anchorPosition)?.nextKey?.minus(1)
        }
    }

    /** 从网络加载数据 */
    private suspend fun loadFromNetwork(page: Int, pageSize: Int): NetworkResult {
        val startTime = System.currentTimeMillis()
        return try {
            val result =
                agentApi.exploreAgents(
                    page = page,
                    pageSize = pageSize,
                    sort_seed = sortSeed.toString(),
                )

            val responseTime = System.currentTimeMillis() - startTime

            when (result) {
                is HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    val validAgents = agents.filter { it.id.isNotEmpty() }
                    val agentsCount = validAgents.size

                    // 上报成功事件
                    fetchCallback?.onSuccess(page, pageSize, responseTime, agentsCount, sortSeed)

                    NetworkResult.Success(result.data)
                }
                is HttpResult.Failure -> {
                    // 上报失败事件
                    fetchCallback?.onFailure(page, pageSize, responseTime, result.message, sortSeed)

                    NetworkResult.Error(result.message)
                }
            }
        } catch (e: Exception) {
            val responseTime = System.currentTimeMillis() - startTime

            // 上报异常事件
            fetchCallback?.onException(page, pageSize, responseTime, e, sortSeed)

            NetworkResult.Error(e.message ?: "Network error")
        }
    }

    /** 异步从网络加载数据（不阻塞UI） */
    private fun loadFromNetworkAsync(page: Int, pageSize: Int) {
        // 在后台协程中执行，不阻塞当前加载
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val result = loadFromNetwork(page, pageSize)
                if (result is NetworkResult.Success) {
                    val agents = result.data.list ?: emptyList()
                    // 过滤掉id为空的agent，避免key重复问题
                    val validAgents = agents.filter { it.id.isNotEmpty() }
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

/** 网络请求结果 */
sealed class NetworkResult {
    data class Success(val data: AgentInfoResponse) : NetworkResult()

    data class Error(val error: String) : NetworkResult()
}
