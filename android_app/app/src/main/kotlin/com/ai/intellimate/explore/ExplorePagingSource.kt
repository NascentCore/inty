package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import ai.sxwl.android.data.explore.paging.ExplorePagingSource as BaseExplorePagingSource
import ai.sxwl.android.data.explore.paging.NetworkResult
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.PagingSource
import com.ai.intellimate.utils.UnifiedStartupManager
import kotlinx.coroutines.delay

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

/** Explore页面的Paging数据源 负责处理推荐agents的分页加载、缓存管理
 * 继承 core/data 层的 ExplorePagingSource，添加事件上报和账户就绪检查功能
 */
class ExplorePagingSource(
    useCache: Boolean = true,
    sortSeed: Int = IntySetting.sortSeed(),
    cacheProvider: RecommendedAgentCacheProvider? = null,
    private val fetchCallback: ExploreFetchCallback? = null,
) : BaseExplorePagingSource(useCache, sortSeed, cacheProvider) {
    
    // 保存 sortSeed 用于事件上报（父类的 sortSeed 是 private 的）
    private val currentSortSeed = sortSeed

    override suspend fun load(params: PagingSource.LoadParams<Int>): PagingSource.LoadResult<Int, AgentInfo> {
        // 检查用户账户是否已就绪，如果未就绪则等待或返回空数据
        // 这是 app 层特有的功能，core/data 层只检查登录状态
        if (!UnifiedStartupManager.isUserAccountReady()) {
            // 等待用户账户就绪，最多等待5秒
            var waitTime = 0
            while (!UnifiedStartupManager.isUserAccountReady() && waitTime < 5000) {
                delay(100)
                waitTime += 100
            }

            if (!UnifiedStartupManager.isUserAccountReady()) {
                // 如果账户仍未就绪，返回空数据，但设置 nextKey 以便后续重试
                LogUtils.w("ExplorePagingSource - 用户账户未就绪，返回空数据但允许重试")
                return PagingSource.LoadResult.Page(
                    data = emptyList(),
                    prevKey = null,
                    nextKey = BaseExplorePagingSource.INITIAL_PAGE, // 设置 nextKey，允许后续重试
                )
            }
        }

        // 调用父类的 load 方法，复用基础逻辑
        return super.load(params)
    }

    // getRefreshKey 方法已在父类中实现，无需重写

    /** 重写网络加载方法，添加性能指标上报 */
    override suspend fun loadFromNetwork(page: Int, pageSize: Int): NetworkResult {
        val startTime = System.currentTimeMillis()
        val result = super.loadFromNetwork(page, pageSize)
        val responseTime = System.currentTimeMillis() - startTime

        // 添加事件上报逻辑
        when (result) {
            is NetworkResult.Success -> {
                val agents = result.data.list ?: emptyList()
                val validAgents = agents.filter { it.id.isNotEmpty() }
                val agentsCount = validAgents.size
                fetchCallback?.onSuccess(page, pageSize, responseTime, agentsCount, currentSortSeed)
            }
            is NetworkResult.Error -> {
                fetchCallback?.onFailure(page, pageSize, responseTime, result.error, currentSortSeed)
            }
        }

        return result
    }
}
