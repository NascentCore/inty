package com.ai.inty.explore

import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.ai.inty.beans.AgentInfo
import com.ai.inty.net.IAgentApi
import com.ai.inty.utils.AgentCacheManager
import com.ai.inty.utils.UnifiedStartupManager
import com.architecture.httplib.core.HttpResult
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Explore页面的Paging数据源 负责处理推荐agents的分页加载、缓存管理 */
class ExplorePagingSource(
    private val useCache: Boolean = true,
    private val sortSeed: Int = IntySetting.sortSeed(),
) : PagingSource<Int, AgentInfo>() {

  private val agentApi: IAgentApi by lazy {
    TheRouter.get(IAgentApi::class.java)
        ?: throw IllegalStateException("IAgentApi not found in TheRouter")
  }

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

        EasyLog.log("ExplorePagingSource - 加载第${page}页，页面大小: ${pageSize}")

        // 第一页特殊处理：优先使用缓存数据
        if (page == INITIAL_PAGE && useCache) {
          val cachedAgents = UnifiedStartupManager.getCurrentRecommendedAgents()
          if (cachedAgents.isNotEmpty()) {
            EasyLog.log("ExplorePagingSource - 使用缓存数据: ${cachedAgents.size}个")

            // 如果有缓存数据，返回缓存数据，同时后台加载网络数据
            if (shouldUpdateFromNetwork()) {
              // 后台静默刷新，不阻塞UI
              loadFromNetworkAsync(page, pageSize)
            }

            // 关键修复：即使缓存数据不足一页，也假设有更多数据
            // 这样Paging会继续尝试加载下一页，确保分页功能正常
            // 但是要确保缓存数据不为空，避免无限循环
            return@withContext LoadResult.Page(
                data = cachedAgents,
                prevKey = null,
                nextKey = if (cachedAgents.isNotEmpty()) page + 1 else null,
            )
          }
        }

        // 从网络加载数据
        val result = loadFromNetwork(page, pageSize)

        when (result) {
          is NetworkResult.Success -> {
            val agents = result.data.list ?: emptyList()
            val hasMore = agents.isNotEmpty() && agents.size >= pageSize

            // 缓存第一页数据
            if (page == INITIAL_PAGE && agents.isNotEmpty()) {
              AgentCacheManager.cacheAgents(agents)
              UnifiedStartupManager.refreshRecommendedAgents()
              EasyLog.log("ExplorePagingSource - 缓存第一页数据: ${agents.size}个")
            }

            LoadResult.Page(
                data = agents,
                prevKey = if (page == INITIAL_PAGE) null else page - 1,
                nextKey = if (hasMore) page + 1 else null,
            )
          }

          is NetworkResult.Error -> {
            EasyLog.log("ExplorePagingSource - 网络加载失败: ${result.error}", EasyLog.ERROR)
            LoadResult.Error(Exception(result.error))
          }
        }
      } catch (e: Exception) {
        EasyLog.log("ExplorePagingSource - 加载异常: ${e.message}", EasyLog.ERROR)
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
          agentApi.recommendAgents(
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
            AgentCacheManager.cacheAgents(agents)
            UnifiedStartupManager.refreshRecommendedAgents()
            EasyLog.log("ExplorePagingSource - 后台刷新完成: ${agents.size}个")
          }
        }
      } catch (e: Exception) {
        EasyLog.log("ExplorePagingSource - 后台刷新失败: ${e.message}", EasyLog.ERROR)
      }
    }
  }

  /** 检查是否需要从网络更新数据 */
  private fun shouldUpdateFromNetwork(): Boolean {
    return IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
  }
}

/** 网络请求结果 */
sealed class NetworkResult {
  data class Success(val data: com.ai.inty.beans.AgentInfoResponse) : NetworkResult()

  data class Error(val error: String) : NetworkResult()
}
