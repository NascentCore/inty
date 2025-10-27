package ai.sxwl.android.data.usecase.agent

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.domain.AgentRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/** 获取聊天Agents用例 封装获取聊天agents列表的业务逻辑 */
class GetChatAgentsUseCase(private val agentRepository: AgentRepository) {

    /**
     * 获取初始聊天agents数据流
     *
     * @return PagingData<AgentInfo> 分页数据流
     */
    operator fun invoke(): Flow<PagingData<AgentInfo>> {
        LogUtils.d("GetChatAgentsUseCase.invoke() called")
        return agentRepository.getInitialChatAgents()
    }

    /**
     * 刷新聊天agents数据流
     *
     * @return PagingData<AgentInfo> 分页数据流
     */
    fun refresh(): Flow<PagingData<AgentInfo>> {
        LogUtils.d("GetChatAgentsUseCase.refresh() called")
        return agentRepository.refreshChatAgents()
    }

    /**
     * 获取聊天agents数据流（带参数）
     *
     * @param useCache 是否使用缓存
     * @param sortSeed 排序种子
     * @return PagingData<AgentInfo> 分页数据流
     */
    fun getAgentsFlow(
        useCache: Boolean = true,
        sortSeed: Int = IntySetting.randomSortSeed()
    ): Flow<PagingData<AgentInfo>> {
        LogUtils.d("GetChatAgentsUseCase.getAgentsFlow: useCache=$useCache, sortSeed=$sortSeed")
        return agentRepository.getChatAgentsFlow(useCache, sortSeed)
    }
}
