package ai.sxwl.android.data.explore.domain

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/** 获取推荐Agents用例 封装获取推荐Agents的业务逻辑 遵循Clean Architecture的UseCase模式 */
class GetRecommendAgentsUseCase(private val exploreRepository: ExploreRepository) {

    operator fun invoke(useCache: Boolean = true): Flow<PagingData<AgentInfo>> {
        return exploreRepository.getInitialRecommendAgents()
    }

    /** 刷新推荐agents数据（更新sort seed） */
    fun refresh(): Flow<PagingData<AgentInfo>> {
        return exploreRepository.refreshRecommendAgents()
    }
}
