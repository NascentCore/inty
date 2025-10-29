package ai.sxwl.android.data.agent.domain

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/**
 * 获取聊天Agents用例
 * 封装获取聊天Agents的业务逻辑
 * 遵循Clean Architecture的UseCase模式
 */
class GetChatAgentsUseCase(
    private val agentRepository: AgentRepository
) {

    operator fun invoke(useCache: Boolean = true): Flow<PagingData<AgentInfo>> {
        return agentRepository.getInitialChatAgents()
    }
}
