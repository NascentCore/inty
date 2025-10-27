package ai.sxwl.android.data.domain

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.paging.PagingData
import kotlinx.coroutines.flow.Flow

/**
 * Agent领域层接口
 * 定义Agent相关的业务逻辑接口，不依赖具体实现
 */
interface AgentRepository {

    /** 获取聊天agents的分页数据流 */
    fun getChatAgentsFlow(useCache: Boolean = true, sortSeed: Int): Flow<PagingData<AgentInfo>>

    /** 刷新聊天agents数据 */
    fun refreshChatAgents(): Flow<PagingData<AgentInfo>>

    /** 获取初始聊天agents数据 */
    fun getInitialChatAgents(): Flow<PagingData<AgentInfo>>
}
