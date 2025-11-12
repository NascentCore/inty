package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager

/** 图片生成错误信息 */
data class ChatImageGenerationError(
    val code: Long,
    val errorCode: String?,
    val message: String?,
    val dailyLimit: Long?,
    val usedCount: Long?,
)

/** 图片生成限制异常 */
class ChatImageGenerationLimitException(val error: ChatImageGenerationError) :
    Exception(error.message ?: "Image generation limit reached")

/** 聊天服务 封装所有聊天相关的API调用 替换原有的 IChatApi */
object ChatService {

    /** 发送聊天消息 替换: IChatApi.sendMessage() */
    suspend fun sendMessage(
        agentId: String,
        message: String,
        conversationId: String? = null,
    ): ApiResult<MsgInfo> {
        return IntyNetworkManager.executeRequest("Send Message") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .agents()
                    .generateMessageVoice(
                        com.inty.api.models.api.v1.chats.agents.AgentGenerateMessageVoiceParams
                            .builder()
                            .agentId(agentId)
                            .messageId("temp_message_id") // 这里需要根据实际情况处理
                            .language("en") // 这里需要根据实际情况处理
                            .build()
                    )

            // 当前 IntySDK 的 Chat 数据结构与业务层不匹配
            // 需要根据实际返回结构进行数据转换
            throw Exception("Chat message conversion not implemented, need data mapping")
        }
    }

    /** 获取聊天历史 替换: IChatApi.getChatHistory() */
    suspend fun getChatHistory(
        conversationId: String,
        page: Int = 1,
        pageSize: Int = 20,
    ): ApiResult<List<MsgInfo>> {
        return IntyNetworkManager.executeRequest("Get Chat History") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .agents()
                    .getMessages(
                        com.inty.api.models.api.v1.chats.agents.AgentGetMessagesParams.builder()
                            .agentId("temp_agent_id") // 这里需要根据实际情况处理
                            .build()
                    )

            // 这里需要根据实际的IntySDK返回结构进行转换
            emptyList<MsgInfo>()
        }
    }

    /** 创建新对话 替换: IChatApi.createConversation() */
    suspend fun createConversation(agentId: String): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Create Conversation") {
            val chat =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .create(
                        com.inty.api.models.api.v1.chats.ChatCreateParams.builder()
                            .agentId(agentId)
                            .build()
                    )

            chat.id() ?: throw IllegalStateException("Conversation ID is null")
        }
    }

    /** 删除对话 替换: IChatApi.deleteConversation() */
    suspend fun deleteConversation(conversationId: String): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Delete Conversation") {
            IntyNetworkManager.getClient().api().v1().chats().delete(conversationId)
        }
    }

    /** 获取对话列表 替换: IChatApi.getConversations() */
    suspend fun getConversations(
        page: Int = 1,
        pageSize: Int = 20,
    ): ApiResult<List<ConversationInfo>> {
        return IntyNetworkManager.executeRequest("Get Conversations") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .chats()
                    .list(
                        com.inty.api.models.api.v1.chats.ChatListParams.builder()
                            .limit(pageSize.toLong())
                            .skip(((page - 1) * pageSize).toLong())
                            .build()
                    )

            // 这里需要根据实际的IntySDK返回结构进行转换
            emptyList<ConversationInfo>()
        }
    }

    /** 生成聊天图片 */
    suspend fun generateImage(
        agentId: String,
        messageId: String,
    ): ApiResult<ChatImageGenerationResult> {
        return IntyNetworkManager.executeRequest("Generate Chat Image") {
            val client = IntyNetworkManager.getClient()
            val params =
                com.inty.api.models.api.v1.chats.ChatGenerateImageParams.builder()
                    .agentId(agentId)
                    .messageId(messageId.toLongOrNull() ?: 0L)
                    .build()

            val response = client.api().v1().chats().generateImage(params)

            if (
                response.code() == 200L && response.data()?.isChatImageGenerationResponse() == true
            ) {
                val imageData = response.data()?.asChatImageGenerationResponse()!!
                val imageUrl = imageData.imageUrl()
                val imageMeta = imageData.imageMetadata()

                // 从 ImageMetadata 的 additionalProperties 中获取 width 和 height
                val width = imageMeta._additionalProperties()["width"]?.asNumber()?.toInt() ?: 0
                val height = imageMeta._additionalProperties()["height"]?.asNumber()?.toInt() ?: 0

                ChatImageGenerationResult(
                    imageUrl = imageUrl,
                    width = width,
                    height = height,
                    messageId = imageData.messageId(),
                )
            } else if (response.data()?.isUsageLimitExceeded() == true) {
                // 处理业务错误（如次数限制）
                val errorData = response.data()?.asUsageLimitExceeded()!!
                val errorCodeStr = errorData.errorCode()

                // 将errorCode映射到业务错误码
                val businessCode =
                    when (errorCodeStr) {
                        "IMAGE_GENERATION_LIMIT_REACHED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes
                                .IMAGE_GENERATION_LIMIT_REACHED_CODE
                                .toLong()
                        "SUBSCRIPTION_REQUIRED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
                                .toLong()
                        else -> errorData.code()
                    }

                val error =
                    ChatImageGenerationError(
                        code = businessCode,
                        errorCode = errorCodeStr,
                        message = errorData.message(),
                        dailyLimit = errorData.dailyLimit(),
                        usedCount = errorData.usedCount(),
                    )
                throw ChatImageGenerationLimitException(error)
            } else {
                val errorMessage = response.message() ?: "Failed to generate image"
                throw Exception(errorMessage)
            }
        }
    }

    /** 对话信息数据类 */
    data class ConversationInfo(
        val id: String,
        val agentId: String,
        val agentName: String,
        val lastMessage: String?,
        val lastMessageTime: Long,
        val messageCount: Int,
    )

    /** 图片生成结果 */
    data class ChatImageGenerationResult(
        val imageUrl: String,
        val width: Int,
        val height: Int,
        val messageId: Long,
    )
}
