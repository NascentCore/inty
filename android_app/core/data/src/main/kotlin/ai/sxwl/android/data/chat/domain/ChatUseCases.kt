package ai.sxwl.android.data.chat.domain

import ai.sxwl.android.data.api.model.SendMsgResponse
import com.architecture.httplib.core.HttpResult

/** 加载聊天历史用例 封装加载聊天历史的业务逻辑 遵循Clean Architecture的UseCase模式 */
class LoadChatHistoryUseCase(private val chatRepository: ChatRepository) {

    suspend operator fun invoke(agentId: String, pageSize: Int = 20) {
        chatRepository.ensureInitialHistory(agentId, pageSize)
    }
}

/** 发送消息用例 封装发送消息的业务逻辑 */
class SendMessageUseCase(private val chatRepository: ChatRepository) {

    suspend operator fun invoke(agentId: String, content: String): HttpResult<SendMsgResponse> {
        return chatRepository.sendMessage(agentId, content)
    }
}

/** 同步聊天数据用例 封装同步聊天数据的业务逻辑 */
class SyncChatDataUseCase(private val chatRepository: ChatRepository) {

    suspend operator fun invoke(agentId: String, pageSize: Int = 20) {
        chatRepository.syncLatestMessages(agentId, pageSize)
    }
}

/** 更新消息反馈用例 封装消息反馈的业务逻辑 */
class UpdateMessageFeedbackUseCase(private val chatRepository: ChatRepository) {

    operator fun invoke(
        agentId: String,
        messageId: String,
        feedback: ai.sxwl.android.data.api.model.MsgInfo.UserFeedback?,
    ) {
        chatRepository.updateMessageFeedback(agentId, messageId, feedback)
    }
}

/** 重新生成消息用例 封装重新生成消息的业务逻辑 */
class RecallMessageUseCase(private val chatRepository: ChatRepository) {

    suspend operator fun invoke(agentId: String) {
        chatRepository.recallLastAssistantMessage(agentId)
    }
}

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
