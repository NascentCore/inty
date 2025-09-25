package com.ai.inty.explore

import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import com.ai.inty.beans.AgentInfo
import com.ai.inty.net.IAgentApi
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.flow.Flow

/**
 * Explore页面的Paging数据仓库
 * 负责管理Paging数据流、配置和传统数据请求
 * 集成了原ExploreRepository的所有功能
 */
class ExplorePagingRepository {

    private val agentApi: IAgentApi by lazy {
        TheRouter.get(IAgentApi::class.java)
            ?: throw IllegalStateException("IAgentApi not found in TheRouter")
    }

    // 用于推荐接口的sort seed
    private var sortSeed = IntySetting.sortSeed()

    companion object {
        // 使用统一的常量
        private const val PAGE_SIZE = ExploreConstants.PAGE_SIZE
        private const val PREFETCH_DISTANCE = ExploreConstants.PREFETCH_DISTANCE
        private const val ENABLE_PLACEHOLDERS = ExploreConstants.ENABLE_PLACEHOLDERS
    }

    /**
     * 获取推荐agents的Paging数据流
     * @param useCache 是否使用缓存数据
     * @param sortSeed 排序种子，用于刷新时改变排序
     */
    fun getRecommendAgentsFlow(
        useCache: Boolean = true,
        sortSeed: Int = IntySetting.sortSeed()
    ): Flow<PagingData<AgentInfo>> {
        EasyLog.log("ExplorePagingRepository - 创建Paging数据流，useCache: $useCache, sortSeed: $sortSeed")
        
        return Pager(
            config = PagingConfig(
                pageSize = PAGE_SIZE,
                prefetchDistance = PREFETCH_DISTANCE,
                enablePlaceholders = ENABLE_PLACEHOLDERS,
                initialLoadSize = PAGE_SIZE,
                maxSize = PAGE_SIZE * ExploreConstants.MAX_CACHE_PAGES // 最大缓存页数
            ),
            pagingSourceFactory = {
                ExplorePagingSource(
                    useCache = useCache,
                    sortSeed = sortSeed
                )
            }
        ).flow
    }

    /**
     * 刷新数据（生成新的排序种子）
     */
    fun refreshRecommendAgents(): Flow<PagingData<AgentInfo>> {
        val newSortSeed = IntySetting.sortSeed() + 1
        IntySetting.updateSortSeed(newSortSeed)
        EasyLog.log("ExplorePagingRepository - 刷新数据，新sortSeed: $newSortSeed")
        
        return getRecommendAgentsFlow(
            useCache = false, // 刷新时不使用缓存
            sortSeed = newSortSeed
        )
    }

    /**
     * 获取初始数据（优先使用缓存）
     */
    fun getInitialRecommendAgents(): Flow<PagingData<AgentInfo>> {
        return getRecommendAgentsFlow(useCache = true)
    }

    /**
     * 预加载第一页数据，用于刷新前的数据验证
     * 返回Result，成功时表示数据可用，失败时保持当前数据
     */
    suspend fun preloadFirstPage(): Result<Unit> {
        return try {
            val newSortSeed = IntySetting.sortSeed() + 1
            val agentApi: IAgentApi = TheRouter.get(IAgentApi::class.java)
                ?: throw IllegalStateException("IAgentApi not found in TheRouter")

            val result = agentApi.recommendAgents(
                page = 1,
                pageSize = PAGE_SIZE,
                sort_seed = newSortSeed.toString()
            )

            when (result) {
                is com.architecture.httplib.core.HttpResult.Success -> {
                    val agents = result.data.list ?: emptyList()
                    if (agents.isNotEmpty()) {
                        EasyLog.log("ExplorePagingRepository - 预加载第一页成功: ${agents.size}个")
                        Result.success(Unit)
                    } else {
                        EasyLog.log("ExplorePagingRepository - 预加载第一页数据为空", EasyLog.WARN)
                        Result.failure(Exception("Empty data"))
                    }
                }
                is com.architecture.httplib.core.HttpResult.Failure -> {
                    EasyLog.log("ExplorePagingRepository - 预加载第一页失败: ${result.message}", EasyLog.WARN)
                    Result.failure(Exception(result.message ?: "Network error"))
                }
            }
        } catch (e: Exception) {
            EasyLog.log("ExplorePagingRepository - 预加载第一页异常: ${e.message}", EasyLog.ERROR)
            Result.failure(e)
        }
    }

}
