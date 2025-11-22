package ai.sxwl.android.data.chat.paging

import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentConstants
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AgentInfoResponse
import ai.sxwl.android.data.cache.AgentCacheProvider
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Agent分页数据源 负责处理聊天agents的分页加载、缓存管理 */
class AgentPagingSource(
    private val useCache: Boolean = true,
    private val sortSeed: Int = IntySetting.randomSortSeed(),
    private val cacheProvider: AgentCacheProvider? = null,
) : PagingSource<Int, AgentInfo>() {

    private val agentApi: IAgentApi by lazy { NetServiceMgr.getAgentApi() }

    companion object {
        private const val PAGE_SIZE = 20
        private const val INITIAL_PAGE = 1
    }

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, AgentInfo> {
        return withContext(Dispatchers.IO) {
            try {
                val page = params.key ?: INITIAL_PAGE
                val pageSize = params.loadSize.coerceAtMost(PAGE_SIZE)

                LogUtils.i("AgentPagingSource - 加载第${page}页，页面大小: $pageSize, sortSeed: $sortSeed")

                // 第一页特殊处理：优先使用缓存数据
                if (page == INITIAL_PAGE && useCache && cacheProvider != null) {
                    val cachedAgents = cacheProvider.getCachedChatAgents()
                    if (cachedAgents.isNotEmpty()) {
                        // 过滤掉id为空的agent，避免key重复问题
                        val validCachedAgents = cachedAgents.filter { it.id.isNotEmpty() }

                        if (validCachedAgents.isNotEmpty()) {
                            // 去重：对缓存数据也进行去重，防止重复数据
                            val uniqueCachedAgents = validCachedAgents.distinctBy { it.id }

                            // 如果有缓存数据，返回缓存数据，同时后台加载网络数据
                            if (cacheProvider.shouldUpdateFromNetwork()) {
                                // 后台静默刷新，不阻塞UI
                                loadFromNetworkAsync(page, pageSize)
                            }

                            val hasMoreData = uniqueCachedAgents.size >= pageSize

                            return@withContext LoadResult.Page(
                                data = uniqueCachedAgents,
                                prevKey = null,
                                nextKey = if (hasMoreData) page + 1 else null,
                            )
                        }
                    }
                }

                // 检查用户账户是否已就绪，如果未就绪则等待或返回空数据
                // 暂时注释掉账户检查逻辑
                // if (!UnifiedStartupManager.isUserAccountReady()) {
                //     LogUtils.i("AgentPagingSource - 用户账户未就绪，等待账户就绪")
                //
                //     // 等待用户账户就绪，最多等待5秒
                //     var waitTime = 0
                //     while (!UnifiedStartupManager.isUserAccountReady() && waitTime < 5000) {
                //         delay(100)
                //         waitTime += 100
                //     }
                //
                //     if (!UnifiedStartupManager.isUserAccountReady()) {
                //         LogUtils.i("AgentPagingSource - 等待超时，返回空数据")
                //         return@withContext LoadResult.Page(
                //             data = emptyList(),
                //             prevKey = null,
                //             nextKey = null,
                //         )
                //     }
                // }

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
                        // 去重：基于 agent.id 进行去重，防止重复数据
                        val uniqueAgents = validAgents.distinctBy { it.id }

                        val hasMore = uniqueAgents.isNotEmpty() && uniqueAgents.size >= pageSize

                        // 缓存第一页数据
                        if (
                            page == INITIAL_PAGE &&
                                uniqueAgents.isNotEmpty() &&
                                cacheProvider != null
                        ) {
                            cacheProvider.cacheChatAgents(uniqueAgents)
                            cacheProvider.refreshChatAgents()
                            LogUtils.i("AgentPagingSource - 缓存第一页数据: ${uniqueAgents.size}个 (去重后)")
                        }

                        LoadResult.Page(
                            data = uniqueAgents,
                            prevKey = if (page == INITIAL_PAGE) null else page - 1,
                            nextKey = if (hasMore) page + 1 else null,
                        )
                    }

                    is NetworkResult.Error -> {
                        LogUtils.e("AgentPagingSource - 网络加载失败: ${result.error}")
                        LoadResult.Error(Exception(result.error))
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("AgentPagingSource - 加载异常: ${e.message}")
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
        return try {
            val result =
                agentApi.chatAgents(
                    page = page,
                    pageSize = pageSize,
                    sort_seed = sortSeed.toString(),
                )

            when (result) {
                is HttpResult.Success -> {
                    NetworkResult.Success(result.data)
                }

                is HttpResult.Failure -> {
                    NetworkResult.Error(result.message)
                }
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.message ?: "Network error")
        }
    }

    /** 异步从网络加载数据（不阻塞UI） */
    private fun loadFromNetworkAsync(page: Int, pageSize: Int) {
        // 在后台协程中执行，不阻塞当前加载
        CoroutineScope(Dispatchers.IO).launch {
            try {
                LogUtils.i(
                    "AgentPagingSource.loadFromNetworkAsync - 后台加载第${page}页，sortSeed: $sortSeed"
                )
                val result = loadFromNetwork(page, pageSize)
                if (result is NetworkResult.Success) {
                    val agents = result.data.list ?: emptyList()
                    // 过滤掉id为空的agent，避免key重复问题
                    val validAgents = agents.filter { it.id.isNotEmpty() }
                    // 去重：基于 agent.id 进行去重，防止重复数据
                    val uniqueAgents = validAgents.distinctBy { it.id }
                    if (uniqueAgents.isNotEmpty() && cacheProvider != null) {
                        // 只更新缓存，不触发刷新，避免触发新的数据流导致重复
                        cacheProvider.cacheChatAgents(uniqueAgents)
                        LogUtils.i("AgentPagingSource - 后台刷新完成: ${uniqueAgents.size}个 (去重后)，已更新缓存")
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("AgentPagingSource - 后台刷新失败: ${e.message}")
            }
        }
    }

    /** 检查是否需要从网络更新数据 */
    private fun shouldUpdateFromNetwork(): Boolean {
        // 暂时简化逻辑，直接返回true
        return true
        // 确保用户账户已就绪（包括游客账户）且token有效
        // return UnifiedStartupManager.isUserAccountReady() &&
        //     IntySetting.isLogin() &&
        //     IntySetting.getCurToken().isNotEmpty()
    }
}

/** 网络请求结果 */
sealed class NetworkResult {
    data class Success(val data: AgentInfoResponse) : NetworkResult()

    data class Error(val error: String) : NetworkResult()
}
