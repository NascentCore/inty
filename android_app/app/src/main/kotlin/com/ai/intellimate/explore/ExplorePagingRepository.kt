package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/** Explore页面的Paging数据仓库 负责管理Paging数据流、配置和传统数据请求 集成了原ExploreRepository的所有功能 */
class ExplorePagingRepository {
    companion object {
        // 使用统一的常量
        private const val PAGE_SIZE = ExploreConstants.PAGE_SIZE
        private const val PREFETCH_DISTANCE = ExploreConstants.PREFETCH_DISTANCE
        private const val ENABLE_PLACEHOLDERS = ExploreConstants.ENABLE_PLACEHOLDERS
    }

    /**
     * 获取推荐agents的Paging数据流
     *
     * @param useCache 是否使用缓存数据
     * @param sortSeed 排序种子，用于刷新时改变排序
     */
    fun getRecommendAgentsFlow(
        useCache: Boolean = true,
        sortSeed: Int = IntySetting.sortSeed(),
    ): Flow<PagingData<AgentInfo>> {
        return Pager(
            config =
            PagingConfig(
                pageSize = PAGE_SIZE,
                prefetchDistance = PREFETCH_DISTANCE,
                enablePlaceholders = ENABLE_PLACEHOLDERS,
                initialLoadSize = PAGE_SIZE,
                maxSize = PAGE_SIZE * ExploreConstants.MAX_CACHE_PAGES, // 最大缓存页数
            ),
            pagingSourceFactory = {
                ExplorePagingSource(useCache = useCache, sortSeed = sortSeed)
            },
        )
            .flow
    }

    /** 刷新数据（生成新的排序种子） */
    fun refreshRecommendAgents(): Flow<PagingData<AgentInfo>> {
        val newSortSeed = IntySetting.sortSeed() + 1
        IntySetting.updateSortSeed(newSortSeed)
        return getRecommendAgentsFlow(
            useCache = false, // 刷新时不使用缓存
            sortSeed = newSortSeed,
        )
    }

    /** 获取初始数据（优先使用缓存） */
    fun getInitialRecommendAgents(): Flow<PagingData<AgentInfo>> {
        return getRecommendAgentsFlow(useCache = true)
    }
}
