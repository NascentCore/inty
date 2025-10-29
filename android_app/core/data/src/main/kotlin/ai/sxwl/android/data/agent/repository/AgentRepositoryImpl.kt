package ai.sxwl.android.data.agent.repository

import ai.sxwl.android.data.agent.domain.AgentRepository
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.cache.AgentCacheProvider
import ai.sxwl.android.data.chat.paging.AgentPagingSource
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/** Agent仓库实现 作为Domain层和Data层之间的桥梁 遵循Clean Architecture的Repository模式 */
class AgentRepositoryImpl(
    private val cacheProvider: AgentCacheProvider? = null,
) : AgentRepository {

    companion object {
        private const val PAGE_SIZE = 20
        private const val PREFETCH_DISTANCE = 3
        private const val ENABLE_PLACEHOLDERS = false
    }

    override fun getChatAgentsFlow(useCache: Boolean, sortSeed: Int): Flow<PagingData<AgentInfo>> {
        LogUtils.d("AgentRepositoryImpl.getChatAgentsFlow: useCache=$useCache, sortSeed=$sortSeed")

        return Pager(
                config =
                    PagingConfig(
                        pageSize = PAGE_SIZE,
                        prefetchDistance = PREFETCH_DISTANCE,
                        enablePlaceholders = ENABLE_PLACEHOLDERS,
                        initialLoadSize = PAGE_SIZE,
                    ),
                pagingSourceFactory = {
                    AgentPagingSource(
                        useCache = useCache,
                        sortSeed = sortSeed,
                        cacheProvider = cacheProvider
                    )
                },
            )
            .flow
    }

    override fun refreshChatAgents(): Flow<PagingData<AgentInfo>> {
        LogUtils.d("AgentRepositoryImpl.refreshChatAgents")
        val newSortSeed = IntySetting.randomSortSeed()
        return getChatAgentsFlow(useCache = false, sortSeed = newSortSeed)
    }

    override fun getInitialChatAgents(): Flow<PagingData<AgentInfo>> {
        LogUtils.d("AgentRepositoryImpl.getInitialChatAgents")
        return getChatAgentsFlow(useCache = true, sortSeed = IntySetting.randomSortSeed())
    }
}
