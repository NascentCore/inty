package ai.sxwl.android.data.chat.domain

import ai.sxwl.android.data.api.model.ChatImageGenerationResult
import com.architecture.httplib.core.HttpResult

/** 生成图片消息用例 封装生成图片消息的业务逻辑 */
class GenerateImageUseCase(private val chatRepository: ChatRepository) {

    suspend operator fun invoke(
        agentId: String,
        messageId: String,
    ): HttpResult<ChatImageGenerationResult> {
        return chatRepository.generateImageForMessage(agentId, messageId)
    }
}
