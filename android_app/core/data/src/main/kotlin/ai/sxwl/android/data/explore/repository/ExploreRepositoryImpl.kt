package ai.sxwl.android.data.explore.repository

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import ai.sxwl.android.data.explore.domain.ExploreRepository
import ai.sxwl.android.data.explore.paging.ExplorePagingSource
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/** Explore仓库实现 作为Domain层和Data层之间的桥梁 遵循Clean Architecture的Repository模式 */
class ExploreRepositoryImpl(private val cacheProvider: RecommendedAgentCacheProvider? = null) :
    ExploreRepository {

    companion object {
        private const val PAGE_SIZE = 20
        private const val PREFETCH_DISTANCE = 3
        private const val ENABLE_PLACEHOLDERS = false
        private const val MAX_CACHE_PAGES = 3
    }

    override fun getRecommendAgentsFlow(
        useCache: Boolean,
        sortSeed: Int,
    ): Flow<PagingData<AgentInfo>> {
        LogUtils.d(
            "ExploreRepositoryImpl.getRecommendAgentsFlow: useCache=$useCache, sortSeed=$sortSeed"
        )

        return Pager(
                config =
                    PagingConfig(
                        pageSize = PAGE_SIZE,
                        prefetchDistance = PREFETCH_DISTANCE,
                        enablePlaceholders = ENABLE_PLACEHOLDERS,
                        initialLoadSize = PAGE_SIZE,
                        maxSize = PAGE_SIZE * MAX_CACHE_PAGES,
                    ),
                pagingSourceFactory = {
                    ExplorePagingSource(
                        useCache = useCache,
                        sortSeed = sortSeed,
                        cacheProvider = cacheProvider,
                    )
                },
            )
            .flow
    }

    override fun refreshRecommendAgents(): Flow<PagingData<AgentInfo>> {
        LogUtils.d("ExploreRepositoryImpl.refreshRecommendAgents")
        val newSortSeed = IntySetting.sortSeed() + 1
        IntySetting.updateSortSeed(newSortSeed)
        return getRecommendAgentsFlow(useCache = false, sortSeed = newSortSeed)
    }

    override fun getInitialRecommendAgents(): Flow<PagingData<AgentInfo>> {
        LogUtils.d("ExploreRepositoryImpl.getInitialRecommendAgents")
        return getRecommendAgentsFlow(useCache = true, sortSeed = IntySetting.sortSeed())
    }
}
