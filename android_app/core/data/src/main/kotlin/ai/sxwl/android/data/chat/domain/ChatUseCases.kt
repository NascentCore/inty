package ai.sxwl.android.data.chat.domain

import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.api.model.VoteMessageRsp
import com.architecture.httplib.core.HttpResult


/** 生成图片消息用例 封装生成图片消息的业务逻辑 */
class GenerateImageUseCase(private val chatRepository: ChatRepository) {

    suspend operator fun invoke(
        agentId: String,
        messageId: String,
    ): com.architecture.httplib.core.HttpResult<
        ai.sxwl.android.data.http.services.ChatService.ChatImageGenerationResult
    > {
        return chatRepository.generateImageForMessage(agentId, messageId)
    }
}
