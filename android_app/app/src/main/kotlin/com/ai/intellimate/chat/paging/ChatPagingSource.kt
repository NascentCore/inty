package com.ai.intellimate.chat.paging

import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AgentInfoResponse
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.ai.intellimate.chat.constants.ChatConstants
import com.ai.intellimate.utils.AgentCacheManager
import com.ai.intellimate.utils.UnifiedStartupManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** 聊天页面的分页数据源负责处理聊天代理的分页加载、服务器管理 使用chatAgents API，与exploreAgents区分开 */
class ChatPagingSource(
    private val useCache: Boolean = true,
    private val sortSeed: Int = IntySetting.randomSortSeed(),
) : PagingSource<Int, AgentInfo>() {

    private val agentApi: IAgentApi by lazy {
        NetServiceMgr.getAgentApi()
    }

    companion object {
// 使用统一的常量
        private const val PAGE_SIZE = ChatConstants.PAGE_SIZE
        private const val INITIAL_PAGE = ChatConstants.INITIAL_PAGE
    }

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, AgentInfo> {
        return withContext(Dispatchers.IO) {
            try {
                val page = params.key ?: INITIAL_PAGE
                val pageSize = params.loadSize.coerceAtMost(PAGE_SIZE)

                LogUtils.i("ChatPagingSource - 加载第${page}页，页面大小: $pageSize")
//第一页特殊处理：优先使用服务器数据
                if (page == INITIAL_PAGE && useCache) {
                    val cachedAgents = UnifiedStartupManager.getCurrentChatAgents()
                    if (cachedAgents.isNotEmpty()) {
// 如果有缓存数据，返回缓存数据，同时后台加载网络数据
                        if (shouldUpdateFromNetwork()) {
// 后台安静默刷新，不阻塞UI
                            loadFromNetworkAsync(page, pageSize)
                        }
// 返回存储数据，假设有更多数据支持分页
                        return@withContext LoadResult.Page(
                            data = cachedAgents,
                            prevKey = null,
                            nextKey = if (cachedAgents.isNotEmpty()) page + 1 else null,
                        )
                    }
                }
// 检查用户账户是否已就绪，如果未就绪则等待或返回空数据
                if (!UnifiedStartupManager.isUserAccountReady()) {
                    LogUtils.i("ChatPagingSource - 用户账户未就绪，等待账户就绪")
// 等待用户账户就绪，最多等待5秒
                    var waitTime = 0
                    while (!UnifiedStartupManager.isUserAccountReady() && waitTime < 5000) {
                        delay(100)
                        waitTime += 100
                    }

                    if (!UnifiedStartupManager.isUserAccountReady()) {
                        LogUtils.i("ChatPagingSource - 等待超时，返回空数据")
                        return@withContext LoadResult.Page(
                            data = emptyList(),
                            prevKey = null,
                            nextKey = null,
                        )
                    }
                }
// 来自网络加载数据
                val result = loadFromNetwork(page, pageSize)

                when (result) {
                    is NetworkResult.Success -> {
                        val agents = result.data.list ?: emptyList()
                        val hasMore = agents.isNotEmpty() && agents.size >= pageSize
// 存储第一页数据
                        if (page == INITIAL_PAGE && agents.isNotEmpty()) {
                            AgentCacheManager.cacheChatAgents(agents)
                            UnifiedStartupManager.refreshChatAgents()
                            LogUtils.i("ChatPagingSource - 缓存第一页数据: ${agents.size}个")
                        }

                        LoadResult.Page(
                            data = agents,
                            prevKey = if (page == INITIAL_PAGE) null else page - 1,
                            nextKey = if (hasMore) page + 1 else null,
                        )
                    }

                    is NetworkResult.Error -> {
                        LogUtils.e("ChatPagingSource - 网络加载失败: ${result.error}")
                        LoadResult.Error(Exception(result.error))
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ChatPagingSource - 加载异常: ${e.message}")
                LoadResult.Error(e)
            }
        }
    }

    override fun getRefreshKey(state: PagingState<Int, AgentInfo>): Int? {
// 返回最近访问的页面，用于刷新时间定位
        return state.anchorPosition?.let { anchorPosition ->
            state.closestPageToPosition(anchorPosition)?.prevKey?.plus(1)
                ?: state.closestPageToPosition(anchorPosition)?.nextKey?.minus(1)
        }
    }

    /** 来自网络加载数据 */
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
// 在后台协程中执行，不阻止当前加载
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val result = loadFromNetwork(page, pageSize)
                if (result is NetworkResult.Success) {
                    val agents = result.data.list ?: emptyList()
                    if (agents.isNotEmpty()) {
                        AgentCacheManager.cacheChatAgents(agents)
                        UnifiedStartupManager.refreshChatAgents()
                        LogUtils.i("ChatPagingSource - 后台刷新完成: ${agents.size}个")
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ChatPagingSource - 后台刷新失败: ${e.message}")
            }
        }
    }

    /** 检查是否需要从网络更新数据 */
    private fun shouldUpdateFromNetwork(): Boolean {
//确保用户账户已就绪（包括游客账户）且token有效
        return UnifiedStartupManager.isUserAccountReady() &&
                IntySetting.isLogin() &&
                IntySetting.getCurToken().isNotEmpty()
    }
}

/** 网络请求结果 */
sealed class NetworkResult {
    data class Success(val data: AgentInfoResponse) : NetworkResult()

    data class Error(val error: String) : NetworkResult()
}
