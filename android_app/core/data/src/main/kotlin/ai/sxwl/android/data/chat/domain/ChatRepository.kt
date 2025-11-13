package ai.sxwl.android.data.chat.domain

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.http.services.ChatService
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.flow.StateFlow

/** Chat领域层接口 定义聊天相关的业务逻辑接口，不依赖具体实现 遵循Clean Architecture的依赖倒置原则 */
interface ChatRepository {

    /** 获取指定agent的消息流 */
    fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>>

    /** 获取加载更多状态流 */
    fun getLoadingMoreFlow(agentId: String): StateFlow<Boolean>

    /** 获取是否有更多消息状态流 */
    fun getHasMoreFlow(agentId: String): StateFlow<Boolean>

    /** 确保初始历史数据已加载 */
    suspend fun ensureInitialHistory(agentId: String, pageSize: Int = 20)

    /** 加载更多消息 */
    suspend fun loadMoreMessages(agentId: String, pageSize: Int = 20)

    /** 发送消息 */
    suspend fun sendMessage(agentId: String, content: String): HttpResult<SendMsgResponse>

    /** 同步最新消息 */
    suspend fun syncLatestMessages(agentId: String, pageSize: Int = 20)

    /** 更新消息音频URL */
    fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String)

    /** 更新消息反馈（like/dislike） */
    fun updateMessageFeedback(agentId: String, messageId: String, feedback: MsgInfo.UserFeedback?)

    /**
     * 更新消息的生成图片信息
     *
     * @param generatedImage 如果为 null，则移除 generatedImage
     */
    fun updateMessageGeneratedImage(
        agentId: String,
        messageId: String,
        generatedImage: MsgInfo.MsgMetaData.GeneratedImage?,
    )

    /** 删除消息 */
    suspend fun removeMessage(agentId: String, messageId: String)

    /** 添加消息 */
    suspend fun addMessage(agentId: String, message: MsgInfo)

    /** 重新生成最后一条AI消息 */
    suspend fun recallLastAssistantMessage(agentId: String)

    /**
     * 生成图片消息
     *
     * @return HttpResult.Success 成功
     * @return HttpResult.Failure
     *   失败，code为业务错误码（如BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_CODE）
     */
    suspend fun generateImageForMessage(
        agentId: String,
        messageId: String,
    ): HttpResult<ChatService.ChatImageGenerationResult>

    /** 清理指定agent的聊天数据 */
    fun clearChatData(agentId: String)

    /** 清理所有聊天数据 */
    fun clearAllChatData()
}
