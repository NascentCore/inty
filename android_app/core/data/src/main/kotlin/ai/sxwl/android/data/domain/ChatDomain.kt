package ai.sxwl.android.data.domain

import ai.sxwl.android.data.api.model.MsgInfo
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.StateFlow

/**
 * 聊天领域层接口
 * 定义聊天相关的业务逻辑接口，不依赖具体实现
 */
interface ChatRepository {

    /**
     * 获取指定agent的消息流
     */
    fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>>

    /**
     * 获取加载更多状态流
     */
    fun getLoadingMoreFlow(agentId: String): StateFlow<Boolean>

    /**
     * 获取是否有更多消息状态流
     */
    fun getHasMoreFlow(agentId: String): StateFlow<Boolean>

    /**
     *确定最终历史数据已加载
     */
    suspend fun ensureInitialHistory(agentId: String, pageSize: Int = 20)

    /**
     * 加载更多消息
     */
    suspend fun loadMoreMessages(agentId: String, pageSize: Int = 20)

    /**
     * 发送消息
     */
    suspend fun sendMessage(agentId: String, content: String): HttpResult<ai.sxwl.android.data.api.model.SendMsgResponse>

    /**
     * 同步最新消息
     */
    suspend fun syncLatestMessages(agentId: String, pageSize: Int = 20)

    /**
     * 更新消息音频URL
     */
    fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String)

    /**
     * 清理指定代理的聊天数据
     */
    fun clearChatData(agentId: String)

    /**
     * 清理所有聊天数据
     */
    fun clearAllChatData()
}
