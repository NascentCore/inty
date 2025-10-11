package com.ai.inty.chat.paging

import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.ai.inty.beans.AgentInfo
import com.ai.inty.chat.constants.ChatConstants
import com.ai.inty.net.IAgentApi
import com.ai.inty.utils.AgentCacheManager
import com.ai.inty.utils.UnifiedStartupManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Chat页面的Paging数据源 负责处理聊天agents的分页加载、缓存管理 使用chatAgents API，与exploreAgents区分开 */
class ChatPagingSource(
    private val useCache: Boolean = true,
    private val sortSeed: Int = IntySetting.randomSortSeed(),
) : PagingSource<Int, AgentInfo>() {

    private val agentApi: IAgentApi by lazy {
        TheRouter.get(IAgentApi::class.java)
            ?: throw IllegalStateException("IAgentApi not found in TheRouter")
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

                EasyLog.log("ChatPagingSource - 加载第${page}页，页面大小: ${pageSize}")

                // 第一页特殊处理：优先使用缓存数据
                if (page == INITIAL_PAGE && useCache) {
                    val cachedAgents = UnifiedStartupManager.getCurrentChatAgents()
                    if (cachedAgents.isNotEmpty()) {
                        // 如果有缓存数据，返回缓存数据，同时后台加载网络数据
                        if (shouldUpdateFromNetwork()) {
                            // 后台静默刷新，不阻塞UI
                            loadFromNetworkAsync(page, pageSize)
                        }

                        // 返回缓存数据，假设有更多数据以支持分页
                        return@withContext LoadResult.Page(
                            data = cachedAgents,
                            prevKey = null,
                            nextKey = if (cachedAgents.isNotEmpty()) page + 1 else null,
                        )
                    }
                }

                // 检查用户账户是否已就绪，如果未就绪则等待或返回空数据
                if (!UnifiedStartupManager.isUserAccountReady()) {
                    EasyLog.log("ChatPagingSource - 用户账户未就绪，等待账户就绪")
                    
                    // 等待用户账户就绪，最多等待5秒
                    var waitTime = 0
                    while (!UnifiedStartupManager.isUserAccountReady() && waitTime < 5000) {
                        delay(100)
                        waitTime += 100
                    }
                    
                    if (!UnifiedStartupManager.isUserAccountReady()) {
                        EasyLog.log("ChatPagingSource - 等待超时，返回空数据")
                        return@withContext LoadResult.Page(
                            data = emptyList(),
                            prevKey = null,
                            nextKey = null,
                        )
                    }
                }

                // 从网络加载数据
                val result = loadFromNetwork(page, pageSize)

                when (result) {
                    is NetworkResult.Success -> {
                        val agents = result.data.list ?: emptyList()
                        val hasMore = agents.isNotEmpty() && agents.size >= pageSize

EasyLog.log("ChatPagingSource - 角色总数统计: ${result.data.total}", EasyLog.INFO)


                        // 缓存第一页数据
                        if (page == INITIAL_PAGE && agents.isNotEmpty()) {
                            AgentCacheManager.cacheChatAgents(agents)
                            UnifiedStartupManager.refreshChatAgents()
                            EasyLog.log("ChatPagingSource - 缓存第一页数据: ${agents.size}个")
                        }

                        LoadResult.Page(
                            data = agents,
                            prevKey = if (page == INITIAL_PAGE) null else page - 1,
                            nextKey = if (hasMore) page + 1 else null,
                        )
                    }

                    is NetworkResult.Error -> {
                        EasyLog.log("ChatPagingSource - 网络加载失败: ${result.error}", EasyLog.ERROR)
                        LoadResult.Error(Exception(result.error))
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("ChatPagingSource - 加载异常: ${e.message}", EasyLog.ERROR)
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
                    NetworkResult.Error(result.message ?: "Unknown error")
                }
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.message ?: "Network error")
        }
    }

    /** 异步从网络加载数据（不阻塞UI） */
    private fun loadFromNetworkAsync(page: Int, pageSize: Int) {
        // 在后台协程中执行，不阻塞当前加载
        kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch {
            try {
                val result = loadFromNetwork(page, pageSize)
                if (result is NetworkResult.Success) {
                    val agents = result.data.list ?: emptyList()
                    if (agents.isNotEmpty()) {
                        AgentCacheManager.cacheChatAgents(agents)
                        UnifiedStartupManager.refreshChatAgents()
                        EasyLog.log("ChatPagingSource - 后台刷新完成: ${agents.size}个")
                    }
                }
            } catch (e: Exception) {
                EasyLog.log("ChatPagingSource - 后台刷新失败: ${e.message}", EasyLog.ERROR)
            }
        }
    }

    /** 检查是否需要从网络更新数据 */
    private fun shouldUpdateFromNetwork(): Boolean {
        // 确保用户账户已就绪（包括游客账户）且token有效
        return UnifiedStartupManager.isUserAccountReady() && 
               IntySetting.isLogin() && 
               IntySetting.getCurToken().isNotEmpty()
    }
}

/** 网络请求结果 */
sealed class NetworkResult {
    data class Success(val data: com.ai.inty.beans.AgentInfoResponse) : NetworkResult()

    data class Error(val error: String) : NetworkResult()
}
