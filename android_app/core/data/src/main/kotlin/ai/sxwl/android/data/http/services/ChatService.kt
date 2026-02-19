package ai.sxwl.android.data.http.services

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

    /** 消息生图 */
    suspend fun messageGenerateImage(
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

                // 将 error_code 映射到业务错误码（与后端 app/schemas/response.py 一致）
                val businessCode =
                    when (errorCodeStr) {
                        "SUBSCRIPTION_REQUIRED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
                                .toLong()
                        "IMAGE_GENERATION_LIMIT_REACHED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes
                                .IMAGE_GENERATION_LIMIT_REACHED_CODE
                                .toLong()
                        "AGENT_CREATION_LIMIT_REACHED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes
                                .AGENT_CREATION_LIMIT_REACHED_CODE
                                .toLong()
                        "VOICE_GENERATION_LIMIT_REACHED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes
                                .VOICE_GENERATION_LIMIT_REACHED_CODE
                                .toLong()
                        "GUEST_LOGIN_REQUIRED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes.GUEST_LOGIN_REQUIRED_CODE
                                .toLong()
                        "IMAGE_GENERATION_BLOCKED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes
                                .IMAGE_GENERATION_BLOCKED_CODE
                                .toLong()
                        "LIVE_CHAT_AGENT_LIMIT_REACHED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes
                                .LIVE_CHAT_AGENT_LIMIT_REACHED_CODE
                                .toLong()
                        "LIVE_CHAT_DURATION_LIMIT_REACHED" ->
                            ai.sxwl.android.data.http.BusinessErrorCodes
                                .LIVE_CHAT_DURATION_LIMIT_REACHED_CODE
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

    /** 图片生成结果 */
    data class ChatImageGenerationResult(
        val imageUrl: String,
        val width: Int,
        val height: Int,
        val messageId: Long,
    )
}
