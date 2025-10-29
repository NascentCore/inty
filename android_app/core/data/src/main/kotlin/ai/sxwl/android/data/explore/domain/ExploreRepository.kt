package ai.sxwl.android.data.explore.domain

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/**
 * Explore领域层接口
 * 定义探索页面相关的业务逻辑接口，不依赖具体实现
 * 遵循Clean Architecture的依赖倒置原则
 */
interface ExploreRepository {

    /** 获取推荐agents的分页数据流 */
    fun getRecommendAgentsFlow(useCache: Boolean = true, sortSeed: Int): Flow<PagingData<AgentInfo>>

    /** 刷新推荐agents数据 */
    fun refreshRecommendAgents(): Flow<PagingData<AgentInfo>>

    /** 获取初始推荐agents数据 */
    fun getInitialRecommendAgents(): Flow<PagingData<AgentInfo>>
}
