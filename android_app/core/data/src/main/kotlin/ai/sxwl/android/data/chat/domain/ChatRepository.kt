package ai.sxwl.android.data.chat.domain

import ai.sxwl.android.data.api.model.ChatImageGenerationResult
import ai.sxwl.android.data.api.model.MsgInfo
import com.architecture.httplib.core.HttpResult

/** Chat领域层接口 定义聊天相关的业务逻辑接口 来完成与后端服务的交互，并写入数据到本地存储中 */
interface ChatRepository {

    /** 更新消息音频URL */
    fun updateMessageAudioUrl(agentId: String, messageId: String, audioUrl: String)

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
    ): HttpResult<ChatImageGenerationResult>

    /** 清理指定agent的聊天数据 这个函数在 RoomDataSource 中实现是异步，因此需要是 suspend 函数 */
    suspend fun clearChatData(agentId: String)

    /** 清理所有聊天数据 这个函数在 RoomDataSource 中实现是异步，因此需要是 suspend 函数 */
    suspend fun clearAllChatData()

    /** Reset聊天 */
    suspend fun clearMessage(agentId: String): Boolean
}
