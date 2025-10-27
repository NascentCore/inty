package ai.sxwl.android.data.chat.paging

import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AgentInfoResponse
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Agent分页数据源
 * 负责处理聊天agents的分页加载、缓存管理
 */
class AgentPagingSource(
    private val useCache: Boolean = true,
    private val sortSeed: Int = IntySetting.randomSortSeed(),
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

                LogUtils.i("AgentPagingSource - 加载第${page}页，页面大小: $pageSize")

                // 第一页特殊处理：优先使用缓存数据
                if (page == INITIAL_PAGE && useCache) {
                    // 暂时注释掉缓存逻辑，避免依赖问题
                    // val cachedAgents = UnifiedStartupManager.getCurrentChatAgents()
                    // if (cachedAgents.isNotEmpty()) {
                    //     // 如果有缓存数据，返回缓存数据，同时后台加载网络数据
                    //     if (shouldUpdateFromNetwork()) {
                    //         // 后台静默刷新，不阻塞UI
                    //         loadFromNetworkAsync(page, pageSize)
                    //     }
                    //
                    //     // 返回缓存数据，假设有更多数据以支持分页
                    //     return@withContext LoadResult.Page(
                    //         data = cachedAgents,
                    //         prevKey = null,
                    //         nextKey = if (cachedAgents.isNotEmpty()) page + 1 else null,
                    //     )
                    // }
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
                        val hasMore = agents.isNotEmpty() && agents.size >= pageSize

                        // 缓存第一页数据
                        if (page == INITIAL_PAGE && agents.isNotEmpty()) {
                            // 暂时注释掉缓存逻辑
                            // AgentCacheManager.cacheChatAgents(agents)
                            // UnifiedStartupManager.refreshChatAgents()
                            LogUtils.i("AgentPagingSource - 缓存第一页数据: ${agents.size}个")
                        }

                        LoadResult.Page(
                            data = agents,
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
            val result = agentApi.chatAgents(
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
                val result = loadFromNetwork(page, pageSize)
                if (result is NetworkResult.Success) {
                    val agents = result.data.list ?: emptyList()
                    if (agents.isNotEmpty()) {
                        // 暂时注释掉缓存逻辑
                        // AgentCacheManager.cacheChatAgents(agents)
                        // UnifiedStartupManager.refreshChatAgents()
                        LogUtils.i("AgentPagingSource - 后台刷新完成: ${agents.size}个")
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
